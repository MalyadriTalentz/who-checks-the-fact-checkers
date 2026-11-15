"""Run the frozen judge prompt on every (note, readable cited page) pair, once per judge model.

Usage: python audit/judge.py claude-cli/sonnet codex-cli/gpt-5.6-terra [--limit N]
Writes audit/judgments/<model>/<noteId>__<url sha1>.json (raw reply + parsed label). Resumable.
Judges never see whether a note is AI- or human-written.
"""
import hashlib, json, os, pathlib, re, subprocess, sys, tempfile, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

PROMPT = pathlib.Path("audit/judge_prompt.md").read_text()
LABELS = {"SUPPORTS", "PARTIAL", "DOES_NOT_SUPPORT", "UNCHECKABLE"}
norm = lambda s: re.sub(r"\W+", " ", s).lower().strip()


def ask(model, user):
    """Both judges run through local command-line clients on the author's own subscriptions (see DEVIATIONS D2).
    No tools are given to the Claude client; the Codex client runs read-only in an empty directory."""
    for attempt in range(3):
        try:
            if model.startswith("adaption/"):  # sponsor API, temperature 0; reads ADAPTION_API_KEY from the environment
                req = urllib.request.Request("https://api.prod.adaptionlabs.ai/api/v1/responses", json.dumps({
                    "model": model.split("/")[1], "instructions": PROMPT, "input": user, "temperature": 0,
                    "max_output_tokens": 16000, "stream": True}).encode(), {"Authorization": "Bearer " + os.environ["ADAPTION_API_KEY"],
                                                                            "Content-Type": "application/json"})
                text, d = "", {}  # streamed so long replies are not cut off by the gateway timeout (DEVIATIONS D6)
                with urllib.request.urlopen(req, timeout=900) as r:
                    for line in r:
                        line = line.decode().strip()
                        if not line.startswith("data:") or line[5:].strip() == "[DONE]":
                            continue
                        e = json.loads(line[5:])
                        if e.get("type") == "response.output_text.delta":
                            text += e.get("delta", "")
                        elif e.get("type") in ("response.completed", "response.incomplete", "response.failed"):
                            d = e.get("response", {})
                if not text:
                    raise RuntimeError(f"empty reply, status {d.get('status')}")
                return {"choices": [{"message": {"content": text}}], "usage": d.get("usage")}
            if model.startswith("claude-cli/"):
                r = subprocess.run(["claude", "-p", "--model", model.split("/")[1], "--system-prompt", PROMPT, "--tools", "",
                                    "--strict-mcp-config", "--no-session-persistence", "--setting-sources", "", "--output-format", "json"],
                                   input=user, capture_output=True, text=True, timeout=300)
                d = json.loads(r.stdout)
                if d.get("is_error"):
                    raise RuntimeError(str(d.get("result"))[:200])
                return {"choices": [{"message": {"content": d["result"]}}], "served_by": list((d.get("modelUsage") or {}).keys())}
            with tempfile.TemporaryDirectory() as tmp:
                r = subprocess.run(["codex", "exec", "--skip-git-repo-check", "--ephemeral", "-s", "read-only", "-C", tmp,
                                    "-m", model.split("/")[1], "-o", tmp + "/out.txt", "-"],
                                   input=PROMPT + "\n-----\n" + user, capture_output=True, text=True, timeout=600)
                return {"choices": [{"message": {"content": pathlib.Path(tmp + "/out.txt").read_text()}}]}
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:200]}"
            time.sleep(20 * (attempt + 1))
    return {"error": err}


def judge(job):
    model, note, page, post = job
    out = pathlib.Path(OUT_DIR) / model.replace("/", "__") / f"{note['noteId']}__{hashlib.sha1(page['url'].encode()).hexdigest()[:12]}.json"
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


OUT_DIR = "audit/judgments"


def control_jobs(notes, models, n):
    """Negative control (DEVIATIONS D4): each note is paired with a readable page cited by a note on a different post.
    A sound judge should almost never call such a page support, so the SUPPORTS/PARTIAL share here is its false-support rate."""
    h = lambda x: hashlib.md5((x + "control20261115").encode()).hexdigest()
    pages = []
    for nt in notes:
        for u in dict.fromkeys(nt["urls"]):
            pg = json.loads(pathlib.Path("cache/pages/" + hashlib.sha1(u.encode()).hexdigest() + ".json").read_text())
            if pg["status"] == "ok":
                pages.append((nt["tweetId"], pg))
    pages.sort(key=lambda tp: h(tp[1]["url"]))
    jobs = []
    for i, nt in enumerate(sorted(notes, key=lambda x: h(x["noteId"]))[:n]):
        tweet, pg = next(tp for tp in pages[i * 7 % len(pages):] + pages if tp[0] != nt["tweetId"])
        post = json.loads(pathlib.Path(f"cache/posts/{nt['tweetId']}.json").read_text())["text"]
        jobs += [(m, nt, pg, post) for m in models]
    return jobs


if __name__ == "__main__":
    args = sys.argv[1:]
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else None
    models = [a for a in args if "/" in a]
    notes = [json.loads(l) for l in open("cache/sample_text.jsonl")][:limit]
    jobs = []
    if "--control" in args:
        OUT_DIR = "audit/control"
        jobs = control_jobs(notes, models, int(args[args.index("--control") + 1]))
        notes = []
    for n in notes:
        post = json.loads(pathlib.Path(f"cache/posts/{n['tweetId']}.json").read_text())["text"]
        for u in dict.fromkeys(n["urls"]):
            page = json.loads(pathlib.Path("cache/pages/" + hashlib.sha1(u.encode()).hexdigest() + ".json").read_text())
            if page["status"] == "ok":
                jobs += [(m, n, page, post) for m in models]
    print(len(jobs), "judgments to make (cached ones are skipped)")
    with ThreadPoolExecutor(int(os.environ.get("JUDGE_WORKERS", 4))) as ex:
        list(ex.map(judge, jobs))
