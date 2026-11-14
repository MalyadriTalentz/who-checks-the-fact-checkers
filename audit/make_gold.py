"""Build the blind human labelling sheet: 150 notes (75 AI, 75 human), one row per cited link.

Usage: python audit/make_gold.py  -> cache/gold_sheet.csv (give a separate copy to each labeller)
The sheet has no author-type column and no judge output. Row order is shuffled by hash.
"""
import csv, hashlib, json, pathlib

sample = list(csv.DictReader(open("audit/sample.csv")))
text = {d["noteId"]: d for d in map(json.loads, open("cache/sample_text.jsonl"))}
key = lambda r: hashlib.md5((r["noteId"] + "gold20261115").encode()).hexdigest()
chosen = [r for g in ("ai", "human") for r in sorted((r for r in sample if r["grp"] == g), key=key)[:75]]
rows = []
for r in sorted(chosen, key=key):
    n = text[r["noteId"]]
    post = json.loads(pathlib.Path(f"cache/posts/{n['tweetId']}.json").read_text())["text"]
    for u in dict.fromkeys(n["urls"]) or [""]:
        rows.append([r["noteId"], f"https://x.com/i/status/{n['tweetId']}", post, n["summary"], u, "", ""])
with open("cache/gold_sheet.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["noteId", "post_link", "post_text", "note_text", "cited_link",
                "label (SUPPORTS / PARTIAL / DOES_NOT_SUPPORT / DEAD / UNCHECKABLE)", "comment"])
    w.writerows(rows)
print(len(chosen), "notes,", len(rows), "rows")
