"""
値上げ予報 - AI記事自動生成スクリプト
GitHub Actions が毎週月曜に自動実行します。
手動実行: pip install anthropic requests && python generate_articles.py
"""
import os, json, datetime, textwrap, requests
from pathlib import Path

OUTPUT_DIR = Path("articles")
OUTPUT_DIR.mkdir(exist_ok=True)

API_KEY    = os.environ.get("ANTHROPIC_API_KEY", "")
NOW        = datetime.datetime.now()
THIS_MONTH = NOW.strftime("%-m月")
TODAY_STR  = NOW.strftime("%Y年%m月%d日")

def fetch_market():
    data = {"usdjpy": 151.80, "wheat_up": "+4.2", "soy_up": "+2.8", "wti": 78.4, "labor": 66, "fetched": TODAY_STR, "source": "フォールバック値"}
    for url, parser in [
        ("https://open.er-api.com/v6/latest/USD",               lambda d: round(d["rates"]["JPY"], 2) if d.get("result") == "success" else None),
        ("https://api.frankfurter.dev/v2/rates?base=USD&quotes=JPY", lambda d: round(d[0]["rate"], 2) if isinstance(d, list) and d else None),
    ]:
        try:
            r = requests.get(url, timeout=7)
            val = parser(r.json())
            if val:
                data["usdjpy"] = val
                data["source"] = url.split("/")[2]
                print(f"✅ 為替: {val}円 ({data['source']})")
                break
        except Exception as e:
            print(f"⚠ {url}: {e}")
    return data

def call_claude(prompt):
    if not API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY が設定されていません")
    import anthropic
    client = anthropic.Anthropic(api_key=API_KEY)
    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=2000, messages=[{"role": "user", "content": prompt}])
    return msg.content[0].text

WRAPPER = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@700;900&family=Noto+Sans+JP:wght@400;500;700&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Noto Sans JP',sans-serif;background:#f1f5f9;color:#1e293b;line-height:1.8;font-size:15px}}
.site-hdr{{background:#002B80;padding:12px 16px;display:flex;align-items:center;justify-content:space-between}}
.site-hdr a{{font-family:'Noto Serif JP',serif;font-size:16px;font-weight:900;color:#fff;text-decoration:none}}
.site-hdr-date{{font-size:10px;color:rgba(255,255,255,.4)}}
.art-wrap{{max-width:760px;margin:32px auto;padding:0 16px 40px}}
article{{background:#fff;border-radius:12px;padding:32px;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
article h1,article h2{{font-family:'Noto Serif JP',serif;font-weight:700;margin-bottom:14px;margin-top:24px;color:#1e293b;line-height:1.4}}
article h1{{font-size:24px;border-bottom:3px solid #002B80;padding-bottom:12px}}
article h2{{font-size:19px}}
article p{{margin-bottom:14px;color:#334155}}
article ul,article ol{{margin:0 0 14px 20px}}
article li{{margin-bottom:6px;color:#334155}}
article a{{color:#002B80;text-decoration:underline}}
.aff-cta{{display:inline-block;background:#c0392b;color:#fff;text-decoration:none;padding:10px 20px;border-radius:6px;font-weight:700;margin:4px 4px 4px 0;font-size:14px;transition:background .15s}}
.aff-cta:hover{{background:#a93226}}
.back-link{{display:inline-flex;align-items:center;gap:6px;color:#64748b;font-size:12px;margin-bottom:20px;text-decoration:none}}
.back-link:hover{{color:#002B80}}
.site-ftr{{background:#002B80;color:rgba(255,255,255,.4);text-align:center;padding:20px;font-size:11px;margin-top:32px}}
.aff-disc{{background:rgba(192,57,43,.07);border:0.5px solid rgba(192,57,43,.2);border-radius:6px;padding:10px 14px;font-size:10px;color:#64748b;margin-top:20px;line-height:1.7}}
</style>
</head>
<body>
<header class="site-hdr">
  <a href="../index.html">値上げ予報</a>
  <span class="site-hdr-date">{date}</span>
</header>
<div class="art-wrap">
  <a class="back-link" href="../index.html">← トップへ戻る</a>
{body}
  <div class="aff-disc">PR：当サイトはアフィリエイトプログラムに参加しています。</div>
</div>
<footer class="site-ftr">© 2026 値上げ予報 All rights reserved.</footer>
</body>
</html>"""

def save_article(slug, title, desc, body):
    body = body.replace("```html", "").replace("```", "").strip()
    html = WRAPPER.format(title=title, desc=desc, date=TODAY_STR, body=body)
    path = OUTPUT_DIR / f"{slug}.html"
    path.write_text(html, encoding="utf-8")
    print(f"💾 {path}")

def update_index(new_articles):
    path = Path("articles-index.json")
    existing = []
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
    slugs = {a["slug"] for a in new_articles}
    merged = new_articles + [a for a in existing if a["slug"] not in slugs]
    path.write_text(json.dumps(merged[:50], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"📋 articles-index.json: {len(merged)} 件")

def main():
    print("=" * 50)
    print(f"  値上げ予報 AI記事生成 - {TODAY_STR}")
    print("=" * 50)
    m = fetch_market()
    print(f"📊 {m}")

    tasks = [
        {
            "slug": f"{NOW.strftime('%Y%m')}-neage-list",
            "title": f"{THIS_MONTH}値上げ一覧｜食品・日用品・光熱費まとめ",
            "desc": f"{THIS_MONTH}に値上がりする食品・日用品・光熱費の一覧。円安{m['usdjpy']}円台の影響で家計直撃。",
            "prompt": textwrap.dedent(f"""
                あなたはSEOに強い家計節約の専門ライターです。
                {THIS_MONTH}の値上げ一覧記事を日本語HTMLで書いてください。
                【データ（{m['fetched']}時点）】
                - 円/ドル: {m['usdjpy']}円 - 小麦: {m['wheat_up']}% - 大豆: {m['soy_up']}% - 人件費由来: {m['labor']}%
                構成: リード文→カテゴリ別一覧（食品・日用品・光熱費・外食）→まとめ
                末尾に「<a class='aff-cta' href='#'>Amazonでまとめ買い →</a>」のCTAを入れること。
                800〜1000字。HTMLのみ(<article>タグ)。余計な説明不要。
            """).strip(),
        },
        {
            "slug": f"{NOW.strftime('%Y%m')}-buy-ranking",
            "title": f"{THIS_MONTH}版・値上げ前に今すぐ買うべきもの ランキング10選",
            "desc": f"値上げが迫る{THIS_MONTH}、今のうちに買い溜めすべき保存食・日用品のランキング。",
            "prompt": textwrap.dedent(f"""
                あなたはSEOに強い家計節約の専門ライターです。
                「{THIS_MONTH}版・値上げ前に今すぐ買うべきもの ランキング10選」を日本語HTMLで書いてください。
                円安{m['usdjpy']}円、小麦{m['wheat_up']}%上昇のデータを根拠に。保存が効く商品を中心に。
                各商品に「<a class='aff-cta' href='#'>Amazonで確認 →</a>」を入れること。
                900〜1200字。HTMLのみ(<article>タグ)。余計な説明不要。
            """).strip(),
        },
        {
            "slug": f"{NOW.strftime('%Y%m%d')}-fx-analysis",
            "title": f"円安{m['usdjpy']}円台が家計に与える影響【{TODAY_STR}時点】",
            "desc": f"ドル円{m['usdjpy']}円台の影響を解説。今後3〜6ヶ月で値上がりする品目と家計防衛策。",
            "prompt": textwrap.dedent(f"""
                あなたはSEOに強い経済解説ライターです。
                為替{m['usdjpy']}円が家計に与える影響解説記事を日本語HTMLで書いてください。
                構成: 現状説明→3〜6ヶ月後の値上げ品目予測→今できる家計防衛策3選
                「コスト上昇から価格転嫁まで3〜6ヶ月のタイムラグがある」という説明を必ず含めること。
                800〜1000字。HTMLのみ(<article>タグ)。余計な説明不要。
            """).strip(),
        },
    ]

    generated = []
    for task in tasks:
        print(f"\n✍️  {task['title']}")
        try:
            body = call_claude(task["prompt"])
            save_article(task["slug"], task["title"], task["desc"], body)
            generated.append({"slug": task["slug"], "title": task["title"], "desc": task["desc"], "type": task.get("type", "monthly_list"), "date": TODAY_STR, "usdjpy": m["usdjpy"]})
            print(f"✅ 完了")
        except Exception as e:
            print(f"❌ {e}")

    if generated:
        update_index(generated)

    print(f"\n🎉 完了: {len(generated)}件生成")

if __name__ == "__main__":
    main()
