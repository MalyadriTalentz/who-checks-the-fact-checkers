"""Fetch every cited URL in the sample (live, then Internet Archive) and each post's text (X oEmbed).

Usage: python audit/fetch.py   -> cache/pages/<sha1>.json, cache/posts/<tweetId>.json, audit/fetch_log.csv
Resumable: anything already cached is skipped. Standard library only.
"""
import csv, hashlib, html, json, pathlib, re, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
      "Accept-Language": "en;q=0.9,*;q=0.5"}
# shortcut: fixed list of hosts whose pages cannot be read as text without a login or a video player;
# upgrade to transcript/API fetching if the uncheckable share needs to come down.
UNCHECKABLE = ("x.com", "twitter.com", "t.co", "instagram.com", "facebook.com", "fb.watch", "tiktok.com",
               "youtube.com", "youtu.be", "threads.net", "threads.com", "t.me", "linkedin.com", "truthsocial.com",
               "bsky.app", "twitch.tv", "vimeo.com", "rumble.com")
PAGES, POSTS = pathlib.Path("cache/pages"), pathlib.Path("cache/posts")
PAGES.mkdir(parents=True, exist_ok=True); POSTS.mkdir(parents=True, exist_ok=True)
MAX_CHARS = 20000


def get(url, timeout=25):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.status, r.headers.get("Content-Type", ""), r.read(3_000_000)


def to_text(raw, ctype):
    m = re.search(r"charset=([\w-]+)", ctype)
    s = raw.decode(m.group(1) if m else "utf-8", errors="replace")
    title = re.search(r"<title[^>]*>(.*?)</title>", s, re.S | re.I)
    s = re.sub(r"<(script|style|noscript|svg|nav|footer|header)\b.*?</\1>", " ", s, flags=re.S | re.I)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return (html.unescape(title.group(1)).strip() if title else ""), re.sub(r"\s+", " ", s).strip()


def host(url):
    return urllib.parse.urlparse(url).netloc.lower().removeprefix("www.").removeprefix("m.").removeprefix("mobile.")


def fetch_page(url):
    out = PAGES / (hashlib.sha1(url.encode()).hexdigest() + ".json")
    if out.exists():
        return json.loads(out.read_text())
    rec = {"url": url, "host": host(url), "status": None, "source": None, "title": "", "text": "", "error": ""}
    if any(rec["host"] == h or rec["host"].endswith("." + h) for h in UNCHECKABLE):
        rec["status"] = "uncheckable_host"
    else:
        for source, target in (("live", url), ("archive", "https://web.archive.org/web/2026id_/" + url)):
            try:
                code, ctype, raw = get(target)
                if "html" not in ctype and "text" not in ctype:
                    rec.update(status="non_text", source=source, error=ctype); break
                title, text = to_text(raw, ctype)
                if len(text) < 400:  # login walls, JS shells and consent pages come back nearly empty
                    rec["error"] += f"{source}: thin page ({len(text)} chars); "; continue
                rec.update(status="ok", source=source, title=title[:300], text=text[:MAX_CHARS]); break
            except Exception as e:  # dead link, block or timeout: try the archive, then give up
                rec["error"] += f"{source}: {type(e).__name__} {getattr(e, 'code', '')}; "
        rec["status"] = rec["status"] or "unreachable"
    out.write_text(json.dumps(rec))
    return rec


def fetch_post(tweet_id):
    out = POSTS / f"{tweet_id}.json"
    if out.exists():
        return json.loads(out.read_text())
    rec = {"tweetId": tweet_id, "text": "", "error": ""}
    try:
        q = urllib.parse.quote(f"https://twitter.com/i/status/{tweet_id}", safe="")
        d = json.loads(get(f"https://publish.twitter.com/oembed?url={q}&omit_script=1&dnt=1")[2])
        rec["text"] = to_text(d.get("html", "").encode(), "")[1]
    except Exception as e:
        rec["error"] = f"{type(e).__name__} {getattr(e, 'code', '')}"
    out.write_text(json.dumps(rec))
    return rec


def archive_pass():
    """Second pass, one request at a time (the archive refuses bursts): settle every 'unreachable' page as
    ok (archive copy read), dead (live 404/410/DNS failure and no archive copy) or blocked (anything else)."""
    import time
    for f in sorted(PAGES.glob("*.json")):
        rec = json.loads(f.read_text())
        if rec["status"] != "unreachable":
            continue
        snap = None
        for attempt in range(4):
            try:
                q = urllib.parse.quote(rec["url"], safe="")
                d = json.loads(get(f"https://archive.org/wayback/available?url={q}&timestamp=20261101")[2])
                snap = d.get("archived_snapshots", {}).get("closest", {}).get("url", "")
                break
            except Exception:
                time.sleep(5 * (attempt + 1))
        rec["archive_snapshot"] = snap  # None = the archive could not be asked
        if snap:
            try:
                time.sleep(1)
                code, ctype, raw = get(re.sub(r"/web/(\d+)/", r"/web/\1id_/", snap.replace("http://", "https://", 1)), timeout=40)
                title, text = to_text(raw, ctype)
                if len(text) >= 400:
                    rec.update(status="ok", source="archive", title=title[:300], text=text[:MAX_CHARS])
            except Exception as e:
                rec["error"] += f"archive2: {type(e).__name__} {getattr(e, 'code', '')}; "
        if rec["status"] == "unreachable":
            gone = re.search(r"live: (HTTPError (404|410)|URLError)", rec["error"])
            rec["status"] = "dead" if (gone and snap == "") else "blocked"
        f.write_text(json.dumps(rec))
        time.sleep(1)


if __name__ == "__main__":
    notes = [json.loads(l) for l in open("cache/sample_text.jsonl")]
    urls = sorted({u for n in notes for u in n["urls"]})
    with ThreadPoolExecutor(24) as ex:
        pages = list(ex.map(fetch_page, urls))
        posts = list(ex.map(fetch_post, sorted({n["tweetId"] for n in notes})))
    archive_pass()
    pages = [fetch_page(u) for u in urls]
    with open("audit/fetch_log.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["url_sha1", "host", "status", "source", "chars", "error"])
        for p in pages:
            w.writerow([hashlib.sha1(p["url"].encode()).hexdigest(), p["host"], p["status"], p["source"], len(p["text"]), p["error"]])
    count = lambda xs: {k: xs.count(k) for k in sorted(set(xs))}
    print("pages", count([p["status"] for p in pages]), "| posts with text", sum(bool(p["text"]) for p in posts), "of", len(posts))
