"""投稿スペック(post.json)からスライド画像(JPEG)と、必要ならリール動画(MP4)を作る。

使い方:
  python scripts/render.py posts/2026-10-01
  python scripts/render.py posts/2026-10-01 --reel   # リール動画も作る(post.json の type が reel なら自動)

テキスト記法: [[強調]] → 赤字 / **太字** / 改行は \n
"""
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = (ROOT / "templates" / "base.css").read_text(encoding="utf-8")
PULSE = ('<span class="pulse"><svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="#fff" '
         'stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12h4l3-8 4 16 3-8h6"/></svg></span>')
ICON = {"x": "!", "v": "✓", "q": "?"}


def t(s):
    s = html.escape(s or "")
    s = re.sub(r"\[\[(.+?)\]\]", r"<em>\1</em>", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return s.replace("\n", "<br>")


def brand():
    return f'<div class="brand">{PULSE}AI救急</div>'


def head(sl, gap=36):
    out = ""
    if sl.get("tag"):
        out += f'<span class="tag">{t(sl["tag"])}</span>'
    if sl.get("title"):
        out += f'<h2 style="margin-top:{gap}px">{t(sl["title"])}</h2>'
    return out


def lead(sl):
    return f'<div class="spacer"></div><p class="lead">{t(sl.get("lead", ""))}</p>'


def s_cover(sl):
    mock = ""
    if sl.get("mock"):
        m = sl["mock"]
        bars = "".join(f'<div class="bar" style="width:{w}%"></div>' for w in m.get("bars", [92, 64, 78]))
        mock = f'<div class="mock"><div class="lbl">{t(m.get("label", ""))}</div>{bars}<div class="err">⚠ {t(m.get("error", ""))}</div></div>'
    return (f'{brand()}<div style="margin-top:72px"><span class="tag">{t(sl.get("tag", ""))}</span></div>'
            f'<h1 style="margin-top:44px;font-size:{sl.get("size", 80)}px">{t(sl["title"])}</h1>{mock}{lead(sl)}')


def s_list(sl):
    icon = sl.get("icon", "q")
    rows = "".join(f'<div class="row"><span class="ico {icon}">{ICON[icon]}</span><span>{t(i)}</span></div>' for i in sl["items"])
    return f'{head(sl)}<div class="card" style="margin-top:48px">{rows}</div>{lead(sl)}'


def s_steps(sl):
    cls = "num rank" if sl.get("rank") else "num"
    start = sl.get("start", 1)
    st = "".join(f'<div class="step"><div class="{cls}">{start + k}</div><div><h3>{t(i["h"])}</h3><p>{t(i.get("p", ""))}</p></div></div>'
                 for k, i in enumerate(sl["items"]))
    return f'{head(sl)}<div style="margin-top:56px">{st}</div>{lead(sl)}'


def s_grid(sl):
    cells = "".join(f'<div class="cell"><h3>{t(i["h"])}</h3><p>{t(i.get("p", ""))}</p></div>' for i in sl["items"])
    return f'{head(sl)}<div class="grid">{cells}</div>{lead(sl)}'


def s_prices(sl):
    rows = "".join(f'<div class="price"><div><div class="n">{t(i["n"])}</div><div class="d">{t(i.get("d", ""))}</div></div>'
                   f'<div class="y">{t(i["y"])}</div></div>' for i in sl["items"])
    return (f'{head(sl)}<div class="card" style="margin-top:44px;padding-top:14px;padding-bottom:14px">{rows}</div>'
            f'<div class="spacer"></div><p class="lead" style="font-size:30px">{t(sl.get("lead", ""))}</p>')


def s_qa(sl):
    qa = "".join(f'<div class="qa"><div class="qq"><b>Q</b>{t(i["q"])}</div><div class="aa">{t(i["a"])}</div></div>' for i in sl["items"])
    return f'{head(sl)}<div style="margin-top:56px">{qa}</div>{lead(sl)}'


def s_message(sl):
    return (f'{brand() if sl.get("brand") else ""}<div class="spacer"></div>'
            f'<span class="tag">{t(sl.get("tag", ""))}</span>'
            f'<div class="big" style="margin-top:40px;font-size:{sl.get("size", 96)}px">{t(sl["text"])}</div>{lead(sl)}')


def s_cta(sl):
    return (f'{brand()}<h2 style="margin-top:72px">止まったAI・自動化・<br>フォーム、直します。</h2>'
            f'<p class="lead" style="margin-top:28px">GAS／スプレッドシート／WordPress／<br>外注・自作したAIツール</p>'
            f'<div class="spacer"></div><div class="cta"><div class="bigt">DMで「診断」</div>'
            f'<div class="sm">無料診断 15分｜原因と費用の目安をお伝えします</div></div>'
            f'<p class="foot" style="margin-top:44px">エンジニア歴17年<br>運営：株式会社ドコデモどあ</p>')


KINDS = {"cover": s_cover, "list": s_list, "steps": s_steps, "grid": s_grid, "prices": s_prices,
         "qa": s_qa, "message": s_message, "cta": s_cta}
DARK_DEFAULT = {"cover", "cta", "message"}


def build_html(spec):
    slides = spec["slides"]
    n = len(slides)
    secs = []
    for i, sl in enumerate(slides, 1):
        kind = sl["kind"]
        dark = sl.get("dark", kind in DARK_DEFAULT)
        body = KINDS[kind](sl)
        secs.append(f'<section class="slide{" dark" if dark else ""}" data-n="{i}">{body}'
                    f'<div class="page">{i} / {n}</div></section>')
    js = ("<script>const n=new URLSearchParams(location.search).get('s')||'1';"
          "document.querySelector('.slide[data-n=\"'+n+'\"]').classList.add('on');</script>")
    return (f'<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><style>{CSS}</style></head>'
            f'<body>{"".join(secs)}{js}</body></html>')


def render(post_dir, reel=False):
    post_dir = Path(post_dir).resolve()
    spec = json.loads((post_dir / "post.json").read_text(encoding="utf-8"))
    page = post_dir / "_slides.html"
    page.write_text(build_html(spec), encoding="utf-8")
    from playwright.sync_api import sync_playwright
    from PIL import Image
    channel = os.environ.get("RENDER_CHANNEL")  # ローカルWindowsなら msedge
    exe = os.environ.get("RENDER_CHROMIUM_PATH")  # プリインストール済みChromiumを使う場合
    outs = []
    with sync_playwright() as p:
        if exe:
            b = p.chromium.launch(executable_path=exe)
        elif channel:
            b = p.chromium.launch(channel=channel)
        else:
            b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for i in range(1, len(spec["slides"]) + 1):
            pg.goto(page.as_uri() + f"?s={i}")
            pg.wait_for_timeout(300)
            png = post_dir / f"_{i:02d}.png"
            pg.screenshot(path=str(png))
            jpg = post_dir / f"{i:02d}.jpg"
            Image.open(png).convert("RGB").save(jpg, "JPEG", quality=92)
            png.unlink()
            outs.append(jpg)
        b.close()
    page.unlink()
    if reel or spec.get("type") == "reel":
        make_reel(post_dir, outs, spec.get("seconds_per_slide", 3))
    print("rendered:", ", ".join(o.name for o in outs))


def make_reel(post_dir, imgs, sec):
    """4:5 のスライドを 9:16(1080x1920) の紺背景に載せ、無音の音声トラック付きMP4にする。"""
    lst = post_dir / "_list.txt"
    lines = []
    for im in imgs:
        lines += [f"file '{im.name}'", f"duration {sec}"]
    lines.append(f"file '{imgs[-1].name}'")
    lst.write_text("\n".join(lines), encoding="utf-8")
    total = sec * len(imgs)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst.name,
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-vf", "scale=1080:1350,pad=1080:1920:0:285:color=0x0f1b2d,fps=30,format=yuv420p",
        "-c:v", "libx264", "-profile:v", "high", "-c:a", "aac", "-b:a", "128k",
        "-t", str(total), "-movflags", "+faststart", "reel.mp4"], cwd=post_dir, check=True)
    lst.unlink()
    print("reel: reel.mp4")


if __name__ == "__main__":
    render(sys.argv[1], reel="--reel" in sys.argv)
