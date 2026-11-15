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

# Figure 1: ever-Helpful on surviving notes vs all notes, for all AI, human, and AI split by whether the writer deletes.
X = p1["exploratory_ai_by_deletion"]
groups = [("All AI writers", g["ai"]), ("Human writers", g["human"]),
          (f"{X['deleting_writers']['writers']} deleting\nAI accounts", X["deleting_writers"]),
          (f"{X['non_deleting_writers']['writers']} other\nAI writers", X["non_deleting_writers"])]
fig, ax = plt.subplots(figsize=(6.2, 2.7))
for i, (label, d) in enumerate(groups):
    col = HU if label.startswith("Human") else AI
    for off, k, alpha, name in ((-0.18, "ever_helpful_surviving_only", 0.45, "Surviving notes only"), (0.18, "ever_helpful_all_notes", 1.0, "All notes, incl. deleted")):
        est, lo, hi = (100 * v for v in d[k])
        ax.bar(i + off, est, 0.34, color=col, alpha=alpha, label=name if i == 0 else None)
        ax.text(i + off, est + 0.4, f"{est:.1f}", ha="center", fontsize=7.5)
    ax.text(i, -2.6, f"{100 * d['deleted'][0]:.1f}% deleted", ha="center", fontsize=7.5, color="#444")
ax.set_xticks(range(len(groups)), [x[0] for x in groups]); ax.set_ylabel("% ever rated Helpful")
ax.set_ylim(-3.5, 18.5); ax.axhline(0, color="k", lw=0.5)
leg = ax.legend(frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.16))
for h in leg.legend_handles: h.set_color("#777")
fig.tight_layout(); fig.savefig("results/fig1_survivorship.png", dpi=220)

# Figure 2: monthly AI share of notes and deletion rate by group.
rows = list(csv.DictReader(open("results/monthly.csv")))
months = sorted({r["month"] for r in rows})
get = lambda m, grp, k: next((float(r[k]) for r in rows if r["month"] == m and r["grp"] == grp), float("nan"))
share = [get(m, "ai", "notes") / (get(m, "ai", "notes") + get(m, "human", "notes")) * 100 for m in months]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.2, 2.3))
a1.plot(months, share, color=AI); a1.set_ylabel("AI share of new notes (%)")
for grp, col in (("ai", AI), ("human", HU)):
    a2.plot(months, [100 * get(m, grp, "deleted_rate") for m in months], color=col, label=grp)
a2.set_ylabel("Deleted (%)"); a2.legend(["AI", "Human"], frameon=False, loc="upper left")
if "2026-04" in months:
    a2.annotate("deletion jumps", xy=(months.index("2026-04"), 15), xytext=(months.index("2026-04") + 0.8, 10),
                fontsize=7.5, arrowprops=dict(arrowstyle="->", lw=0.7))
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
