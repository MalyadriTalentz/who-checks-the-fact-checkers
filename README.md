# Who checks the fact-checkers?

An independent reliability audit of AI-written Community Notes on X.
Entry for the Apart Research AI x Epistemics Research Sprint, 13 to 15 November 2026
(Track 4: Open Track; Track 2: Trust Infrastructure).
Authors: Malyadri Chowdary Marneni (student researcher, Masters' Union University), Poojitha G (Sapthagiri NPS University; research intern, IIM Bangalore), Chandana R (BGS College).

AI note writers now write about three in ten Community Notes. Published comparisons score them by
how often raters mark their notes Helpful. This project measures two things the ratings do not:
whether a note keeps its Helpful status, and whether the sources it cites support what it says.

Results are in `results/` and the report. The plan was fixed in advance in [`PREREG.md`](PREREG.md);
every change since is in [`DEVIATIONS.md`](DEVIATIONS.md).

## What is new and what is pre-existing

**Nothing is pre-existing.** All code, the pre-registration, the sample, the judgments and the
analysis were produced during the sprint; the first commit is the frozen pre-registration. The data
is X's public Community Notes release. An AI assistant (Claude Code) was used for implementation and writing
support; the authors are responsible for everything here.

## Layout

| Path | What it is |
|---|---|
| `PREREG.md`, `DEVIATIONS.md` | Hypotheses and methods frozen before any outcome data was read; dated log of changes |
| `analysis/part1.py` | Status outcomes for every note in the window (Part 1); also the per-writer table |
| `audit/sample.py`, `audit/sample.csv` | The 800-note sample: 400 same-post pairs of AI and human Helpful notes |
| `audit/fetch.py`, `audit/fetch_log.csv` | Fetches each cited link (live, then Internet Archive) and logs the outcome |
| `audit/judge_prompt.md`, `audit/judge.py` | The frozen judge prompt and the runner |
| `audit/judgments/`, `audit/control/` | Every judge reply, for the real pairs and for the mismatched-page negative control |
| `audit/control_perturbed/` | The harder control: one number altered in notes all judges called supported (DEVIATIONS D8) |
| `audit/make_gold.py`, `audit/gold_v2_design.json`, `audit/gold_labels_1.csv` | The human check sheet, which half was random, and the authors' labels (DEVIATIONS D7) |
| `audit/get_ratings.sh` | Extracts the public ratings of the sampled notes (Part 3) |
| `analysis/part2.py` | Citation support and rater blindness (Parts 2 and 3) |
| `results/` | Every number used in the report |
| `analysis/figures.py`, `report/build.py`, `run_all.sh` | Figures; the report (PDF via LaTeX, and the template .docx), built from `results/` only |

## Reproduce

Python 3.11 or newer; [tectonic](https://tectonic-typesetting.github.io) for the PDF.

```sh
python3 -m venv .venv && .venv/bin/pip install duckdb numpy matplotlib python-docx
# 1. Download the 2026-11-14 snapshot (notes, noteStatusHistory, userEnrollment) into data/raw/ and unzip:
#    https://ton.twimg.com/birdwatch-public-data/2026/11/14/{notes,noteStatusHistory,userEnrollment}/...
# 2. Rebuild the local caches that are not committed (note text, fetched pages, ratings of sampled notes):
.venv/bin/python audit/sample.py && .venv/bin/python audit/fetch.py && ./audit/get_ratings.sh
# 3. Rebuild every number, figure and the report from the snapshot, the caches and the committed judgments:
./run_all.sh
```

Part 1 needs only step 1. `analysis/part1.py <dir>` runs unchanged on any other day's snapshot, so the
per-writer reliability table can be refreshed daily. Part 2 also needs the caches from step 2, which are
not committed because they hold note text and copies of third-party web pages. Pages fetched later may
differ from ours (live pages change), so judge labels are committed in `audit/judgments/` and
`audit/control*/`, and the fetch outcome for every link is in `audit/fetch_log.csv`. Re-judging
(`audit/judge.py`) is the slow, paid step and is not needed to rebuild the numbers.

## Data handling

Notes are public. Writer and rater identifiers are the hashed ids X publishes, shown truncated. This
repository holds note ids, derived labels and short quoted passages, not bulk note text or ratings.
