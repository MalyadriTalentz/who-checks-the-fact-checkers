"""Report figures, drawn only from results/ (run after part1.py and part2.py).

Usage: python analysis/figures.py  -> results/fig1_survivorship.png, results/fig2_monthly.png, results/fig3_support.png
"""
import csv, json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
AI, HU = "#c0392b", "#2c6fbb"
p1 = json.load(open("results/part1.json"))
g = p1["groups"]

# Figure 1: deletion and ever-Helpful, surviving-only vs all notes.
fig, ax = plt.subplots(figsize=(6.2, 2.6))
metrics = [("deleted", "Deleted by author"), ("ever_helpful_surviving_only", "Ever Helpful\n(surviving only)"),
           ("ever_helpful_all_notes", "Ever Helpful\n(incl. deleted)"), ("lost_helpful_among_ever_helpful", "Lost Helpful\n(of ever Helpful)")]
for i, (k, label) in enumerate(metrics):
    for off, grp, col, name in ((-0.18, "ai", AI, "AI writers"), (0.18, "human", HU, "Human writers")):
        est, lo, hi = (100 * v for v in g[grp][k])
        ax.bar(i + off, est, 0.34, color=col, label=name if i == 0 else None)
        ax.errorbar(i + off, est, [[est - lo], [hi - est]], color="k", lw=0.8, capsize=2)
        ax.text(i + off, est + 0.6, f"{est:.1f}", ha="center", fontsize=7.5)
ax.set_xticks(range(len(metrics)), [m[1] for m in metrics]); ax.set_ylabel("% of notes")
ax.legend(frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.15)); ax.set_ylim(0, 21); fig.tight_layout()
fig.savefig("results/fig1_survivorship.png", dpi=220)

# Figure 2: monthly AI share of notes and deletion rate by group.
rows = list(csv.DictReader(open("results/monthly.csv")))
months = sorted({r["month"] for r in rows})
get = lambda m, grp, k: next((float(r[k]) for r in rows if r["month"] == m and r["grp"] == grp), float("nan"))
share = [get(m, "ai", "notes") / (get(m, "ai", "notes") + get(m, "human", "notes")) * 100 for m in months]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.2, 2.3))
a1.plot(months, share, color=AI); a1.set_ylabel("AI share of new notes (%)")
for grp, col in (("ai", AI), ("human", HU)):
    a2.plot(months, [100 * get(m, grp, "deleted_rate") for m in months], color=col, label=grp)
a2.set_ylabel("Deleted (%)"); a2.legend(["AI", "Human"], frameon=False)
for a in (a1, a2):
    a.set_xticks(months[::3], [m[2:] for m in months[::3]], rotation=45)
fig.tight_layout(); fig.savefig("results/fig2_monthly.png", dpi=220)

# Figure 3: share of notes with an unsupporting citation, by judge rule (Part 2).
p2 = pathlib.Path("results/part2.json")
if p2.exists():
    h3 = json.load(open(p2))["H3"]
    rules = [("lower_bound_both", "Both A and B\nsay unsupported"), ("primary_agree_set", "A and B agree\n(primary)"),
             ("majority_of_three", "Majority of\nthree judges"), ("upper_bound_either", "Either A or B\nsays unsupported")]
    rules = [r for r in rules if r[0] in h3]
    fig, ax = plt.subplots(figsize=(6.2, 2.4))
    for i, (k, label) in enumerate(rules):
        d = h3[k]
        for off, grp, col in ((-0.18, "ai", AI), (0.18, "human", HU)):
            ax.bar(i + off, 100 * d[grp], 0.34, color=col, label=("AI" if grp == "ai" else "Human") if i == 0 else None)
            ax.text(i + off, 100 * d[grp] + 0.4, f"{100 * d[grp]:.1f}", ha="center", fontsize=7.5)
        ax.text(i, -3.2, f"diff {100 * d['diff']:+.1f} [{100 * d['lo']:+.1f}, {100 * d['hi']:+.1f}]", ha="center", fontsize=7)
    ax.set_xticks(range(len(rules)), [r[1] for r in rules]); ax.set_ylabel("% of notes with an\nunsupporting source")
    ax.set_ylim(bottom=-4.5); ax.axhline(0, color="k", lw=0.5); ax.legend(frameon=False); fig.tight_layout()
    fig.savefig("results/fig3_support.png", dpi=220)
print("figures written")
