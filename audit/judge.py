"""Run the frozen judge prompt on every (note, readable cited page) pair, once per judge model.

Usage: OPENROUTER_API_KEY=... python audit/judge.py vendor/model-a vendor/model-b [--limit N]
Writes audit/judgments/<model>/<noteId>__<url sha1>.json (raw reply + parsed label). Resumable.
Judges never see whether a note is AI- or human-written.
"""
import hashlib, json, os, pathlib, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

PROMPT = pathlib.Path("audit/judge_prompt.md").read_text()
LABELS = {"SUPPORTS", "PARTIAL", "DOES_NOT_SUPPORT", "UNCHECKABLE"}
norm = lambda s: re.sub(r"\W+", " ", s).lower().strip()


def ask(model, user):
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": 2000,
                       "messages": [{"role": "system", "content": PROMPT}, {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", body, {
        "Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"], "Content-Type": "application/json"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except Exception as e:
            err = f"{type(e).__name__} {getattr(e, 'code', '')}"
            time.sleep(3 * (attempt + 1))
    return {"error": err}


def judge(job):
    model, note, page, post = job
    out = pathlib.Path("audit/judgments") / model.replace("/", "__") / f"{note['noteId']}__{hashlib.sha1(page['url'].encode()).hexdigest()[:12]}.json"
    if out.exists():
        return
    user = (f"POST:\n{post or '(not available)'}\n\nNOTE:\n{note['summary']}\n\n"
            f"CITED PAGE ({page['url']})\nTITLE: {page['title']}\nTEXT:\n{page['text']}")
    reply = ask(model, user)
    if "choices" not in reply:  # transport or billing failure: leave uncached so a rerun retries it
        print("failed:", model, reply.get("error"), flush=True)
        return
    rec = {"noteId": note["noteId"], "url": page["url"], "model": model, "raw": reply, "label": "JUDGE_ERROR", "quote_found": None}
    try:
        text = reply["choices"][0]["message"]["content"]
        parsed = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
        rec.update(parsed=parsed, label=parsed["label"] if parsed.get("label") in LABELS else "JUDGE_ERROR")
        if rec["label"] in ("SUPPORTS", "PARTIAL"):
            # Deterministic check fixed before any judging: a support label whose quote is not on the page is not counted as support.
            rec["quote_found"] = bool(parsed.get("quote")) and norm(parsed["quote"]) in norm(page["text"])
            if not rec["quote_found"]:
                rec["label"] = "UNVERIFIED_QUOTE"
    except Exception:
        pass
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec))


if __name__ == "__main__":
    args = sys.argv[1:]
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else None
    models = [a for a in args if "/" in a]
    notes = [json.loads(l) for l in open("cache/sample_text.jsonl")][:limit]
    jobs = []
    for n in notes:
        post = json.loads(pathlib.Path(f"cache/posts/{n['tweetId']}.json").read_text())["text"]
        for u in dict.fromkeys(n["urls"]):
            page = json.loads(pathlib.Path("cache/pages/" + hashlib.sha1(u.encode()).hexdigest() + ".json").read_text())
            if page["status"] == "ok":
                jobs += [(m, n, page, post) for m in models]
    print(len(jobs), "judgments to make (cached ones are skipped)")
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(judge, jobs))
