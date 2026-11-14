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
