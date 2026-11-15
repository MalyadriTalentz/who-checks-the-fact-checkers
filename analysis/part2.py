"""Parts 2 and 3 (PREREG.md sections 6-7): citation support and rater blindness on the 800-note sample.

Usage: python analysis/part2.py  -> results/part2.json, results/audit_labels.csv, results/unsupported_examples.csv
Human labels, when present, are read from audit/gold_labels_*.csv (one file per labeller, columns noteId,cited_link,label).
"""
import csv, glob, hashlib, json, pathlib, collections
import numpy as np

A, B, C = "claude-cli__sonnet", "adaption__qwen3.5-397b", "adaption__glm-5.2"  # see DEVIATIONS D5
SEED, NB = 20261115, 2000
rng = np.random.default_rng(SEED)
sample = {r["noteId"]: r for r in csv.DictReader(open("audit/sample.csv"))}
text = {d["noteId"]: d for d in map(json.loads, open("cache/sample_text.jsonl"))}
sha = lambda u: hashlib.sha1(u.encode()).hexdigest()
page = lambda u: json.loads(pathlib.Path(f"cache/pages/{sha(u)}.json").read_text())


def url_label(judge, note_id, u):
    st = page(u)["status"]
    if st == "dead":
        return "DEAD"
    if st != "ok":
        return "UNCHECKABLE"
    f = pathlib.Path(f"audit/judgments/{judge}/{note_id}__{sha(u)[:12]}.json")
    if not f.exists():
        return "MISSING"
    lab = json.loads(f.read_text())["label"]
    return lab if lab in ("SUPPORTS", "PARTIAL", "DOES_NOT_SUPPORT") else "UNCHECKABLE"  # incl. UNVERIFIED_QUOTE


def note_label(labels):
    checkable = [l for l in labels if l in ("SUPPORTS", "PARTIAL", "DOES_NOT_SUPPORT")]
    if "MISSING" in labels:
        return "missing"
    if "DOES_NOT_SUPPORT" in checkable:
        return "unsupported"
    return "supported" if checkable else "no_checkable"


def kappa(x, y):
    cats = sorted(set(x) | set(y)); n = len(x)
    if n == 0: return None
    po = sum(a == b for a, b in zip(x, y)) / n
    pe = sum((x.count(c) / n) * (y.count(c) / n) for c in cats)
    return None if pe == 1 else (po - pe) / (1 - pe)


def boot_diff(rows, value):
    """AI minus human difference in mean(value), bootstrap over posts. rows: (tweetId, grp, note)."""
    by_post = collections.defaultdict(list)
    for t, g, n in rows:
        by_post[t].append((g, value(n)))
    posts = list(by_post.values())
    def stat(ps):
        a = [v for p in ps for g, v in p if g == "ai"]; h = [v for p in ps for g, v in p if g == "human"]
        return (np.mean(a) - np.mean(h)) if a and h else np.nan
    draws = [stat([posts[i] for i in rng.integers(0, len(posts), len(posts))]) for _ in range(NB)]
    lo, hi = np.nanpercentile(draws, [2.5, 97.5])
    a = [value(n) for t, g, n in rows if g == "ai"]; h = [value(n) for t, g, n in rows if g == "human"]
    return {"ai": float(np.mean(a)), "human": float(np.mean(h)), "n_ai": len(a), "n_human": len(h),
            "diff": float(stat(posts)), "lo": float(lo), "hi": float(hi)}


notes, url_rows = {}, []
for nid, s in sample.items():
    urls = list(dict.fromkeys(text[nid]["urls"]))
    per_judge = {j: [url_label(j, nid, u) for u in urls] for j in (A, B, C)}
    for i, u in enumerate(urls):
        url_rows.append({"noteId": nid, "grp": s["grp"], "host": page(u)["host"], "page_status": page(u)["status"],
                         "A": per_judge[A][i], "B": per_judge[B][i], "C": per_judge[C][i]})
    notes[nid] = {"grp": s["grp"], "tweetId": s["tweetId"], "writer": s["writer"], "n_urls": len(urls),
                  "dead": any(page(u)["status"] == "dead" for u in urls),
                  **{k: note_label(per_judge[j]) for k, j in (("A", A), ("B", B), ("C", C))}}
rows = [(n["tweetId"], n["grp"], n) for n in notes.values()]
res = {"notes": len(notes), "urls": len(url_rows),
       "page_status_by_group": {g: dict(collections.Counter(r["page_status"] for r in url_rows if r["grp"] == g)) for g in ("ai", "human")},
       "judgments_missing": {j: sum(r[j] == "MISSING" for r in url_rows) for j in "ABC"}}

# Judge agreement on readable pages (URL level) and at note level.
ok = [r for r in url_rows if r["page_status"] == "ok" and "MISSING" not in (r["A"], r["B"])]
res["agreement"] = {"url_AB_n": len(ok), "url_AB_kappa": kappa([r["A"] for r in ok], [r["B"] for r in ok]),
                    "url_AB_confusion": dict(collections.Counter(f"{r['A']}|{r['B']}" for r in ok))}
both = [n for n in notes.values() if n["A"] in ("supported", "unsupported") and n["B"] in ("supported", "unsupported")]
res["agreement"]["note_AB_n"] = len(both)
res["agreement"]["note_AB_kappa"] = kappa([n["A"] for n in both], [n["B"] for n in both])

# H3. Primary: notes where A and B agree. Bounds: both say unsupported (lower), either says so (upper).
agree = [(n["tweetId"], n["grp"], n) for n in both if n["A"] == n["B"]]
bothrows = [(n["tweetId"], n["grp"], n) for n in both]
res["H3"] = {
    "primary_agree_set": boot_diff(agree, lambda n: n["A"] == "unsupported"),
    "lower_bound_both": boot_diff(bothrows, lambda n: n["A"] == "unsupported" and n["B"] == "unsupported"),
    "upper_bound_either": boot_diff(bothrows, lambda n: "unsupported" in (n["A"], n["B"])),
}
three = [(n["tweetId"], n["grp"], n) for n in notes.values() if all(n[j] in ("supported", "unsupported") for j in "ABC")]
if three:
    res["H3"]["majority_of_three"] = boot_diff(three, lambda n: [n[j] for j in "ABC"].count("unsupported") >= 2)
# Same-post pairs where both notes are in the agree set (the cleanest comparison).
pair = collections.defaultdict(dict)
for t, g, n in agree:
    pair[t][g] = n["A"] == "unsupported"
pairs = [p for p in pair.values() if len(p) == 2]
res["H3"]["same_post_pairs"] = {"n": len(pairs), "ai": float(np.mean([p["ai"] for p in pairs])) if pairs else None,
                                "human": float(np.mean([p["human"] for p in pairs])) if pairs else None,
                                "ai_only_unsupported": sum(p["ai"] and not p["human"] for p in pairs),
                                "human_only_unsupported": sum(p["human"] and not p["ai"] for p in pairs)}

# Secondary: dead links and notes with no checkable source.
res["secondary"] = {"has_dead_link": boot_diff(rows, lambda n: n["dead"]),
                    "no_checkable_source_judgeA": boot_diff(rows, lambda n: n["A"] == "no_checkable")}

# H4 / Part 3: do raters' source tags track verified support?
tags = collections.defaultdict(lambda: [0, 0, 0])
with open("cache/sample_ratings.tsv") as f:
    for r in csv.DictReader(f, delimiter="\t"):
        t = tags[r["noteId"]]; t[0] += 1; t[1] += r["helpfulGoodSources"] == "1"; t[2] += r["notHelpfulSourcesMissingOrUnreliable"] == "1"
for nid, n in notes.items():
    k = tags[nid]; n["ratings"] = k[0]; n["good_sources_share"] = k[1] / k[0] if k[0] else None
    n["bad_sources_share"] = k[2] / k[0] if k[0] else None
def tag_diff(field):
    s = np.array([n[field] for t, g, n in agree if n["A"] == "supported"]); u = np.array([n[field] for t, g, n in agree if n["A"] == "unsupported"])
    if not len(s) or not len(u): return None
    d = [rng.choice(s, len(s)).mean() - rng.choice(u, len(u)).mean() for _ in range(NB)]
    return {"supported": float(s.mean()), "unsupported": float(u.mean()), "n_supported": len(s), "n_unsupported": len(u),
            "diff": float(s.mean() - u.mean()), "lo": float(np.percentile(d, 2.5)), "hi": float(np.percentile(d, 97.5))}
res["H4"] = {"helpfulGoodSources_share": tag_diff("good_sources_share"),
             "notHelpfulSourcesMissingOrUnreliable_share": tag_diff("bad_sources_share")}

# Human gold labels, if the labellers' files exist.
gold_files = sorted(glob.glob("audit/gold_labels_*.csv"))
if gold_files:
    collapse = lambda l: {"SUPPORTS": "SUPPORTS", "PARTIAL": "PARTIAL", "DOES_NOT_SUPPORT": "DOES_NOT_SUPPORT"}.get(l.strip().upper(), "UNCHECKABLE")
    gold = [{(r["noteId"], r["cited_link"]): collapse(r["label"]) for r in csv.DictReader(open(f)) if r["label"].strip()} for f in gold_files]
    res["gold"] = {"labellers": len(gold), "rows": [len(g) for g in gold]}
    if len(gold) >= 2:
        k = sorted(set(gold[0]) & set(gold[1]))
        res["gold"]["human_human_kappa_url"] = kappa([gold[0][x] for x in k], [gold[1][x] for x in k])
    for name, j in (("A", A), ("B", B), ("C", C)):
        k = [x for x in gold[0] if x[1]]
        res["gold"][f"judge{name}_vs_human1_kappa_url"] = kappa([url_label(j, x[0], x[1]) for x in k], [gold[0][x] for x in k])
        rnd = set(json.load(open("audit/gold_v2_design.json"))["random"]) if pathlib.Path("audit/gold_v2_design.json").exists() else set()
        kr = [x for x in k if x[0] in rnd]  # random half only: unbiased by the flagged over-sample (DEVIATIONS D7)
        if kr:
            res["gold"][f"judge{name}_vs_human1_kappa_url_random_half"] = kappa([url_label(j, x[0], x[1]) for x in kr], [gold[0][x] for x in kr])
        # Per-label view of DOES_NOT_SUPPORT: how often the judge's flag matches the human's, and how many human flags it finds.
        jd = {x: url_label(j, x[0], x[1]) for x in k}
        hd = [x for x in k if gold[0][x] == "DOES_NOT_SUPPORT"]; jdn = [x for x in k if jd[x] == "DOES_NOT_SUPPORT"]
        res["gold"][f"judge{name}_dns"] = {"human_dns": len(hd), "judge_dns": len(jdn),
                                           "both": sum(gold[0][x] == "DOES_NOT_SUPPORT" for x in jdn),
                                           "human_dns_judge_supports": sum(jd[x] in ("SUPPORTS", "PARTIAL") for x in hd),
                                           "agree_exact": sum(jd[x] == gold[0][x] for x in k), "n": len(k)}
    res["gold"]["human_labels"] = dict(collections.Counter(gold[0].values()))
    # PREREG s6 gate is judge-human kappa at NOTE level; and its fallback, H3 on the human-labelled set (random half only).
    rnd = set(json.load(open("audit/gold_v2_design.json"))["random"])
    hn = {}
    for (nid, u), l in gold[0].items(): hn.setdefault(nid, []).append(l)
    hn = {nid: note_label(ls) for nid, ls in hn.items()}
    for name in ("A", "B", "C"):
        for tag, ids in (("", list(hn)), ("_random_half", [i for i in hn if i in rnd])):
            ids = [i for i in ids if i in notes]
            res["gold"][f"judge{name}_vs_human1_kappa_note{tag}"] = kappa([notes[i][name] for i in ids], [hn[i] for i in ids])
    res["gold"]["human_only_H3_random_half"] = {g: {"notes": sum(notes[i]["grp"] == g for i in hn if i in rnd and i in notes),
        "unsupported": sum(notes[i]["grp"] == g and hn[i] == "unsupported" for i in hn if i in rnd and i in notes),
        "supported": sum(notes[i]["grp"] == g and hn[i] == "supported" for i in hn if i in rnd and i in notes)} for g in ("ai", "human")}

# Exploratory H3 sensitivity (not pre-registered, added after the final review).
sens = res["H3_sensitivity"] = {}
# (a) Each judge alone: does the sign of H3 depend on which judge is used?
for name in "ABC":
    r_ = [(n["tweetId"], n["grp"], n) for n in notes.values() if n[name] in ("supported", "unsupported")]
    sens[f"judge{name}_alone"] = boot_diff(r_, lambda n, name=name: n[name] == "unsupported")
# (b) Coverage: AI notes more often have a checkable source. Using Judge A over all 400 + 400 notes, how unsupported
# would AI notes without a checkable source have to be (human ones counted as fully supported) for AI to tie humans?
cnt = {g: {"n": sum(n["grp"] == g for n in notes.values()),
           "uns": sum(n["grp"] == g and n["A"] == "unsupported" for n in notes.values()),
           "nc": sum(n["grp"] == g and n["A"] == "no_checkable" for n in notes.values())} for g in ("ai", "human")}
sens["coverage"] = {**cnt, "break_even_rate_ai_uncheckable": (cnt["human"]["uns"] / cnt["human"]["n"] * cnt["ai"]["n"] - cnt["ai"]["uns"]) / cnt["ai"]["nc"]}
# (c) Is judge leniency the same for AI- and human-cited links? Uses the authors' labels (DEVIATIONS D7).
if gold_files:
    for name, j in (("A", A), ("B", B), ("C", C)):
        out = {}
        for g in ("ai", "human"):
            k = [x for x in gold[0] if x[0] in notes and notes[x[0]]["grp"] == g]
            jl = {x: url_label(j, x[0], x[1]) for x in k}
            hd = [x for x in k if gold[0][x] == "DOES_NOT_SUPPORT"]
            out[g] = {"links": len(k), "agree": sum(jl[x] == gold[0][x] for x in k), "human_dns": len(hd),
                      "human_dns_judge_supports": sum(jl[x] in ("SUPPORTS", "PARTIAL") for x in hd)}
        sens[f"leniency_judge{name}"] = out

# Negative control (DEVIATIONS D4): share of mismatched note-page pairs a judge still calls support.
res["negative_control"] = {}
for name, j in (("A", A), ("B", B), ("C", C)):
    labs = [json.loads(p.read_text())["label"] for p in pathlib.Path(f"audit/control/{j}").glob("*.json")]
    if labs:
        res["negative_control"][name] = {"n": len(labs), "false_support": sum(l in ("SUPPORTS", "PARTIAL") for l in labs),
                                         "labels": dict(collections.Counter(labs))}

# Harder control (DEVIATIONS D8): one number changed in a note all judges called supported; support now counts as a miss.
res["perturbed_control"] = {}
for name, j in (("A", A), ("B", B), ("C", C)):
    labs = [json.loads(p.read_text())["label"] for p in pathlib.Path(f"audit/control_perturbed/{j}").glob("*.json")]
    if labs:
        res["perturbed_control"][name] = {"n": len(labs), "missed": sum(l in ("SUPPORTS", "PARTIAL") for l in labs),
                                          "labels": dict(collections.Counter(labs))}
man = json.load(open("audit/control_perturbed/manifest.json")) if pathlib.Path("audit/control_perturbed/manifest.json").exists() else []
clean = [m for m in man if m["to"] not in page(m["url"])["text"]]  # drop pairs where the new number also appears on the page
caught = lambda j, m: json.loads(pathlib.Path(f"audit/control_perturbed/{j}/{m['noteId']}__{sha(m['url'])[:12]}.json").read_text())["label"] in ("DOES_NOT_SUPPORT", "UNVERIFIED_QUOTE")
if clean:
    res["perturbed_control"]["clean_n"] = len(clean)
    for name, j in (("A", A), ("B", B), ("C", C)):
        res["perturbed_control"][f"clean_caught_{name}"] = sum(caught(j, m) for m in clean)
    res["perturbed_control"]["clean_caught_any"] = sum(any(caught(j, m) for j in (A, B, C)) for m in clean)

# Extra agreement check (DEVIATIONS D5): the 110 judgments the first Judge B made before its usage limit.
G = "codex-cli__gpt-5.6-terra"
gk = [(p.name, json.loads(p.read_text())["label"]) for p in pathlib.Path(f"audit/judgments/{G}").glob("*.json")]
collapse3 = lambda l: l if l in ("SUPPORTS", "PARTIAL", "DOES_NOT_SUPPORT") else "UNCHECKABLE"
res["gpt_subset"] = {"n": len(gk)}
for name, j in (("A", A), ("B", B), ("C", C)):
    pr = [(collapse3(l), collapse3(json.loads(q.read_text())["label"])) for f, l in gk if (q := pathlib.Path(f"audit/judgments/{j}/{f}")).exists()]
    res["gpt_subset"][f"kappa_vs_{name}"] = kappa([a for a, b in pr], [b for a, b in pr]); res["gpt_subset"][f"n_vs_{name}"] = len(pr)

# Exploratory: per AI writer, and the list of unsupported notes for human review.
w = collections.defaultdict(lambda: [0, 0])
for t, g, n in agree:
    if g == "ai": w[n["writer"]][0] += 1; w[n["writer"]][1] += n["A"] == "unsupported"
res["exploratory_per_writer"] = {k: {"n": v[0], "unsupported": v[1]} for k, v in sorted(w.items(), key=lambda kv: -kv[1][0])}

pathlib.Path("results").mkdir(exist_ok=True)
json.dump(res, open("results/part2.json", "w"), indent=1)
with open("results/audit_labels.csv", "w", newline="") as f:
    wr = csv.writer(f); wr.writerow(["noteId", "grp", "writer", "n_urls", "judgeA", "judgeB", "judgeC", "has_dead_link", "ratings", "good_sources_share"])
    for nid, n in notes.items():
        wr.writerow([nid, n["grp"], n["writer"], n["n_urls"], n["A"], n["B"], n["C"], int(n["dead"]), n["ratings"], n["good_sources_share"]])
with open("results/unsupported_examples.csv", "w", newline="") as f:
    wr = csv.writer(f); wr.writerow(["noteId", "grp", "url", "judgeA_reason", "judgeB_reason"])
    for nid, n in notes.items():
        if n["A"] == n["B"] == "unsupported":
            for u in dict.fromkeys(text[nid]["urls"]):
                js = [pathlib.Path(f"audit/judgments/{j}/{nid}__{sha(u)[:12]}.json") for j in (A, B)]
                if all(p.exists() for p in js):
                    d = [json.loads(p.read_text()) for p in js]
                    if d[0]["label"] == d[1]["label"] == "DOES_NOT_SUPPORT":
                        wr.writerow([nid, n["grp"], u, d[0]["parsed"].get("reason", ""), d[1]["parsed"].get("reason", "")])
print(json.dumps(res, indent=1))
