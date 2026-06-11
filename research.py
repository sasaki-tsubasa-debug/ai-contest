#!/usr/bin/env python3
"""毎日のリサーチ: Gemini(Google検索grounding)でAI映像コンテストを収集し data.json を生成。
   環境変数 GEMINI_API_KEY を使用（新形式 AQ. / 旧形式 AIza のどちらでも可）。"""
import os, re, json, time, datetime, urllib.request, urllib.error, sys

KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
MAX_ITEMS = 50
today = datetime.date.today().isoformat()

if not KEY:
    sys.exit("GEMINI_API_KEY が未設定です。")

PROMPT = f"""本日は {today} です。あなたはAI映像・生成AIクリエイティブ系のコンテスト/映画祭を追う専門リサーチャーです。
Google検索を使い、いま応募可能、または近日応募開始予定の「AIを用いた映像・映画・画像・クリエイティブ作品」を対象としたコンテスト/映画祭/アワードを、世界と日本の両方から探してください。

【最重要】日本国内は規模を問わず「全て」網羅すること:
- 大規模な映画祭だけでなく、自治体・観光協会・商店街・地方イベント主催の小さなAI動画コンテスト、
  企業のPR/CM系AI動画コンテスト、ツールベンダー主催(ConoHa等)のAI生成コンテスト、
  学生向け・地域限定・賞金数万円規模のものまで、見つかったものは全て含める。
- 国内の探索は最低でも次を確認: 登竜門(compe.japandesign.ne.jp)の映像カテゴリ, Koubo(koubo.jp),
  公募データベース(koubodatabase.com), PR TIMESの「AI 動画 コンテスト」系リリース, note のAIコンテストまとめ記事,
  X(Twitter)で告知されているコンテスト(検索indexやまとめ経由で可), Peatix/connpassのAI動画コンテスト・上映イベント,
  地方紙・自治体サイトの「AI動画 募集」告知。
- 検索語のバリエーションも複数試すこと: 「AI動画コンテスト 募集」「生成AI 映像 コンテスト」「AIショートフィルム 公募」
  「AI movie contest Japan」「AIアニメ コンテスト」「AI CM コンテスト」など。
- 「AI利用可」程度の一般動画コンテストは除外し、AI利用が前提・歓迎されるものを対象とする。

海外は主要なもの中心でよい(網羅性より確度優先):
- Runway AIFF, WAIFF, Project Odyssey, AI for Good, AAIFF(Astana), BAIFF(Burano), Red Rocks AIFF,
  AI International Film Festival, Chroma Awards, melies.co/ai-film-festivals, FilmFreeway。

条件:
- 締切が本日より前に既に終了したものは除外。
- 公式・一次情報を優先し、応募開始/締切/賞金/URLは推測で埋めない(不明はnull)。
- start/deadline は分かる範囲で YYYY-MM-DD。
- region は国内なら必ず「日本」を含める(例: 日本（武蔵野市）)。
- 重複は1件にまとめる。最大 {MAX_ITEMS} 件。日本のものを優先的に枠に入れる。
出力は次スキーマのJSON配列のみ。説明文やMarkdown見出しを付けず、```json コードブロック1つだけで返すこと:
[{{"name":"…","organizer":"… or null","region":"日本（◯◯） / 国際 / 米国 など","category":"短編映画/縦型/CM/画像 など",
"start":"YYYY-MM-DD or null","deadline":"YYYY-MM-DD or null","prize":"… or null","requirement":"主な応募要件1行 or null",
"url":"公式URL or null","source":"公式/X/PR TIMES/登竜門/Koubo など","status":"募集中/まもなく開始/締切間近"}}]"""

def call_gemini():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    payload = {"contents":[{"role":"user","parts":[{"text":PROMPT}]}],
               "tools":[{"google_search":{}}], "generationConfig":{"temperature":0.4}}
    body = json.dumps(payload).encode("utf-8")
    last_err = None
    for attempt in range(5):  # 503/429(一時的な混雑)に備えて最大5回リトライ
        try:
            req = urllib.request.Request(url, data=body,
                headers={"Content-Type":"application/json",
                         "x-goog-api-key": KEY})  # 公式推奨のヘッダー認証(新AQ.キー/旧AIzaキー両対応)
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read().decode("utf-8"))
            parts = data.get("candidates",[{}])[0].get("content",{}).get("parts",[])
            return "".join(p.get("text","") for p in parts)
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 500, 503) and attempt < 4:
                wait = 20 * (attempt + 1)
                print(f"HTTP {e.code} (一時的エラーの可能性) → {wait}秒待って再試行 ({attempt+1}/5)", file=sys.stderr)
                time.sleep(wait)
                continue
            try:
                detail = e.read().decode("utf-8")[:500]
            except Exception:
                detail = ""
            raise SystemExit(f"Gemini API エラー HTTP {e.code}: {detail or e.reason}")
    raise SystemExit(f"Gemini API エラー(リトライ上限): {last_err}")

def parse(text):
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    raw = m.group(1) if m else text
    s, e = raw.find("["), raw.rfind("]")
    return json.loads(raw[s:e+1])

def normalize(c):
    keys = ["name","organizer","region","category","start","deadline","prize","requirement","url","source","status"]
    out = {k: c.get(k) for k in keys}
    # 締切で締切間近を補正
    dl = out.get("deadline")
    if dl and re.match(r"\d{4}-\d{2}-\d{2}", str(dl)):
        d = datetime.date.fromisoformat(str(dl)[:10])
        left = (d - datetime.date.today()).days
        if 0 <= left <= 30 and out.get("status") not in ("近日開始","まもなく開始"):
            out["status"] = "締切間近"
    return out

def main():
    arr = parse(call_gemini())
    contests = [normalize(c) for c in arr if isinstance(c, dict) and c.get("name")]

    def alive(c):
        dl = c.get("deadline")
        if dl:
            try: return datetime.date.fromisoformat(str(dl)[:10]) >= datetime.date.today()
            except Exception: return True
        # 締切未定のものは、初回収集から90日で自動的に落とす（陳腐化防止）
        fs = c.get("firstSeen")
        if fs:
            try:
                return (datetime.date.today() - datetime.date.fromisoformat(str(fs)[:10])).days <= 90
            except Exception: return True
        return True

    contests = [c for c in contests if alive(c)]

    # ---- 取りこぼし防止マージ ----
    # 前回までの一覧を読み込み、(1)firstSeenの引き継ぎ、(2)今日の検索で漏れた既知コンテストの温存 を行う。
    # ※「【仮】」サンプルと手動分(source=手動)は引き継がない。
    prev_list = []
    try:
        with open("data.json", encoding="utf-8") as f:
            prev_list = json.load(f).get("contests", [])
    except Exception:
        pass

    def norm_name(s):
        return re.sub(r"[\s　・,，。．()（）\[\]【】]", "", str(s or "").lower())

    seen = {norm_name(c["name"]): c for c in contests}
    for p in prev_list:
        if not p.get("name"): continue
        if "【仮】" in p["name"] or p.get("source") == "手動": continue
        k = norm_name(p["name"])
        if k in seen:
            # firstSeen は過去の値を優先して引き継ぐ
            if p.get("firstSeen"):
                seen[k]["firstSeen"] = p["firstSeen"]
        elif alive(p):
            # 今日の検索で漏れたが、まだ生きている既知コンテストは残す
            seen[k] = p

    merged = list(seen.values())
    for c in merged:
        c.setdefault("firstSeen", today)

    # 締切昇順(未定は後ろ)で安定ソートして保存
    def sort_key(c):
        dl = c.get("deadline")
        return (0, str(dl)) if dl else (1, "")
    merged.sort(key=sort_key)

    out = {"generatedAt": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M"), "contests": merged}
    with open("data.json","w",encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"wrote data.json: {len(merged)} contests (new from search: {len(contests)})")

if __name__ == "__main__":
    main()
