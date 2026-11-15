# Deviations from PREREG.md

Every change after the freeze, with date and reason. Empty at the freeze.

## D1 (2026-11-15): collaborative-note account is not flagged `apiEarnedIn`

PREREG section 3 defined the collaborative-note account as an `apiEarnedIn` author with at least 90%
collaborative surviving notes. In the snapshot, all 77,077 notes with `isCollaborativeNote = 1` come
from one author whose `enrollmentState` is not `apiEarnedIn`, so the rule as written would have left
those Grok-drafted notes in the human group. The rule is now: any author with at least 90%
collaborative surviving notes, whatever its enrollment state. Found on the first run of
`analysis/part1.py`, from a count of notes by collaborative flag and enrollment state; the exclusion
itself was pre-registered, only the way of finding the account changed.

## Judge models (recorded 2026-11-15, before the main judging run)

Judge A: `anthropic/claude-sonnet-5.5`. Judge B: `google/gemini-3.8-flash`. Both through OpenRouter,
temperature 0, `max_tokens` 2000, prompt `audit/judge_prompt.md` as committed in `8f4dbcc`.
A ten-note mechanics pilot ran first; its judgments are kept and are part of the main run (same prompt, same models).

## D2 (2026-11-15): judges changed before the main run, for cost

The OpenRouter account had no credit, so the judges recorded above could not be run. Before any
main-run judgment, they were replaced by two models reached through local command-line clients on
the author's own subscriptions, still from two vendors: **Judge A `claude-sonnet-5-5`** (Claude
Code client, no tools) and **Judge B `gpt-5.6-terra`** (Codex client, read-only sandbox in an empty
directory). The prompt is unchanged (`audit/judge_prompt.md`, commit `8f4dbcc`). Temperature cannot
be set through these clients, so judgments use each client's default sampling instead of the
pre-registered temperature 0. The 14 judgments from the OpenRouter mechanics pilot were discarded
unread except for label counts used to debug the runner; every pair is judged afresh.

## D3 (2026-11-15): a third judge added as a robustness check

The sprint sponsor's API (Adaption) became available after the freeze. **Judge C `qwen3.5-397b`**,
an open-weights model from a third vendor, run at temperature 0 with the same prompt, is added.
Decided before any judgment was tabulated by author type. The pre-registered primary H3 estimate is
unchanged (notes where Judges A and B agree). Judge C is used only for (i) a majority-of-three
estimate reported next to the primary one and (ii) agreement statistics against the human labels.

## D4 (2026-11-15): negative control for the judges added

Added before any citation result was tabulated. 150 sampled notes are each paired with a readable
page cited by a note on a different post, and judged with the same prompt by all three judges. A
sound judge should label almost none of these SUPPORTS or PARTIAL, so that share is reported as each
judge's false-support rate. This is an extra validity check; it changes no pre-registered outcome.

## D5 (2026-11-15): Judge B replaced after the GPT client hit its usage limit

The Codex client stopped at 110 of about 780 judgments: the author's free ChatGPT plan reached its
usage limit and does not reset until after the deadline. Decided before any citation result was
tabulated by author type:

- **Judge A** stays `claude-sonnet-5-5`.
- **Judge B** is now `qwen3.5-397b` (sponsor API, temperature 0), previously Judge C.
- **Judge C** (robustness only, as in D3) is now `glm-5.2` (sponsor API, temperature 0).
- The 110 `gpt-5.6-terra` judgments are kept. They cover a hash-ordered, effectively random subset
  of pairs and are reported only as an extra agreement check against Judges A and B.

The primary H3 estimate is still "notes where Judges A and B agree"; A and B are still from two vendors.

## D6 (15 Nov, ~11:05 IST): output-token cap raised for the sponsor-API judges

About a quarter of `qwen3.5-397b` calls returned no answer: the model spent the whole 4,000-token
output cap on reasoning (`status: incomplete`, `reason: max_output_tokens`). These calls were never
cached, so no label was recorded for them. The cap is raised to 16,000 for the remaining calls of
Judges B and C. The prompt, model and temperature are unchanged; judgments already made are kept.
Pairs that needed more reasoning are therefore judged under the higher cap, which is a known
difference between the earlier and later calls.

## D7 (15 Nov, ~12:30 IST): human check is one labeller on 60 notes, over-sampling judge-flagged notes

The plan (PREREG section 8) was 150 notes labelled by two people. The project has one author, so
there is one labeller and no human-human kappa. The time left allows about 60 notes. Judge A called
only 45 of 779 links DOES_NOT_SUPPORT, so 60 random notes would contain only a handful of
unsupported cases and the kappa would mean little. The sheet (`cache/gold_sheet_v2.csv`, built by
`audit/make_gold.py`) therefore mixes 30 random notes with 30 notes Judge A flagged, in hash order,
with no flag or author column; only readable links are included. The split is recorded in
`audit/gold_v2_design.json`, which the labeller does not open before finishing. Kappa is reported
on all 60 notes and on the random half alone; only the random half is unbiased by the selection.
This was set before any human label existed.
