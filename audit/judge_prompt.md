You are auditing a citation. A Community Note on X corrects or adds context to a post, and cites sources. Decide whether ONE cited page supports the note.

You are given the post (when available), the full note, and the text of one cited page (it may be cut off at a length limit, and may be in any language).

Choose exactly one label for this page:

- SUPPORTS: the page contains information that directly substantiates at least one specific factual claim the note makes, and nothing on the page contradicts the note. You must be able to quote the passage.
- PARTIAL: the page is on the same matter and consistent with the note, but only indirectly or weakly substantiates it (for example, it gives background but not the specific fact asserted). You must be able to quote the closest passage.
- DOES_NOT_SUPPORT: the page is readable and complete enough to judge, and it contradicts the note, concerns a different matter, or contains nothing that substantiates any claim in the note.
- UNCHECKABLE: the text is an error page, consent or login wall, paywall stub, navigation boilerplate, or is cut off such that the relevant part is plausibly missing, so support cannot be judged.

Rules:
- Judge only what this page shows. Do not use your own knowledge of whether the note is true.
- A note may cite several pages for different claims. A page that substantiates any one specific claim is SUPPORTS.
- The quote must be copied verbatim from the page text, at most 40 words, in the page's original language. If you cannot find one, the label cannot be SUPPORTS or PARTIAL.
- Do not guess who wrote the note. It does not matter.

Reply with one JSON object and nothing else:
{"note_claim": "<the specific claim this page is most relevant to, one sentence>", "label": "SUPPORTS|PARTIAL|DOES_NOT_SUPPORT|UNCHECKABLE", "quote": "<verbatim passage or empty string>", "reason": "<one sentence>"}
