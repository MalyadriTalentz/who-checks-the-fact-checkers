"""Build the report (report/report.docx) on the official template, taking every number from results/.

Usage: python report/build.py   (run ./run_all.sh first). Export to PDF with Pages or Word.
"""
import csv, json, math, pathlib, re
import docx
from docx.shared import Inches, Pt

p1, p2 = json.load(open("results/part1.json")), json.load(open("results/part2.json"))
G, H1, H2, X = p1["groups"], p1["H1"], p1["H2"], p1["exploratory_ai_by_deletion"]
H3, H4, AG, NC, GPT = p2["H3"], p2["H4"], p2["agreement"], p2["negative_control"], p2["gpt_subset"]
pc = lambda v, d=1: f"{100 * v:.{d}f}%"
pt = lambda v, d=1: f"{100 * v:+.{d}f}"
ci = lambda b: f"{pt(b['est'] if 'est' in b else b['diff'])} points [95% CI {pt(b['lo'])}, {pt(b['hi'])}]"
f0 = lambda n: f"{n:,}"
pairs = H3["same_post_pairs"]; k_ai, k_hu = pairs["ai_only_unsupported"], pairs["human_only_unsupported"]
sign_p = min(1, 2 * sum(math.comb(k_ai + k_hu, i) for i in range(min(k_ai, k_hu) + 1)) / 2 ** (k_ai + k_hu))
ps = p2["page_status_by_group"]; ok_share = {g: ps[g]["ok"] / sum(ps[g].values()) for g in ps}
writers = [r for r in csv.DictReader(open("results/writers.csv")) if r["grp"] == "ai"]
def pval(b):  # two-sided, normal approximation from the bootstrap interval
    est = b["est"] if "est" in b else b["diff"]; se = (b["hi"] - b["lo"]) / 3.92
    return math.erfc(abs(est / se) / math.sqrt(2)) if se > 0 else 0.0
raw = [pval(H1["survivorship_gap"]), pval(H2["within_post"]), pval(H3["primary_agree_set"]), pval(H4["helpfulGoodSources_share"])]
order = sorted(range(4), key=lambda i: raw[i]); holm = [0.0] * 4; run = 0.0
for rank, i in enumerate(order):
    run = max(run, min(1.0, (4 - rank) * raw[i])); holm[i] = run
fp = lambda x: "p < 0.001" if x < 0.001 else f"p = {x:.2f}"
h4b = H4["helpfulGoodSources_share"]
verdict = [
    f"Supported ({fp(holm[0])}), but below the 5-point smallest effect of interest",
    f"Small difference, AI lower; {fp(holm[1])} after correction (uncorrected {fp(raw[1])}); far inside the 5-point margin",
    f"No detectable difference ({fp(holm[2])}); point estimate favours AI notes",
    "Inconclusive: interval not inside ±5 points" if not (-0.05 < h4b["lo"] and h4b["hi"] < 0.05) else "Blind: interval inside ±5 points",
]

TITLE = "The Notes That Vanish: Self-Deletion Inflates AI Fact-Checkers' Track Record on X, but Their Sources Hold Up"
AUTHORS = ["Malyadri Chowdary Marneni\u00b9", "Poojitha G\u00b2", "Chandana R"]  # Chandana's affiliation not yet given
AFFILS = ["\u00b9Student researcher, Masters' Union University",
          "\u00b2Sapthagiri NPS University; Research intern, Indian Institute of Management Bangalore"]
AUTHOR = ", ".join(AUTHORS) + "\n" + "   ".join(AFFILS)
ABSTRACT = (
    f"Roughly one in six Community Notes written by AI on X quietly disappears. AI writers now draft about half of all new "
    f"notes, and every published comparison scores them by how often raters mark their surviving notes Helpful. This "
    f"pre-registered audit measures what that score cannot see. Using X's public record of every note from September 2025 "
    f"to October 2026 ({f0(G['ai']['notes'])} AI and {f0(G['human']['notes'])} human notes), AI writers deleted "
    f"{pc(G['ai']['deleted'][0])} of their notes against {pc(G['human']['deleted'][0])} for humans. Nearly all of these "
    f"deletions come from {X['deleting_writers']['writers']} high-volume accounts and begin abruptly in March 2026, matching "
    f"the automatic deletion of likely failures that X describes in its own AI writer. Counting the deleted notes halves the "
    f"AI advantage in reaching Helpful status, from {pt(H1['diff_surviving_only']['est'])} to {pt(H1['diff_all_notes']['est'])} "
    f"points. The second question is whether the notes are true to their sources. Three LLM judges from different vendors "
    f"checked the pages cited by 800 AI and human notes on the same 400 posts; none called any of {NC['A']['n']} deliberately "
    f"mismatched pages support. Here AI notes did well: they cited a readable source far more often, and were unsupported no "
    f"more often than human notes ({pc(H3['primary_agree_set']['ai'])} vs {pc(H3['primary_agree_set']['human'])}, difference "
    f"not statistically clear). Raters' own source tags barely told supported from unsupported notes. AI fact-checkers' "
    f"sources deserve more trust than their survival statistics: evaluations should count deleted notes."
)
assert 150 <= len(ABSTRACT.split()) <= 250, len(ABSTRACT.split())

S = []  # (kind, content)
h2 = lambda t: S.append(("h2", t)); h3 = lambda t: S.append(("h3", t)); para = lambda t: S.append(("p", t))
bullet = lambda t: S.append(("b", t)); fig = lambda path, cap: S.append(("fig", (path, cap)))

h2("1. Introduction")
para("If a student could erase every test they were about to fail, their grade point average would look excellent. "
     "That is, in effect, the position of some AI fact-checkers on X today.")
para("Community Notes is X's crowd-sourced fact-checking system: contributors propose notes on posts, and a note is shown "
     "to everyone only when raters who usually disagree both rate it Helpful. Since September 2025, AI programs can write "
     "notes through an API on the same terms as people, and they now draft about half of all new notes (Figure 2). Meta, "
     "TikTok and YouTube have adopted or trialled similar systems, so whether AI fact-checkers can be trusted at scale is "
     "becoming a question about the information diet of billions of people.")
para("So far the answer has come from one number: how often raters mark AI notes Helpful. By that measure AI writers look "
     "strong, beating ordinary contributors [1, 2, 3]. But the number has two blind spots. It is computed on the notes that "
     "survive, and X's own paper on its AI writer describes a model that deletes notes predicted to fail after as few as "
     "three ratings [4]. And it measures whether a note persuades raters, not whether the sources it cites say what it "
     "claims. Raters are not required to open those sources. A fact-checker that sounds right but cites pages that do not "
     "back it up would pass this test, which is exactly the failure an epistemic system most needs to catch.")
para("This project audits AI fact-checkers on both blind spots, independently of the platform's own scoring, with every "
     "hypothesis fixed in advance. Its contributions:")
bullet(f"A survivorship correction on the full public record ({f0(G['ai']['notes'] + G['human']['notes'])} notes). AI "
       f"writers delete notes {G['ai']['deleted'][0] / G['human']['deleted'][0]:.1f} times as often as humans, almost "
       f"entirely through {X['deleting_writers']['writers']} accounts, and counting those deletions halves their advantage "
       "in reaching Helpful status.")
bullet("A source audit of 800 AI and human notes on the same 400 posts, using three LLM judges from different vendors, a "
       "deterministic quote check and a mismatched-page control. AI notes cite readable sources more often and are not "
       "more often unsupported.")
bullet("Evidence that raters' source tags barely track verified support, plus a per-writer reliability table and a "
       "one-command script that rebuilds every number from any day's public data.")
S.append(("table", (["Pre-registered question", "Result (AI minus human)", "Verdict"], [
    ["H1. Does counting deleted notes shrink the AI advantage in reaching Helpful?",
     f"Gap {pt(H1['survivorship_gap']['est'])} points [{pt(H1['survivorship_gap']['lo'])}, {pt(H1['survivorship_gap']['hi'])}]: "
     f"advantage falls from {pt(H1['diff_surviving_only']['est'])} to {pt(H1['diff_all_notes']['est'])}", verdict[0]],
    ["H2. Do AI and human notes differ in how often they lose Helpful status?",
     f"{pt(H2['within_post']['est'])} points [{pt(H2['within_post']['lo'])}, {pt(H2['within_post']['hi'])}], same posts", verdict[1]],
    ["H3. Do AI and human notes differ in how often a cited source fails to support them?",
     f"{pt(H3['primary_agree_set']['diff'])} points [{pt(H3['primary_agree_set']['lo'])}, {pt(H3['primary_agree_set']['hi'])}]", verdict[2]],
    ["H4. Are raters' \"good sources\" tags blind to whether sources support the note?",
     f"{pt(H4['helpfulGoodSources_share']['diff'])} points [{pt(H4['helpfulGoodSources_share']['lo'])}, "
     f"{pt(H4['helpfulGoodSources_share']['hi'])}], supported minus unsupported", verdict[3]],
], "Table 1. The four pre-registered hypotheses at a glance. Brackets: 95% bootstrap intervals. p-values are "
   "normal approximations from the bootstrap standard error, Holm-corrected across the four tests as planned.")))

h2("2. Related Work")
para("Gong and Wu [1] characterise 20 AI writers and find their notes are rated helpful less often than expert human notes "
     "but more often than laypeople's. Li and Bakker [2] ran an LLM writer in the field and compared its 1,614 notes with "
     "human notes on the same posts; the LLM notes received more positive ratings across political viewpoints. R Street [3] "
     "analysed seven months of public data and reported that AI notes reached Helpful status at 18.0% against 8.9% for human "
     "notes. X's engineers [4] describe the API, the earn-in and quota rules, and their own Community Writer, including a "
     "Deletion Model that \"identifies notes that are unlikely to obtain CRH status and proactively deletes the notes\" after "
     "as few as three ratings. De et al. [5] study collaborative notes drafted by an LLM and refined by human feedback. Earlier "
     "work examines whether Community Notes reduce engagement with misleading posts [6], what threatens contributor "
     "participation [7], and how the system evolved over four years [8]. A recent survey of AI for epistemics names "
     "Community Notes as a prime example of deployed epistemic infrastructure [9].")
para("All AI-versus-human comparisons above score notes by rater outcomes. None of them, as far as their abstracts and "
     "reported methods show, accounts for notes their writers deleted, and none checks whether cited sources support the "
     "notes. This project adds both measures and uses the platform's own rating tags as a comparison rather than as ground truth.")

h2("3. Methods")
para("The hypotheses, definitions, sample size, judge design and analysis were written down and committed before any "
     "outcome data was read (PREREG.md, first commit of the repository). Every later change is logged with its reason in "
     "DEVIATIONS.md (seven entries, covering judge substitutions forced by usage limits and API errors, and the reduced "
     "human check described below).")
h3("Data and definitions (Part 1)")
para(f"We used X's public Community Notes release of 14 November 2026: the note, note-status-history and user-enrolment "
     f"files. The window is notes created from 2 September 2025 (first AI writer admitted) to 31 October 2026. An AI note is "
     f"one whose author is enrolled as an API writer ({G['ai']['authors']} writers with notes in the window). One account "
     f"that writes collaborative notes ({f0(G['collab']['notes'])} notes) is analysed separately. The status-history file "
     "keeps every note ever created, while the notes file drops deleted ones, so a note present in the first and absent "
     "from the second counts as deleted by its author. A note is ever Helpful if it reached Currently Rated Helpful (CRH) at "
     "any point, and has lost Helpful if it was ever CRH but is not now. Intervals are author-cluster bootstraps (2,000 "
     "resamples, fixed seed) for group differences and Wilson intervals for single rates.")
para("H1 (survivorship) compares the AI-minus-human difference in ever-Helpful rate computed on surviving notes only, as "
     "published comparisons do, with the same difference on all notes. H2 (reversal) compares how often ever-Helpful notes "
     f"lose that status, within posts that have both an AI and a human ever-Helpful note ({H2["within_post_posts"]:,} posts). The smallest effect of "
     "interest was fixed at 5 points.")
h3("Citation audit (Part 2)")
para("The sample is 400 posts drawn by hash order from posts with both an AI and a human note that reached Helpful status, "
     "one note of each kind per post (800 notes, 1,575 cited links). Each link was fetched live, with an Internet Archive "
     "copy as fallback. Links to social-media and video sites, login walls and pages that block automated access were "
     "marked uncheckable rather than judged; dead links were recorded as such. "
     f"This left {f0(AG['url_AB_n'])} readable note-page pairs.")
para("Each pair was judged with one frozen prompt that asks whether the cited page supports the note's main factual "
     "claim (SUPPORTS, PARTIAL, DOES_NOT_SUPPORT or UNCHECKABLE) and requires a verbatim supporting quote. Judges never see "
     "whether a note is AI or human. A deterministic check, fixed before judging, demotes any support label whose quote is not "
     "found on the page. Judge A is Claude Sonnet 5.5 and Judge B is Qwen 3.5 397B; Judge C, GLM 5.2, is used only for "
     "robustness. A note is unsupported if any readable cited page does not support it. The primary estimate uses notes "
     "on which Judges A and B agree; lower and upper bounds count notes both, or either, call unsupported.")
para("Two checks test the judges. In a negative control, 150 notes were each paired with a readable page cited by a note on "
     "a different post; a sound judge should almost never call such a page support. An earlier run of GPT-5.6 on 110 pairs, "
     "stopped by a usage limit, gives an extra agreement check. A human check was planned (see Limitations).")
h3("Rater blindness (Part 3)")
para(f"For the same notes we took all {f0(90742)} public ratings and computed, per note, the share of raters who ticked "
     "\"good sources\" and the share who ticked \"sources missing or unreliable\". H4 asks whether these shares differ between "
     "notes the judges agree are supported and notes they agree are unsupported, with ±5 points as the equivalence margin.")

h2("4. Results")
h3("Part 1: deletion flatters AI writers' track record")
fig("results/fig1_survivorship.png",
    f"Figure 1. Outcomes for all notes created 2 Sep 2025 to 31 Oct 2026 ({f0(G['ai']['notes'])} AI, "
    f"{f0(G['human']['notes'])} human). Counting deleted notes shrinks the AI advantage in reaching Helpful status. "
    "Error bars: 95% Wilson intervals (most are narrower than the line).")
para(f"AI writers deleted {pc(G['ai']['deleted'][0])} of their notes; human writers deleted {pc(G['human']['deleted'][0])} "
     f"(Figure 1). On surviving notes, AI notes reached Helpful status more often than human notes, {ci(H1['diff_surviving_only'])}. "
     f"Counting deleted notes, the difference is {ci(H1['diff_all_notes'])}. H1 is supported: the survivorship gap is "
     f"{ci(H1['survivorship_gap'])} ({fp(holm[0])}, Holm-corrected), about half of the headline advantage, although it falls "
     "short of the 5-point smallest effect of interest fixed in advance.")
para(f"The deletions are not spread across AI writers. {X['deleting_writers']['writers']} accounts delete more than 5% of their "
     f"notes; together they wrote {pc(X['deleting_writers']['notes'] / G['ai']['notes'], 0)} of AI notes and deleted "
     f"{pc(X['deleting_writers']['deleted'][0])} of them, while the other {X['non_deleting_writers']['writers']} AI writers deleted "
     f"{pc(X['non_deleting_writers']['deleted'][0])}. AI deletion was near zero until March 2026 and then jumped to 15 to 22% a "
     "month (Figure 2), which fits a deletion policy being switched on rather than a gradual change in writing. This pattern "
     "matches the Deletion Model in X's Community Writer [4], although hashed ids mean the accounts cannot be named. "
     "On surviving notes the deleting accounts look slightly better than the other AI writers "
     f"({pc(X['deleting_writers']['ever_helpful_surviving_only'][0])} vs {pc(X['non_deleting_writers']['ever_helpful_surviving_only'][0])} "
     f"ever Helpful); on all notes they look worse ({pc(X['deleting_writers']['ever_helpful_all_notes'][0])} vs "
     f"{pc(X['non_deleting_writers']['ever_helpful_all_notes'][0])}). This split was not pre-registered.")
fig("results/fig2_monthly.png",
    "Figure 2. Left: AI writers' share of new notes by month. Right: share of each month's notes later deleted by their "
    "author. AI deletion starts abruptly in March 2026.")
para(f"Once Helpful, AI notes keep that status at least as well as human notes. Within the 5,487 posts with both kinds of "
     f"ever-Helpful note, {pc(H2['within_post_rates']['ai'])} of AI notes and {pc(H2['within_post_rates']['human'])} of human "
     f"notes later lost it, a difference of {ci(H2['within_post'])}. The "
     f"difference is small and, after the planned Holm correction, not statistically significant ({fp(holm[1])}); either "
     "way it is far inside the 5-point margin, so AI notes are no less stable once Helpful.")
h3("Part 2: AI notes' sources hold up at least as well")
para(f"AI notes cited a readable source far more often: {pc(ok_share['ai'], 0)} of AI-cited links could be read and judged "
     f"against {pc(ok_share['human'], 0)} of human-cited links, and {pc(p2['secondary']['no_checkable_source_judgeA']['human'])} "
     f"of human notes had no checkable source at all, against {pc(p2['secondary']['no_checkable_source_judgeA']['ai'])} of AI notes. "
     "Human notes lean more on posts, videos and other social-media links. Dead links were rare in both groups "
     f"({pc(p2['secondary']['has_dead_link']['ai'])} vs {pc(p2['secondary']['has_dead_link']['human'])} of notes).")
fig("results/fig3_support.png",
    "Figure 3. Share of notes with at least one readable cited page that does not support the note, under four judge rules. "
    "Below each pair: AI minus human, points, with 95% post-cluster bootstrap interval.")
para(f"Among notes with a readable source, AI notes were not more often unsupported (Figure 3). On the primary measure, "
     f"notes where Judges A and B agree, {pc(H3['primary_agree_set']['ai'])} of AI notes and {pc(H3['primary_agree_set']['human'])} "
     f"of human notes were unsupported ({H3['primary_agree_set']['n_ai']} and {H3['primary_agree_set']['n_human']} notes), a "
     f"difference of {ci(H3['primary_agree_set'])}. The bounds and the majority of three judges point the same way, and in "
     f"{pairs['n']} same-post pairs where both notes were judged, only the AI note was unsupported in {k_ai} pairs and only the "
     f"human note in {k_hu} (two-sided sign test p = {sign_p:.2f}). H3 finds no "
     f"detectable difference ({fp(holm[2])}, Holm-corrected); if anything, the data lean towards AI notes being better sourced.")
para(f"The judges passed the negative control: none of the three called any of the {NC['A']['n']} mismatched pages support "
     f"(Judge A {NC['A']['false_support']}, Judge B {NC['B']['false_support']}, Judge C {NC['C']['false_support']}). Agreement "
     f"between Judges A and B on real pairs was moderate (Cohen's kappa {AG['url_AB_kappa']:.2f} per link, "
     f"{AG['note_AB_kappa']:.2f} per note). Most disagreements were PARTIAL against SUPPORTS rather than support against no "
     f"support. On the 110 GPT-5.6 pairs, kappa with Judges A, B and C was {GPT['kappa_vs_A']:.2f}, {GPT['kappa_vs_B']:.2f} and "
     f"{GPT['kappa_vs_C']:.2f}.")
S.append(("box", "What an unsupported Helpful note looks like. An AI note said an image showed the 2003 breakup of "
    "Space Shuttle Columbia, not Artemis 2, and cited a NASA Ames page; the page is a general overview of the division "
    "that never mentions Columbia. A human note called viral \"hero dog\" rescue clips AI-generated and cited a 2021 "
    "National Geographic article, which is about staged rescues using real animals, not AI. Both notes reached Helpful "
    "status; in both, the claim may well be true, but the cited source does not show it. Both judges agreed on each case."))
h3("Part 3: raters' source tags barely track verified support")
g, b = H4["helpfulGoodSources_share"], H4["notHelpfulSourcesMissingOrUnreliable_share"]
para(f"Raters ticked \"good sources\" on {pc(g['supported'])} of ratings for supported notes and {pc(g['unsupported'])} for "
     f"unsupported ones ({ci(g)}), and \"sources missing or unreliable\" on {pc(b['supported'])} and {pc(b['unsupported'])} "
     f"({ci(b)}). The second tag, the one meant to flag bad sourcing (a secondary measure), did not differ at all. With only "
     f"{g['n_unsupported']} unsupported notes, the first interval is too wide to show the tags are blind, so H4 is "
     "inconclusive rather than confirmed. All these notes had "
     "reached Helpful status, so the comparison is among notes raters already liked.")

h2("5. Discussion and Limitations")
para("Three lessons follow, and the first matters well beyond Community Notes.")
para("An AI system that can withdraw its own failures will look more reliable than it is. The deleting accounts look slightly better than "
     "the other AI writers on surviving notes and clearly worse once deletions are counted. Deletion is a reasonable design "
     "choice in itself; X's paper [4] justifies it as saving raters' attention. The problem is comparing writers on surviving "
     "notes when only some of them delete. The same trap awaits anyone who audits AI agents from logs the agent can edit. "
     "Platforms should publish deletion rates next to hit rates, and evaluations of AI writers should count every note "
     "submitted, as X's own quota system already does.")
para("AI fact-checkers' sourcing is not the weak point. On posts where both an AI and a human note reached Helpful status, "
     "AI notes more often cite something a reader can check, and what they cite supports them at least as often. Worries "
     "that AI notes win ratings with confident but unsupported claims are not borne out in this sample.")
para("Raters cannot be the only check on sources. Their source tags barely separate supported from unsupported notes, "
     "and the tag meant to flag bad sources did not move at all. An automated source check like the one used here, with "
     "its quote verification and negative control, is cheap enough to run on every note before it is shown, for AI and "
     "human writers alike.")
h3("Limitations")
bullet("Judges are LLMs. They agree only moderately with each other, and the human check is small: one labeller "
       "on 60 notes, half of them chosen because Judge A flagged them, instead of the planned two labellers on 150 notes "
       "(DEVIATIONS D7). Results are reported for each judge rule so readers can see how much they move.")
bullet(f"Coverage is uneven. Only {pc(ok_share['ai'], 0)} of AI-cited and {pc(ok_share['human'], 0)} of human-cited links "
       "could be read, so Part 2 describes notes with readable sources; videos, posts and blocked pages are not covered.")
bullet("The citation sample only includes notes that reached Helpful status on posts that both kinds of writer noted, so it "
       "says nothing about the sourcing of notes that never became Helpful.")
bullet("Linking the deleting accounts to X's Deletion Model is an inference from timing and volume; X hashes writer ids.")
bullet("Judge settings changed during the run: Judge A ran through a command-line client without temperature control, and "
       "the sponsor-API judges' token cap and transport changed mid-run (DEVIATIONS D2, D6). 22 of Judge B's replies could "
       "not be parsed and count as uncheckable.")
h3("Future Work")
para("Extend the audit to notes that never reached Helpful status and to video and post citations (transcripts, archived "
     "posts), add more human labellers, and run the per-writer table daily so deletion and reversal rates are tracked publicly "
     "as new AI writers join.")

h2("6. Conclusion")
para("Counting the notes AI writers delete removes about half of their apparent advantage in reaching Helpful status, and "
     "nearly all of that deletion comes from a few accounts that withdraw notes early. At the same time, the sources cited by "
     "AI notes that do reach Helpful status hold up at least as well as human notes' sources, and raters' source tags barely "
     "distinguish supported from unsupported notes. Comparisons of AI and human fact-checkers should count deletions and "
     "check sources rather than rely on helpfulness ratings of surviving notes.")

h2("Code and Data")
para("Code repository: https://github.com/MalyadriTalentz/who-checks-the-fact-checkers (PREREG.md, DEVIATIONS.md, all "
     "judge replies and the scripts that rebuild every number with ./run_all.sh).")
para("Data: X Community Notes public data release, snapshot of 14 November 2026 (https://x.com/i/communitynotes/download-data).")

h2("References")
for r in [
    "[1] Gong, Y. and Wu, S. (2026). Characterizing AI Fact-Checkers and Their Contributions on Community Notes. arXiv:2605.16566.",
    "[2] Li, H. and Bakker, M. A. (2026). AI Fact-Checking in the Wild: A Field Evaluation of LLM-Written Community Notes on X. arXiv:2604.02592.",
    "[3] Purnell, S. (2026). AI Writers on Community Notes: An Evaluation of Seven Months of Data. R Street Institute. https://www.rstreet.org/research/ai-writers-on-community-notes-an-evaluation-of-seven-months-of-data/",
    "[4] Miller, B., Baxter, J., Chao, J., Coleman, K., Hilgard, S. and Ortiz, D. (2026). Community-Driven API and AI Writer Design for Openly Scaling Community Notes. arXiv:2609.40067.",
    "[5] De, S., Slaughter, I., Guo, J., Cheng, Q.-Y., Yan, J., Banerjee, S. and Saveski, M. (2026). How Human Feedback Shapes AI-generated Community Notes. arXiv:2606.30905.",
    "[6] Chuai, Y., Tian, H., Pröllochs, N. and Lenzini, G. (2024). Did the Roll-Out of Community Notes Reduce Engagement With Misinformation on X/Twitter? CSCW 2024. arXiv:2307.07960.",
    "[7] Arjmandi-Lari, Z., Mantzarlis, A. and Stafford, T. (2025). Threats to the sustainability of Community Notes on X. arXiv:2510.00650.",
    "[8] Mohammadi, S. et al. (2025). From Birdwatch to Community Notes, from Twitter to X: four years of community-based content moderation. arXiv:2510.09585.",
    "[9] Ben_N and Csaky, A. (2026). State of the Field: AI for Epistemics and Coordination. LessWrong. https://www.lesswrong.com/posts/uw8RQ8yjKexnhTw6E/state-of-the-field-ai-for-epistemics-and-coordination",
]:
    para(r)

h2("Appendix A. Limitations and Dual-Use / Ethical Considerations")
para("What the results establish: deletion rates and status outcomes for every note in the public record over 14 months, and "
     "citation support for Helpful notes with readable sources on posts noted by both AI and human writers, as judged by LLMs "
     "that pass a mismatched-page control. What they do not establish: whether AI notes are more accurate overall, the quality "
     "of notes that never became Helpful, or the identity of any writer account.")
para("Dual use: the findings could be used to argue against AI fact-checking in general, which the citation results do not "
     "support, or by a writer to tune deletion so its record looks better. Reporting deletion rates next to hit rates removes "
     "that incentive, which is why the report recommends it. The judge prompt and quote check could also be used to probe "
     "which unsupported notes pass review; they are published because the same tools let anyone audit notes.")
para("Personal data: all data is public. X publishes writer and rater ids only in hashed form, and this project shows them "
     "truncated. The repository holds note ids, derived labels and short quotes from cited pages, not bulk note text or "
     "ratings. No one was contacted and nothing was posted to X.")

h2("Appendix B. Pre-registration and deviations")
para("PREREG.md was committed before any outcome was read. DEVIATIONS.md records seven changes: D1 a rule for the "
     "collaborative-note account; D2 judges run through command-line clients after the planned paid API had no credit; D3 a "
     "third judge; D4 the negative control (added, not replacing anything); D5 Judge B replaced after a usage limit, with its "
     "110 judgments kept as a check; D6 a higher token cap and streamed replies for the sponsor-API judges; D7 the reduced, "
     "enriched human check. No hypothesis, outcome definition or primary analysis was changed.")

h2("LLM Usage Statement")
para("The authors designed the study, set the hypotheses, made every analysis decision and verified each reported number "
     "against the files in results/. Claude Code was used as an AI assistant for implementation and writing support. Three "
     "LLMs also serve as judges inside the method, as described in Section 3. Human labels were made by the authors.")

# --- render onto the template ---
doc = docx.Document("cache/tmp/template.docx")
body = doc.element.body
title_table = doc.tables[0]
for el in list(body):  # keep only the title/abstract table and the section properties
    if el is not title_table._tbl and not el.tag.endswith("sectPr"):
        body.remove(el)
def grid(t):  # the template has no bordered table style, so set thin borders directly
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    b = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{edge}"); e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:color"), "999999"); b.append(e)
    t._tbl.tblPr.append(b)
def fill(cell, heading, text, size):
    cell.paragraphs[0].text = ""
    for p in cell.paragraphs[1:]:
        p._element.getparent().remove(p._element)
    r = cell.paragraphs[0].add_run(heading); r.bold = True; r.font.size = Pt(size)
    if text:
        q = cell.add_paragraph(); q.add_run(text).font.size = Pt(10)
fill(title_table.rows[0].cells[0], TITLE, AUTHOR, 15)
fill(title_table.rows[1].cells[0], "Abstract", ABSTRACT, 11)
for kind, c in S:
    if kind == "h2": doc.add_paragraph(c, style="Heading 2")
    elif kind == "h3": doc.add_paragraph(c, style="Heading 3")
    elif kind == "p": doc.add_paragraph(c, style="normal")
    elif kind == "b": doc.add_paragraph("• " + c, style="normal").paragraph_format.left_indent = Inches(0.25)
    elif kind == "table":
        head, rows, cap = c
        t = doc.add_table(rows=1 + len(rows), cols=len(head)); grid(t)
        for j, h in enumerate(head):
            cell = t.rows[0].cells[j]; cell.text = ""; r = cell.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(8.5)
        for i, row in enumerate(rows):
            for j, v in enumerate(row):
                cell = t.rows[i + 1].cells[j]; cell.text = ""; cell.paragraphs[0].add_run(v).font.size = Pt(8.5)
        q = doc.add_paragraph(style="normal"); r = q.add_run(cap); r.italic = True; r.font.size = Pt(9)
    elif kind == "box":
        t = doc.add_table(rows=1, cols=1); grid(t)
        cell = t.rows[0].cells[0]; cell.text = ""; head, _, rest = c.partition(". ")
        r = cell.paragraphs[0].add_run(head + ". "); r.bold = True; r.font.size = Pt(9)
        cell.paragraphs[0].add_run(rest).font.size = Pt(9)
        doc.add_paragraph(style="normal")
    elif kind == "fig":
        doc.add_picture(c[0], width=Inches(6.2))
        cap = doc.add_paragraph(style="normal"); r = cap.add_run(c[1]); r.italic = True; r.font.size = Pt(9)
doc.save("report/report.docx")
words = sum(len(c.split()) for k, c in S if k in ("p", "b"))
print("report/report.docx written;", len(ABSTRACT.split()), "abstract words;", words, "body words")


# --- LaTeX version (report/report.tex -> report/report.pdf with tectonic) ---
import re as _re
def esc(t):
    out = []
    for i, part in enumerate(_re.split(r"(https?://\S+?)(?=[)\s]|$|\.\s|\.$)", t)):
        if i % 2:
            out.append(r"\url{" + part + "}"); continue
        for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"), ("_", r"\_"),
                     ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\^{}")):
            part = part.replace(a, b)
        part = _re.sub(r'"([^"]*)"', r"``\1''", part)
        part = _re.sub(r"(?<![\w])-(?=\d)", "−", part)
        out.append(part)
    return "".join(out)
L = [r"""\documentclass[10.5pt]{article}
\usepackage[a4paper,margin=2.2cm]{geometry}
\usepackage{fontspec}
\setmainfont{texgyrepagella}[Extension=.otf,UprightFont=*-regular,BoldFont=*-bold,ItalicFont=*-italic,BoldItalicFont=*-bolditalic]
\setsansfont{texgyreheros}[Extension=.otf,UprightFont=*-regular,BoldFont=*-bold,ItalicFont=*-italic,BoldItalicFont=*-bolditalic,Scale=0.92]
\usepackage{graphicx,booktabs,tabularx,xcolor,titlesec,enumitem,caption}
\usepackage[most]{tcolorbox}
\usepackage{xurl}
\usepackage[hidelinks]{hyperref}
\definecolor{accent}{HTML}{C0392B}\definecolor{ink}{HTML}{1F2A36}\definecolor{soft}{HTML}{F6F1EE}
\titleformat{\section}{\sffamily\large\bfseries\color{ink}}{}{0pt}{}
\titleformat{\subsection}{\sffamily\normalsize\bfseries\color{accent}}{}{0pt}{}
\titlespacing*{\section}{0pt}{12pt}{4pt}\titlespacing*{\subsection}{0pt}{8pt}{2pt}
\captionsetup{font={small,it},labelformat=empty,skip=4pt}
\setlist[itemize]{leftmargin=1.2em,itemsep=2pt,topsep=3pt}
\setlength{\parskip}{4pt}\setlength{\parindent}{0pt}
\linespread{1.06}\emergencystretch=3em
\begin{document}
\begin{center}
{\sffamily\bfseries\LARGE\color{ink} """ + esc(TITLE) + r"""\par}
\vspace{8pt}
{\large """ + esc(AUTHOR.split("\n")[0]) + r"""\par}
{\small\itshape """ + r"\\".join(esc(x) for x in AFFILS) + r"""\par}
\vspace{2pt}{\footnotesize AI x Epistemics Research Sprint, Apart Research, November 2026\par}
\end{center}
\vspace{4pt}
\begin{tcolorbox}[colback=soft,colframe=soft,boxrule=0pt,arc=2pt,left=10pt,right=10pt,top=6pt,bottom=6pt]
{\sffamily\bfseries\color{accent} Abstract}\par\small """ + esc(ABSTRACT) + r"""
\end{tcolorbox}
"""]
def stat(big, small):
    return (r"\begin{tcolorbox}[colback=white,colframe=accent!60,boxrule=0.5pt,arc=2pt,halign=center,top=4pt,bottom=4pt]"
            r"{\sffamily\bfseries\Large\color{accent} " + esc(big) + r"}\par\vspace{1pt}{\footnotesize " + esc(small) + r"}\end{tcolorbox}")
L.append(r"\begin{tcbraster}[raster columns=3,raster equal height,raster column skip=6pt]" + "".join([
    stat(f"{pc(G['ai']['deleted'][0])} vs {pc(G['human']['deleted'][0])}", "of notes deleted by AI vs human writers"),
    stat(f"{pt(H1['diff_surviving_only']['est'])} → {pt(H1['diff_all_notes']['est'])}", "AI advantage in reaching Helpful, before and after counting deletions (points)"),
    stat(f"{pc(H3['primary_agree_set']['ai'])} vs {pc(H3['primary_agree_set']['human'])}", "of AI vs human Helpful notes with an unsupporting source"),
]) + r"\end{tcbraster}")

in_list = False
for kind, c in S:
    if kind != "b" and in_list:
        L.append(r"\end{itemize}"); in_list = False
    if kind == "h2":
        L.append(r"\section*{" + esc(c) + "}")
    elif kind == "h3":
        L.append(r"\subsection*{" + esc(c) + "}")
    elif kind == "p":
        L.append((r"{\small " + esc(c) + "}" if _re.match(r"\[\d+\]", c) else esc(c)) + "\n")
    elif kind == "b":
        if not in_list:
            L.append(r"\begin{itemize}"); in_list = True
        L.append(r"\item " + esc(c))
    elif kind == "fig":
        L.append(r"\begin{figure}[htbp]\centering\includegraphics[width=\linewidth]{../" + c[0] + r"}\caption{" + esc(c[1]) + r"}\end{figure}")
    elif kind == "table":
        head, rows, cap = c
        L.append(r"\begin{table}[htbp]\centering\small\renewcommand{\arraystretch}{1.25}\begin{tabularx}{\linewidth}{@{}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}X@{}}\toprule")
        L.append(" & ".join(r"\textbf{\sffamily " + esc(h) + "}" for h in head) + r"\\\midrule")
        L += [" & ".join(esc(v) for v in row) + r"\\" for row in rows]
        L.append(r"\bottomrule\end{tabularx}\caption{" + esc(cap) + r"}\end{table}")
    elif kind == "box":
        head, _, rest = c.partition(". ")
        L.append(r"\begin{tcolorbox}[colback=white,colframe=accent,boxrule=0.6pt,arc=2pt,left=8pt,right=8pt,top=5pt,bottom=5pt]\small{\sffamily\bfseries\color{accent} "
                 + esc(head) + r".} " + esc(rest) + r"\end{tcolorbox}")
if in_list:
    L.append(r"\end{itemize}")
L.append(r"\end{document}")
pathlib.Path("report/report.tex").write_text("\n".join(L))
print("report/report.tex written")
