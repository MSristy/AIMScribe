# Q1: canonical cards and representation choice

The canonical dataset is `data/cards/cards.jsonl`: 32 manually curated cards from the four assigned protocols. `data/cards/card.schema.json` defines the common structure. `scripts/build_cards.py` packages the authored content deterministically; no model automatically extracted clinical recommendations. `scripts/validate_cards.py` checks schema, IDs and source/reference consistency, not clinical validity.

| Field | Meaning |
|---|---|
| `schema_version`, `card_id` | Format version and unique recommendation identifier |
| `disease`, `clinical_category`, `title` | Protocol domain, one of the four output categories, readable label |
| `clinical_context`, `relevant_symptoms` | Relevant presentation or treatment context |
| `applicability` | Structured prerequisite expression, preserving AND/OR dependencies |
| `exclusions` | Source-supported conditions that block the dependent branch |
| `required_patient_fields` | Referenced clinical condition fields, not a claim that all are always unknown |
| `recommended_action` | Source-supported recommendation |
| `medications` | Available name, dose, route, frequency, duration and instructions, with evidence references |
| `investigation_details`, `monitoring_details` | Optional source-supported purpose, timing and conditions |
| `missing_information_policy` | Preserve uncertainty, clarify dependent gaps and retain independent actions |
| `evidence` | Linked evidence IDs, source ID/title/version, PDF page, locator, kind and supporting passage |
| `limitations` | Boundaries and source-unspecified details |

Cards cover probable diagnosis, investigations, medication guidance and advice for the six demonstrated cases across dengue, hypertension, cholera and chikungunya. Card count follows demonstrated coverage, with no atom quota or claim of exhaustive guideline coverage. Multiple evidence passages can jointly support one recommendation, including figure and footnote dependencies. Page positions count the PDF cover as page 1.

Medication null fields mean the source does not specify that prescription field. They must not be filled from model memory. Patient null fields instead mean unknown patient information. False means an explicitly negative finding; an assessed empty list differs from an unassessed list. Evidence passages are manually selected/abridged transcriptions with documented normalization, not guaranteed verbatim quotations. Original supplied PDFs remain authoritative.

## Reasoning example: hypertension treatment escalation

Source: Bangladesh hypertension guideline, second edition 2023, PDF page 64, Figure 8 and its treatment footnotes/pregnancy-potential restriction.

**Alternative A, prose only:** store a sentence to add losartan 50 mg to amlodipine 5 mg after the relevant follow-up period if BP remains above the assessed target, with restrictions in the same text. This is easy to author and retrieve, but enforcement depends on the model attending to every footnote.

**Alternative B, implemented:** store the same source-supported action with structured prerequisites, separate exclusions and linked source evidence. Follow-up context includes the documented regimen, interval, target status, adherence and required pre-losartan checks. Current pregnancy and pregnancy potential are represented explicitly. The distinct source-supported alternative branch has its own card. Source-unspecified route or fixed duration stays null.

**Why B:** conditions are inspectable and reusable by the limited checker. Known exclusions can block an action, while unknown mapped prerequisites lead to clarification. This costs manual condition/question mapping and does not eliminate normalization, retrieval or clinical interpretation errors. Reviewed lab flags do not establish acceptable numeric renal/potassium eligibility; no thresholds were invented.

**Where A could fail:** an adult taking amlodipine 5 mg daily for the required follow-up period has BP above target and good adherence, but may become pregnant. A model focusing on the escalation sentence could overlook the source warning and select losartan. The structured branch retains that exclusion. C02/C06 demonstrate this change: only pregnancy potential changes, while current pregnancy remains false. Unknown pregnancy potential must not count as a negative finding.

Only B is implemented in the dataset. A is an explanatory alternative, not an extra dataset. Both experimental modes receive the same structured cards and use the same final checks. The sole tested improvement is **pre-model `applicability_preview`**, not adding the post-model checker only to Improved. The final comparison did not demonstrate a net checklist gain.
