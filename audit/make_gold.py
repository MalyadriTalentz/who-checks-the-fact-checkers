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

# Enriched short sheet (DEVIATIONS D7): 30 random notes plus 30 notes Judge A flagged DOES_NOT_SUPPORT, mixed blind.
# Only readable (fetched) links, so every row is one a judge also saw. No flag column; order shuffled by hash.
ok = lambda u: json.loads(pathlib.Path("cache/pages/" + hashlib.sha1(u.encode()).hexdigest() + ".json").read_text())["status"] == "ok"
flagged = {json.loads(p.read_text())["noteId"] for p in pathlib.Path("audit/judgments/claude-cli__sonnet").glob("*.json")
           if json.loads(p.read_text())["label"] == "DOES_NOT_SUPPORT"}
readable = sorted((r for r in sample if any(ok(u) for u in text[r["noteId"]]["urls"])), key=key)
pick_f = [r for r in readable if r["noteId"] in flagged][:30]
pick_r = [r for r in readable if r["noteId"] not in {x["noteId"] for x in pick_f}][:30]
short = []
for r in sorted(pick_f + pick_r, key=key):
    n = text[r["noteId"]]
    post = json.loads(pathlib.Path(f"cache/posts/{n['tweetId']}.json").read_text())["text"]
    short += [[r["noteId"], f"https://x.com/i/status/{n['tweetId']}", post, n["summary"], u, "", ""] for u in dict.fromkeys(n["urls"]) if ok(u)]
with open("cache/gold_sheet_v2.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["noteId", "post_link", "post_text", "note_text", "cited_link", "label (SUPPORTS / PARTIAL / DOES_NOT_SUPPORT / UNCHECKABLE)", "comment"])
    w.writerows(short)
json.dump({"flagged": [r["noteId"] for r in pick_f], "random": [r["noteId"] for r in pick_r]}, open("audit/gold_v2_design.json", "w"))
print("v2:", len(pick_f), "flagged +", len(pick_r), "random notes,", len(short), "rows")
