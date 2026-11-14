# Pre-registration: Who checks the fact-checkers?

An independent reliability audit of AI-written Community Notes on X.
Apart Research AI x Epistemics Research Sprint, November 2026 (Open Track; also Trust Infrastructure).

**Status: frozen at the commit that adds this file.** At the freeze, the only things inspected were
the column headers of `userEnrollment` and `noteStatusHistory` and the count of rows per
`enrollmentState` (41 `apiEarnedIn`). No outcome column had been tabulated and the notes and ratings
files had not been opened. Every later change is logged in `DEVIATIONS.md` with a date and a reason.

## 1. Question

X's AI Note Writers now write a large share of Community Notes, and published comparisons score them
by how often raters mark them Helpful. Are AI-written notes as reliable as those ratings suggest?
We measure two things ratings do not: whether a note keeps its Helpful status, and whether the
sources it cites support what it says.

## 2. Data

- Public Community Notes snapshot dated **2026-11-14** (`ton.twimg.com/birdwatch-public-data/2026/11/14/`):
  `notes`, `noteStatusHistory`, `userEnrollment`, and `noteRatings` (ratings are read only for sampled notes).
- **Window:** notes with `createdAtMillis` from 2025-09-02 00:00 UTC (first AI writer admitted) to
  2026-10-31 23:59 UTC, so every note has at least 14 days for its status to settle.

## 3. Definitions

- **AI note:** `noteAuthorParticipantId` has `enrollmentState = apiEarnedIn` in the snapshot.
- **Collaborative-note account:** any `apiEarnedIn` author for whom at least 90% of surviving notes
  have `isCollaborativeNote = 1`. Excluded from the AI group and reported separately.
- **Human note:** any other author. (People pasting LLM text cannot be identified; see Limitations.)
- **Deleted note:** `noteId` present in `noteStatusHistory` and absent from `notes`. The
  documentation says deleted notes leave the notes file and keep their status-history row.
- **Ever Helpful:** `CURRENTLY_RATED_HELPFUL` appears in `firstNonNMRStatus`, `mostRecentNonNMRStatus`
  or `currentStatus`.
- **Lost Helpful:** ever Helpful and `currentStatus != CURRENTLY_RATED_HELPFUL`.
- **Post:** `tweetId`, available only for surviving notes (it is in the notes file only).

## 4. Hypotheses and primary outcomes

Two-sided tests, alpha 0.05, Holm correction across H1 to H4. Smallest effect of interest: 5 percentage points.

- **H1 (survivorship).** The AI minus human difference in the ever-Helpful rate is smaller when deleted
  notes are in the denominator than when only surviving notes are counted.
  *Outcome:* the two rate differences and their difference.
- **H2 (reversal).** Among ever-Helpful notes, the lost-Helpful rate differs between AI and human notes.
  *Outcome:* risk difference. *Primary analysis:* within posts that have at least one ever-Helpful AI
  note and one ever-Helpful human note; if fewer than 300 such posts exist, the primary analysis is
  all ever-Helpful notes with month-of-creation strata.
- **H3 (citation support).** Among sampled ever-Helpful surviving notes, the share with at least one
  checkable cited source that does not support the note differs between AI and human notes.
  *Outcome:* risk difference at note level.
- **H4 (rater blindness).** Among sampled notes, the share of ratings carrying `helpfulGoodSources`
  does not differ between notes whose citations are all supported and notes with an unsupported citation.
  *Outcome:* difference in mean tag share; we report the interval and call "blind" a 95% interval inside ±5 points.

**Secondary:** deletion rate by group; dead-link rate; share of notes with no checkable source;
time from first Helpful status to losing it.

**Exploratory (labelled as such in the report):** one reliability row per AI writer; monthly trend;
cited-domain profile; the collaborative-note account.

## 5. Part 1: status outcomes

All notes in the window, no sampling. Rates with Wilson intervals. For group differences, a
bootstrap with 2,000 resamples: by post for within-post analyses, by author for all-note analyses
(with 41 AI authors this interval will be wide; we report it anyway next to the note-level one).
Seed 20261115 everywhere.

## 6. Part 2: citation audit

- **Sample:** 400 AI and 400 human ever-Helpful surviving notes. First, same-post pairs (one random
  note of each kind per post). If fewer than 400 pairs exist, the remainder is drawn at random within
  month-of-creation strata to match the AI notes' month distribution. Notes with no URL are sampled
  like any other and counted in "no checkable source".
- **Fetching:** each URL in `summary` is fetched live, then from the Internet Archive if the live
  fetch fails. Post text is fetched from X's public oEmbed endpoint when available, as context only.
- **Label per note-URL pair:** `SUPPORTS`, `PARTIAL`, `DOES_NOT_SUPPORT`, `DEAD` (no live page and
  no archive copy), `UNCHECKABLE` (links to X posts, video, login or paywall, non-text).
- **Note-level label:** *unsupported* if any checkable URL is `DOES_NOT_SUPPORT`; *supported* if
  every checkable URL is `SUPPORTS` or `PARTIAL`; otherwise *no checkable source*.
- **Judges:** two LLMs from different vendors, temperature 0, same frozen prompt
  (`audit/judge_prompt.md`), blind to whether the note is AI or human. Model IDs are recorded in
  `DEVIATIONS.md` before the main run. We report a lower bound (both judges say unsupported) and an
  upper bound (either does); the primary H3 estimate uses notes where the judges agree.
- **Human gold set:** 150 sampled notes (75 AI, 75 human) labelled by two people, blind to author
  type and to judge output. We report Cohen's kappa between the humans and between each judge and
  the human consensus. **Gate:** if judge-human kappa at note level is below 0.60, H3 and H4 are
  reported on the human-labelled set only and the judge results move to an appendix.

## 7. Part 3: rater blindness

Ratings for the 800 sampled notes are extracted by streaming the ratings files. Per note: share of
ratings with `helpfulGoodSources` and with `notHelpfulSourcesMissingOrUnreliable`. Compared between
supported and unsupported notes with a bootstrap over notes.

## 8. Exclusions and missing data

- Notes outside the window; notes by the collaborative-note account (reported separately).
- H3 denominator excludes notes with no checkable source; that share is reported by group.
- Fetch failures are never counted as unsupported.

## 9. Known limits stated in advance

- `enrollmentState` is a current-state field: AI writers that left the programme before the snapshot
  are counted as human. This biases AI-human differences toward zero.
- Deleted notes have no text or post id, so Part 2 and all within-post analyses cover surviving notes only.
- "Supports" is judged against the cited page, not against the truth of the note.
- Notes that reach a decision are not a random sample of all posts.

## 10. Reproducibility and disclosure

One command rebuilds every number in the report from the snapshot. Raw judge outputs, human labels,
note ids and derived labels are committed; bulk note text is not republished. All code and this plan
were written during the sprint; nothing is pre-existing. Code and drafting used an AI assistant
(Claude Code); the human gold labels and all conclusions are the team's.
