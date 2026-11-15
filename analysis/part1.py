"""Part 1 (PREREG.md section 5): status outcomes for every note in the window.

Usage: python analysis/part1.py [raw_dir]   -> results/part1.json, results/writers.csv, results/monthly.csv
Re-runs unchanged on any day's snapshot (the "daily runner").
"""
import json, math, sys, pathlib
import duckdb, numpy as np

RAW = sys.argv[1] if len(sys.argv) > 1 else "data/raw"
OUT = pathlib.Path("results"); OUT.mkdir(exist_ok=True)
START, END = "2025-09-02 00:00:00", "2026-11-01 00:00:00"  # UTC, END exclusive
SEED, B = 20261115, 2000
CRH = "CURRENTLY_RATED_HELPFUL"
rng = np.random.default_rng(SEED)
db = duckdb.connect()
tsv = lambda name: f"read_csv('{RAW}/{name}-*.tsv', delim='\t', header=true, quote='', all_varchar=true)"

db.execute(f"""
create table n as
with ai as (select participantId from {tsv('userEnrollment')} where enrollmentState = 'apiEarnedIn'),
     notes as (select noteId, tweetId, coalesce(try_cast(isCollaborativeNote as int), 0) as collab from {tsv('notes')})
select h.noteId, h.noteAuthorParticipantId as author,
       (ai.participantId is not null) as is_ai,
       (notes.noteId is null) as deleted, notes.tweetId, coalesce(notes.collab, 0) as collab,
       strftime(epoch_ms(cast(h.createdAtMillis as bigint)), '%Y-%m') as month,
       coalesce('{CRH}' in (coalesce(h.firstNonNMRStatus, ''), coalesce(h.mostRecentNonNMRStatus, ''), h.currentStatus), false) as eh,
       (h.currentStatus != '{CRH}') as not_crh_now,
       case when h.firstNonNMRStatus = '{CRH}'
            then (cast(h.timestampMillisOfMostRecentStatusChange as bigint)
                  - cast(h.timestampMillisOfFirstNonNMRStatus as bigint)) / 3600000.0 end as hours_first_to_last_change
from {tsv('noteStatusHistory')} h
left join ai on ai.participantId = h.noteAuthorParticipantId
left join notes on notes.noteId = h.noteId
where epoch_ms(cast(h.createdAtMillis as bigint)) >= timestamp '{START}'
  and epoch_ms(cast(h.createdAtMillis as bigint)) <  timestamp '{END}'
""")
# Collaborative-note account(s): any author with >= 90% collaborative surviving notes (see DEVIATIONS.md, D1).
collab_authors = [r[0] for r in db.execute("""
    select author from n where not deleted group by author having avg(collab) >= 0.9""").fetchall()]
db.execute("alter table n add column grp varchar")
db.execute("update n set grp = case when author in (select unnest(?)) then 'collab' when is_ai then 'ai' else 'human' end",
           [collab_authors])


def wilson(k, n):
    if n == 0: return [None, None, None]
    p, z = k / n, 1.96
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [p, c - h, c + h]


def boot(stat, *groups):
    """Cluster bootstrap: each group is an array of per-cluster rows; resample clusters within group."""
    point = stat(*groups)
    draws = [stat(*[g[rng.integers(0, len(g), len(g))] for g in groups]) for _ in range(B)]
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return {"est": float(point), "lo": float(lo), "hi": float(hi)}


res = {"snapshot_dir": RAW, "window": [START, END], "collab_authors": len(collab_authors)}

# Descriptives per group.
res["groups"] = {}
for g, n_all, n_del, eh_all, n_surv, eh_surv, lost, authors in db.execute("""
    select grp, count(*), sum(deleted::int), sum(eh::int), sum((not deleted)::int),
           sum((eh and not deleted)::int), sum((eh and not_crh_now)::int), count(distinct author)
    from n group by grp""").fetchall():
    res["groups"][g] = {
        "notes": n_all, "authors": authors,
        "deleted": wilson(n_del, n_all),
        "ever_helpful_all_notes": wilson(eh_all, n_all),
        "ever_helpful_surviving_only": wilson(eh_surv, n_surv),
        "lost_helpful_among_ever_helpful": wilson(lost, eh_all), "ever_helpful_n": eh_all,
    }

# Per-author counts for author-cluster bootstraps: [n_all, eh_all, n_surv, eh_surv, lost]
def author_rows(g):
    return np.array(db.execute("""
        select count(*), sum(eh::int), sum((not deleted)::int), sum((eh and not deleted)::int),
               sum((eh and not_crh_now)::int) from n where grp = ? group by author order by author""", [g]).fetchall(), dtype=float)

A, H = author_rows("ai"), author_rows("human")
rate = lambda x, k, n: x[:, k].sum() / x[:, n].sum()
# H1: (AI - human ever-Helpful, surviving only) minus (AI - human ever-Helpful, all notes).
res["H1"] = {
    "diff_surviving_only": boot(lambda a, h: rate(a, 3, 2) - rate(h, 3, 2), A, H),
    "diff_all_notes": boot(lambda a, h: rate(a, 1, 0) - rate(h, 1, 0), A, H),
    "survivorship_gap": boot(lambda a, h: (rate(a, 3, 2) - rate(h, 3, 2)) - (rate(a, 1, 0) - rate(h, 1, 0)), A, H),
}

# H2: lost-Helpful among ever-Helpful. Primary: within posts with both an AI and a human ever-Helpful note.
P = np.array(db.execute("""
    select avg(case when grp='ai' then not_crh_now::int end), avg(case when grp='human' then not_crh_now::int end)
    from n where eh and not deleted and grp in ('ai','human') group by tweetId
    having sum((grp='ai')::int) > 0 and sum((grp='human')::int) > 0 order by tweetId""") .fetchall(), dtype=float)
res["H2"] = {"within_post_posts": len(P)}
if len(P):
    res["H2"]["within_post"] = boot(lambda p: (p[:, 0] - p[:, 1]).mean(), P)
    res["H2"]["within_post_rates"] = {"ai": float(P[:, 0].mean()), "human": float(P[:, 1].mean())}
res["H2"]["primary"] = "within_post" if len(P) >= 300 else "month_standardised"
# Month-standardised: human lost rate reweighted to the AI ever-Helpful month distribution.
M = db.execute("""
    select month, sum((grp='ai')::int), sum((grp='ai' and not_crh_now)::int),
           sum((grp='human')::int), sum((grp='human' and not_crh_now)::int)
    from n where eh and grp in ('ai','human') group by month order by month""").fetchall()
w = np.array([m[1] for m in M], dtype=float)
ai_rate = sum(m[2] for m in M) / w.sum()
hum_std = sum(w[i] * (m[4] / m[3]) for i, m in enumerate(M) if m[3]) / w[[bool(m[3]) for m in M]].sum()
res["H2"]["month_standardised"] = {"ai": ai_rate, "human_standardised": hum_std, "diff": ai_rate - hum_std,
                                   "author_cluster": boot(lambda a, h: rate(a, 4, 1) - rate(h, 4, 1), A, H)}

# Secondary: hours from first Helpful status to the last status change, for notes that lost it.
res["hours_to_loss_median"] = dict(db.execute("""
    select grp, median(hours_first_to_last_change) from n
    where eh and not_crh_now and hours_first_to_last_change is not null group by grp""").fetchall())

# Exploratory (not pre-registered): AI writers that delete >5% of their notes vs those that do not.
# Deletion is almost entirely from a few accounts; X describes a "Deletion Model" in its own writer (arXiv 2609.40067).
res["exploratory_ai_by_deletion"] = {}
for name, cond in (("deleting_writers", ">"), ("non_deleting_writers", "<=")):
    k = db.execute(f"""
        with a as (select author from n where grp = 'ai' group by author having avg(deleted::int) {cond} 0.05)
        select count(distinct author), count(*), sum(deleted::int), sum(eh::int), sum((not deleted)::int),
               sum((eh and not deleted)::int), sum((eh and not_crh_now)::int)
        from n where grp = 'ai' and author in (select author from a)""").fetchone()
    res["exploratory_ai_by_deletion"][name] = {
        "writers": k[0], "notes": k[1], "deleted": wilson(k[2], k[1]), "ever_helpful_all_notes": wilson(k[3], k[1]),
        "ever_helpful_surviving_only": wilson(k[5], k[4]), "lost_helpful_among_ever_helpful": wilson(k[6], k[3])}

# Robustness (not pre-registered): H1 with the deleting accounts merged into one cluster (they may share one operator),
# H1 without them, and H1 on notes with at least ~10 weeks of follow-up before the snapshot.
db.execute("create temp table dele as select author from n where grp = 'ai' group by author having avg(deleted::int) > 0.05")
def rows_where(g, extra="", merge=False):
    key = "case when author in (select author from dele) then 'DELETERS' else author end" if merge else "author"
    return np.array(db.execute(f"""
        select count(*), sum(eh::int), sum((not deleted)::int), sum((eh and not deleted)::int), sum((eh and not_crh_now)::int)
        from n where grp = ? {extra} group by {key} order by {key}""", [g]).fetchall(), dtype=float)
gap = lambda a, h: (rate(a, 3, 2) - rate(h, 3, 2)) - (rate(a, 1, 0) - rate(h, 1, 0))
adv_all = lambda a, h: rate(a, 1, 0) - rate(h, 1, 0)
excl = "and author not in (select author from dele)"
A_ex = np.array(db.execute(f"""select count(*), sum(eh::int), sum((not deleted)::int), sum((eh and not deleted)::int),
    sum((eh and not_crh_now)::int) from n where grp = 'ai' {excl} group by author order by author""").fetchall(), dtype=float)
old_q = "and month <= '2026-08'"
res["robustness_H1"] = {
    "deleting_accounts_one_cluster": {"survivorship_gap": boot(gap, rows_where("ai", merge=True), H), "ai_clusters": len(rows_where("ai", merge=True))},
    "without_deleting_accounts": {"survivorship_gap": boot(gap, A_ex, H), "diff_all_notes": boot(adv_all, A_ex, H)},
    "notes_to_2026_08": {"survivorship_gap": boot(gap, rows_where("ai", old_q), rows_where("human", old_q)),
                         "diff_all_notes": boot(adv_all, rows_where("ai", old_q), rows_where("human", old_q)),
                         "deleted_ai": float(db.execute(f"select avg(deleted::int) from n where grp='ai' {old_q}").fetchone()[0]),
                         "deleted_human": float(db.execute(f"select avg(deleted::int) from n where grp='human' {old_q}").fetchone()[0])},
}

# Drawn last so earlier bootstrap intervals keep their random draws.
res["robustness_H1"]["deleting_accounts_one_cluster"]["diff_all_notes"] = boot(adv_all, rows_where("ai", merge=True), H)

json.dump(res, open(OUT / "part1.json", "w"), indent=1)
db.execute(f"""copy (select month, grp, count(*) notes, avg(deleted::int) deleted_rate, avg(eh::int) ever_helpful_rate,
    sum((eh and not_crh_now)::int) * 1.0 / nullif(sum(eh::int), 0) lost_rate
    from n group by all order by all) to '{OUT}/monthly.csv' (header)""")
# Exploratory: one reliability row per AI writer (hashed id shortened).
db.execute(f"""copy (select substr(author, 1, 8) writer, grp, count(*) notes, min(month) first_month, max(month) last_month,
    round(avg(deleted::int), 4) deleted_rate, round(avg(eh::int), 4) ever_helpful_rate, sum(eh::int) ever_helpful,
    round(sum((eh and not_crh_now)::int) * 1.0 / nullif(sum(eh::int), 0), 4) lost_rate
    from n where is_ai group by all order by notes desc, writer) to '{OUT}/writers.csv' (header)""")
print(json.dumps(res, indent=1))
