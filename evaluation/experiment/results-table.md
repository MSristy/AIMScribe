# Q2 comparison results

P = pass; F = fail; NA = not applicable. Source codes: D = Bangladesh dengue 5e (2025); H = Bangladesh hypertension 2e (2023); C = WHO cholera (2024); K = Bangladesh chikungunya (2017). Numbers are PDF positions, cover counted as page 1. Full reasons and per-check source IDs/pages: `manual_reviews.json`.

| Case | Mode | Expected | Citations | Restrictions | Missing info | Seconds | Source PDF pages | Failure / limitation |
|---|---|---|---|---|---|---:|---|---|
| C01 | baseline | P | P | P | P | 1.6708 | D27,37,39,41,45,47-48; K21-22 | Generic ask wording remains. |
| C01 | improved | P | P | P | P | 1.5561 | D27,37,39,41,45,47-48; K21-22 | Generic ask wording remains. |
| C02 | baseline | P | P | P | P | 1.3237 | H46,51,64-65 | None observed. |
| C02 | improved | P | P | P | P | 1.3948 | H46,51,64-65 | None observed. |
| C03 | baseline | P | P | P | P | 1.6055 | C5-6,9-10 | None observed. |
| C03 | improved | P | P | P | P | 1.6479 | C5-6,9-10 | None observed. |
| C04 | baseline | P | P | P | P | 1.4666 | K11,17-22,26-27; D39,41,45,47 | Raw admission error; shared guard withheld. |
| C04 | improved | P | P | P | P | 1.524 | K11,17-22,26-27; D39,41,45,47 | Raw admission error; shared guard withheld. |
| C05 | baseline | F | P | P | P | 1.4124 | D27-28,37,45-48; K11,22 | Epidemiology clarification missing; conditional tests omitted. |
| C05 | improved | F | P | P | P | 1.6209 | D27-28,37,45-48; K11,21-22 | Epidemiology clarification missing; conditional tests added. |
| C06 | baseline | P | P | P | P | 1.45 | H46,51,64-65 | None observed. |
| C06 | improved | P | P | P | P | 1.4791 | H46,51,64-65 | None observed. |

## Counts and denominators

| Check | Baseline P/F/NA | Improved P/F/NA |
|---|---|---|
| expected_behaviour | 5/1/0 (of 6; applicable 6) | 5/1/0 (of 6; applicable 6) |
| citation_support | 6/0/0 (of 6; applicable 6) | 6/0/0 (of 6; applicable 6) |
| restrictions | 6/0/0 (of 6; applicable 6) | 6/0/0 (of 6; applicable 6) |
| missing_information | 6/0/0 (of 6; applicable 6) | 6/0/0 (of 6; applicable 6) |

Baseline: 23/24 passed checks; 5/6 cases passed all four checks; mean elapsed 1.4882 s; input tokens 35905; completion tokens 2516.

Improved: 23/24 passed checks; 5/6 cases passed all four checks; mean elapsed 1.5371 s; input tokens 36613; completion tokens 2525.

Matched fail-to-pass gains: 0; pass-to-fail losses: 0. Additional improved input tokens: 708; additional model calls per case: 0. Quota waits excluded from elapsed times. No unsupported clinical accuracy claim.
