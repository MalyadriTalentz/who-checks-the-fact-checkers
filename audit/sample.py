"""Part 2 sampling (PREREG.md section 6): 400 AI + 400 human ever-Helpful surviving notes, as same-post pairs.

Usage: python audit/sample.py [raw_dir]
Writes audit/sample.csv (ids and group; committed) and cache/sample_text.jsonl (note text; not committed).
"""
import csv, json, re, sys, pathlib
import duckdb

RAW = sys.argv[1] if len(sys.argv) > 1 else "data/raw"
N_PAIRS, SEED = 400, 20261115
CRH = "CURRENTLY_RATED_HELPFUL"
URL = re.compile(r"https?://[^\s<>\"')\]]+")
db = duckdb.connect()
tsv = lambda name: f"read_csv('{RAW}/{name}-*.tsv', delim='\t', header=true, quote='', all_varchar=true)"

db.execute(f"""
create table eh as
with ai as (select participantId from {tsv('userEnrollment')} where enrollmentState = 'apiEarnedIn'),
     collab as (select noteAuthorParticipantId a from {tsv('notes')} group by 1
                having avg(coalesce(try_cast(isCollaborativeNote as int), 0)) >= 0.9)
select n.noteId, n.tweetId, n.summary, n.createdAtMillis,
       case when ai.participantId is not null then 'ai' else 'human' end as grp,
       substr(n.noteAuthorParticipantId, 1, 8) as writer, h.currentStatus
from {tsv('notes')} n
join {tsv('noteStatusHistory')} h using (noteId)
left join ai on ai.participantId = n.noteAuthorParticipantId
where n.noteAuthorParticipantId not in (select a from collab)
  and cast(n.createdAtMillis as bigint) >= epoch_ms(timestamp '2025-09-02 00:00:00')
  and cast(n.createdAtMillis as bigint) <  epoch_ms(timestamp '2026-11-01 00:00:00')
  and '{CRH}' in (coalesce(h.firstNonNMRStatus, ''), coalesce(h.mostRecentNonNMRStatus, ''), h.currentStatus)
""")
# Posts with both kinds; hash-based ordering makes the draw reproducible without relying on RNG state.
posts = [r[0] for r in db.execute(f"""
    select tweetId from eh group by tweetId
    having sum((grp='ai')::int) > 0 and sum((grp='human')::int) > 0
    order by md5(tweetId || '{SEED}') limit {N_PAIRS}""").fetchall()]
assert len(posts) == N_PAIRS, f"only {len(posts)} same-post pairs; use the pre-registered month-strata fallback"
rows = db.execute(f"""
    select * from (select *, row_number() over (partition by tweetId, grp order by md5(noteId || '{SEED}')) r
                   from eh where tweetId in (select unnest(?))) where r = 1
    order by md5(noteId || '{SEED}')""", [posts]).fetchall()
cols = [d[0] for d in db.description]
pathlib.Path("cache").mkdir(exist_ok=True)
with open("audit/sample.csv", "w", newline="") as f, open("cache/sample_text.jsonl", "w") as t:
    w = csv.writer(f); w.writerow(["noteId", "tweetId", "grp", "writer", "currentStatus", "n_urls"])
    for row in rows:
        d = dict(zip(cols, row))
        urls = [u.rstrip(".,;:!?") for u in URL.findall(d["summary"] or "")]
        w.writerow([d["noteId"], d["tweetId"], d["grp"], d["writer"], d["currentStatus"], len(urls)])
        t.write(json.dumps({"noteId": d["noteId"], "tweetId": d["tweetId"], "summary": d["summary"], "urls": urls}) + "\n")
print(len(rows), "notes sampled from", len(posts), "posts")
