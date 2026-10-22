# Prespecified Q2 two-mode experiment

Written before freezing and before any final comparison calls. This is a within-RAG experiment, not RAG versus no retrieval. The six cases are self-authored and were already used in development; this is not a held-out clinical study.

## Weakness and one change

The basic model must interpret nested prerequisites/exclusions while also selecting evidence and questions. It can defer an already resolved branch or overlook an unknown condition. Final deterministic checks already protect several branches, but they cannot ensure the model notices all useful evidence/clarifications.

**Baseline:** retain the current reasonable evidence-referenced prompt, patient facts, canonical clinical fields, BM25 ranking with the existing diagnostic-protocol/category coverage policy (maximum 10), structured output contract and final source guards/advice links. It is not deliberately weakened. This is the current developed baseline, not a newly stripped prompt.

**Improved:** add exactly one user-context field, `applicability_preview`, mapping each retrieved card ID to the limited observed-source review status: blocked, eligible, needs_information, trigger_review or model_review. Unresolved statuses do not imply eligibility. The preview uses the same runtime checker already applied after model selection in both modes; it is not a new checker or a gold answer. No extra model call, corpus edit, retrieval change, new question policy or postprocessing change.

Hypothesis: making these intermediate statuses visible before selection will reduce missed appropriate branches and inappropriate/omitted clarifications. Added cost: local checks for up to 10 cards, added prompt tokens and possible response latency; no extra API call. Measure actual token use and total elapsed time, excluding quota waits. Report a negative result if improved has no net increase in passed checks, or introduces additional failures; any gain accompanied by regressions is mixed, not a universal improvement. A tie with extra cost does not demonstrate benefit.

## Fixed components and order

Use Groq qwen/qwen3.8-27b, temperature 0, reasoning none, max completion 900, one fresh call per case/mode. Same patient JSON, 32-card corpus/index, retrieval hits/order, system prompt, schema, source guards, renderer and question registration in each pair. No answer/checklist/case ID goes into prompts/index. Add case labels only after inference. Existing source passages stay in full run records/UI; the unchanged model projection contains canonical clinical fields and source references. No model training or paid fallback.

Run paired case order C01 through C06, alternating first mode to reduce a simple order confound: C01 B/I, C02 I/B, C03 B/I, C04 I/B, C05 B/I, C06 I/B. Space starts at least 65 seconds. Preserve failures; stop on provider/format failure rather than replacing an answer. A failure requires a documented procedural amendment and a new complete comparison run; never silently cherry-pick retries. One observation per pair cannot separate model variability from a treatment effect.

## Freeze and evaluation

After software development/tests, freeze copies of the unchanged six inputs and existing source-linked checklists, this plan, corpus/index, model settings and runtime code hashes. The original draft remains historical. Frozen checklist wording must not be revised to fit outputs. Keep SHA256 hashes and UTC freeze time in `manifest.json`; verify before/after the run. No policy replay in final outputs.

For every output manually review all four checks using original protocol text/PNG, not just card IDs: (1) key expected behaviour including its conditions, (2) every displayed action supported by its cited evidence and source applicability, (3) relevant restrictions retained/no listed unsupported action, (4) missing patient/medication information handled without guessing or false claims of supplied facts missing. Mark pass/fail/NA, short reason and PDF page(s); fail an omitted required behaviour even if format/citations are valid. Do not count withholding every action as a full pass. For API failures use fail for expected behaviour and NA for content checks with no output, reporting both NA and denominators. Report each check's pass/fail/NA per mode, all-four-pass cases out of six, matched gains/losses, elapsed times and failure notes. The overall denominator is not a clinical accuracy statistic.

Output: two modes in one app, frozen cases/checklists/manifest, 12 exact fresh run records, manual review JSON, compact results table and a comparison note of at most one page (target <=450 words, table separate). Discuss a failure/unchanged/worse outcome; if all pass, hardest case and untested limitation. Next test: repeated matched runs and independent cases/review, not an accuracy claim from six examples.
