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

Addendum to D6 (~12:30 IST): the last 43 Qwen pairs (mostly long pages) kept failing with HTTP 504
gateway timeouts. Sponsor-API calls are now streamed, which only changes how the reply is delivered,
not the prompt, model, temperature or token cap.

Correction to D7 (15 Nov, ~13:30 IST): the team has three authors (Malyadri Chowdary Marneni,
Poojitha G, Chandana R), not one. The single-labeller design stands unless a second author labels
the same sheet, in which case human-human kappa is reported as PREREG section 8 planned.

## D8 (15 Nov, ~14:00 IST): harder negative control by perturbing one number

The mismatched-page control (D4) is easy to pass. As a harder test, decided before running it:
take note-page pairs that all three judges labelled SUPPORTS where the note contains a number of at
least two digits that also appears on the page, change the first such number (years +3, other numbers
x1.5, rounded), and judge the altered note against the same page. The page now contradicts the note,
so SUPPORTS or PARTIAL counts as a miss. Up to 100 pairs, chosen in hash order. Outputs go to
`audit/control_perturbed/` with a manifest of each change. This is a robustness check on the judges
and changes no hypothesis or primary analysis.

Result of D7 (15 Nov, evening IST): the authors labelled all 106 rows (60 notes) in
`audit/gold_labels_1.csv`; an AI tool was used only to tidy the wording of the labellers' working notes, which are not released. One
labeller, so no human-human kappa. Judge-vs-human kappas, per-label DOES_NOT_SUPPORT counts and the
label mix are in `results/part2.json` under `gold`. The per-label counts were added after seeing the
kappas, so they are descriptive, not pre-registered.

## D9 (15 Nov, evening IST): judge-human kappa gate triggered; H3 and H4 stay judge-based, marked provisional

PREREG section 6: if judge-human kappa at note level is below 0.60, H3 and H4 are reported on the
human-labelled set only and the judge results move to an appendix. Note-level kappa against the
authors' labels was 0.56 (Judge A), 0.44 (B) and 0.30 (C), so the gate is triggered. The human set
is one labeller on 60 notes, half chosen from Judge A's flags (D7); its random half holds 30 notes
with one unsupported note, far too few to test H3 or H4. We report that human-only result
(`results/part2.json`, `gold.human_only_H3_random_half`) but keep the judge-based H3 and H4 in the main
text, labelled provisional. This is a departure from the planned primary analysis, decided after
seeing the kappas.

## Exploratory analyses added after outcomes were seen (not deviations; reported as exploratory)

- 15 Nov, afternoon IST: H1 robustness (deleting accounts as one cluster; without them; notes to Aug 2026),
  in `results/part1.json` under `robustness_H1`; report Table 2.
- 15 Nov, evening IST: H3 sensitivity in `results/part2.json` under `H3_sensitivity`: H3 with each judge
  alone; a coverage bound for notes with no checkable source; judge leniency by author type on the
  hand-labelled links. None changes a pre-registered analysis.

Second labeller for D7 (15 Nov, evening IST): a second author (Poojitha G) labelled the same 106
links independently, without seeing the first author's labels or the judges' labels
(`audit/gold_labels_2.csv`; working-notes column not released, as for labeller 1). This restores the
human-human kappa PREREG section 8 planned. Reported in `results/part2.json` under `gold`:
human-human kappa, kappa on "does not support" vs the rest (descriptive, added after seeing the
first kappa), judge vs second labeller, and judge vs the human consensus (links both label alike),
which is the comparison PREREG section 6 names. The human-only H3 in D9 still uses labeller 1.
