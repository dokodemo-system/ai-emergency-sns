"""【試作】内田さん向け SNS自動投稿のエンジン（スプレッドシート → 投稿データ → 画像）。

コマンド:
  python scripts/uchida_engine.py fetch          スプシ（GAS）から全タブを取ってきて demo/input.json に保存
  python scripts/uchida_engine.py build          設定を見て、対象日の投稿データ（post.json）を作る
      毎日入れる：投稿タブ・スライドタブのその日の行を、文言を変えずにそのまま使う → 「MANUAL <dir>」
                  その日の行が空なら「EMPTY <日付>」（終了コード 3）
      自動で作る：曜日テーマなどの材料を demo/context.json に出し、空の post.json を置く → 「AUTO <dir>」
                  （中身は定期実行の Claude が書く）
  python scripts/uchida_engine.py render <dir>   設定のデザイン見本（A/B/C）で画像を作る
  python scripts/uchida_engine.py alert          「毎日入れる」で空だったことを、スプシの実行ログに書く

環境変数: UCHIDA_GAS_URL（スプシの Web アプリの URL）, UCHIDA_TOKEN（合言葉）
"""
import datetime
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "demo" / "input.json"
CONTEXT = ROOT / "demo" / "context.json"
DESIGN_CSS = {"A": "templates/base.css", "B": "templates/themes/b-pop.css", "C": "templates/themes/c-vivid.css"}
TARGETS = ["Instagram", "X", "Threads", "公式LINE"]
WEEK = "月火水木金土日"
LIST_ICON = {"箇条書き（!）": "x", "箇条書き（✓）": "v", "箇条書き（?）": "q"}


# ---------- スプシとのやり取り ----------
def gas_get():
    url = f"{os.environ['UCHIDA_GAS_URL']}?api=data&token={os.environ['UCHIDA_TOKEN']}"
    with urllib.request.urlopen(url, timeout=90) as r:
        d = json.loads(r.read().decode("utf-8"))
    if not d.get("ok"):
        sys.exit(f"スプシの読み込みに失敗: {d}")
    return d["data"]


def gas_log(**payload):
    body = json.dumps({"action": "log", "token": os.environ["UCHIDA_TOKEN"], **payload}).encode("utf-8")
    req = urllib.request.Request(os.environ["UCHIDA_GAS_URL"], data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode("utf-8", "replace")


def load():
    return json.loads(INPUT.read_text(encoding="utf-8"))


# ---------- 設定の読み方 ----------
def norm_date(v):
    m = re.match(r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})", str(v or "").strip())
    return f"{m[1]}/{int(m[2]):02d}/{int(m[3]):02d}" if m else ""


def target_date(d):
    return norm_date(d["settings"].get("（テスト用）対象日")) or d["today"]


def design_key(d):
    return (str(d["settings"].get("デザイン見本") or "A")[:1]).upper()


def targets(d):
    return [t for t in TARGETS if d["settings"].get("投稿先：" + t) is True]


def mode_of(d):
    return d["settings"].get("投稿の作り方") or "自動で作る"


def out_dir(date, mode):
    return ROOT / "posts-uchida" / f"{date.replace('/', '-')}-{'manual' if mode == '毎日入れる' else 'auto'}"


# ---------- スライドの行 → 画像の型 ----------
def lines(s):
    return [re.sub(r"^\s*(?:[・\-]|\d+\s*[.．、)])\s*", "", x).strip() for x in str(s or "").splitlines() if x.strip()]


def parts(x, n):
    p = [s.strip() for s in x.split("／")]
    return (p + [""] * n)[:n]


def mark(s):
    # シートでは全角の ［［強調］］ ＊＊太字＊＊ でも書けるようにする
    return str(s or "").replace("［［", "[[").replace("］］", "]]").replace("＊＊", "**")


def slide_from_row(r):
    kind, tag, title, body, lead, mock = (mark(r.get(k, "")) for k in ("型", "小見出し", "見出し", "中身", "下のひと言", "画面の絵"))
    if kind == "表紙":
        s = {"kind": "cover", "tag": tag, "title": title, "lead": lead}
        if mock:
            label, err = parts(mock, 2)
            s["mock"] = {"label": label, "bars": [100, 100, 0], "error": err}
        return s
    if kind in LIST_ICON:
        return {"kind": "list", "tag": tag, "title": title, "items": lines(body), "icon": LIST_ICON[kind], "lead": lead}
    if kind in ("番号つき", "4マス"):
        items = [dict(zip(("h", "p"), parts(x, 2))) for x in lines(body)]
        return {"kind": "steps" if kind == "番号つき" else "grid", "tag": tag, "title": title, "items": items, "lead": lead}
    if kind == "料金表":
        return {"kind": "prices", "tag": tag, "title": title, "items": [dict(zip(("n", "d", "y"), parts(x, 3))) for x in lines(body)], "lead": lead}
    if kind == "Q&A":
        return {"kind": "qa", "tag": tag, "title": title, "items": [dict(zip(("q", "a"), parts(x, 2))) for x in lines(body)]}
    if kind == "大きな一言":
        return {"kind": "message", "tag": tag, "text": title, "lead": lead}
    return {"kind": "cta"}


# ---------- コマンド ----------
def cmd_fetch():
    INPUT.parent.mkdir(exist_ok=True)
    INPUT.write_text(json.dumps(gas_get(), ensure_ascii=False, indent=1), encoding="utf-8")
    d = load()
    print(f"読み込み: 投稿の作り方={mode_of(d)} デザイン={design_key(d)} 投稿先={targets(d)} 対象日={target_date(d)}")


def cmd_build():
    d = load()
    date, mode = target_date(d), mode_of(d)
    meta = {"date": date.replace("/", "-"), "mode": mode, "design": design_key(d), "targets": targets(d)}
    out = out_dir(date, mode)
    if mode == "毎日入れる":
        post = next((x for x in d["posts"] if x["投稿日"] == date), None)
        rows = sorted((x for x in d["slides"] if x["投稿日"] == date), key=lambda x: int(x["枚目"] or 0))
        if not post or not rows:
            print(f"EMPTY {date}")
            sys.exit(3)
        spec = {**meta, "source": "sheet", "type": "reel" if post["形式"] == "リール" else "carousel", "theme": post["テーマ"],
                "slides": [slide_from_row(r) for r in rows], "caption_ig": post["Instagram の本文"],
                "hashtags": [h.lstrip("#＃") for h in re.split(r"[\s、,]+", post["ハッシュタグ"]) if h.strip("#＃")],
                "x_text": post["X の本文"]}
        out.mkdir(parents=True, exist_ok=True)
        (out / "post.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"MANUAL {out.relative_to(ROOT).as_posix()}")
        return
    wd = WEEK[datetime.date(*map(int, date.split("/"))).weekday()]
    theme = next((x for x in d["themes"] if x["曜日"] == wd), {})
    CONTEXT.write_text(json.dumps({**meta, "weekday": wd, "theme": theme, "base": d["base"],
                                   "rules": [r["ルール"] for r in d["rules"]], "facts": d["facts"]}, ensure_ascii=False, indent=1), encoding="utf-8")
    out.mkdir(parents=True, exist_ok=True)
    skeleton = {**meta, "source": "theme:" + wd, "type": "reel" if theme.get("形式") == "リール" else "carousel",
                "theme": "", "slides": [], "caption_ig": "", "hashtags": [], "x_text": ""}
    (out / "post.json").write_text(json.dumps(skeleton, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"AUTO {out.relative_to(ROOT).as_posix()}")


def cmd_render(post_dir):
    sys.path.insert(0, str(ROOT / "scripts"))
    import render  # 本番と同じ画像づくり。デザインの型（CSS）だけ差し替える
    from playwright.sync_api import sync_playwright
    from PIL import Image

    post_dir = Path(post_dir).resolve()
    spec = json.loads((post_dir / "post.json").read_text(encoding="utf-8"))
    render.CSS = (ROOT / DESIGN_CSS.get(spec.get("design", "A"), DESIGN_CSS["A"])).read_text(encoding="utf-8")
    page = post_dir / "_slides.html"
    page.write_text(render.build_html(spec), encoding="utf-8")
    outs = []
    with sync_playwright() as p:
        ch = os.environ.get("RENDER_CHANNEL")  # 手元の Windows なら msedge
        b = p.chromium.launch(channel=ch) if ch else p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1350})
        for i in range(1, len(spec["slides"]) + 1):
            pg.goto(page.as_uri() + f"?s={i}")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(800)
            png = post_dir / f"_{i:02d}.png"
            pg.screenshot(path=str(png))
            jpg = post_dir / f"{i:02d}.jpg"
            Image.open(png).convert("RGB").save(jpg, "JPEG", quality=92)
            png.unlink()
            outs.append(jpg)
        b.close()
    page.unlink()
    if spec.get("type") == "reel":
        render.make_reel(post_dir, outs, 3)
    print("rendered:", ", ".join(o.name for o in outs))


def cmd_alert():
    d = load()
    date = target_date(d)
    print(gas_log(date=date, mode=mode_of(d), design=design_key(d), result="アラート：その日の投稿が空のため、投稿しませんでした",
                  line="内田さんへ LINE でアラート（試作ではイメージ）", memo="投稿タブ・スライドタブに、その日の行がありません"))


if __name__ == "__main__":
    c = sys.argv[1:]
    if c[:1] == ["fetch"]:
        cmd_fetch()
    elif c[:1] == ["build"]:
        cmd_build()
    elif c[:1] == ["render"] and len(c) == 2:
        cmd_render(c[1])
    elif c[:1] == ["alert"]:
        cmd_alert()
    else:
        sys.exit(__doc__)
