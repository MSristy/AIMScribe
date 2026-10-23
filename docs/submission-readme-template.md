# Clinical NLP assessment submission

This folder contains the runnable two-mode prototype and all requested assessment deliverables. Start here. All patients are fictional. The six self-authored cases and assistant source review are not independent clinical validation.

The approved visual interface includes White/Black appearance through the sidebar sun/moon button, a compact workflow guide and local assets in `ui/`. Keep that folder beside `app.py`. Appearance changes do not change patient information, model settings, retrieval or clinical results.

Post-comparison retrieval maintenance (2026-10-23): 10 cards is a maximum, not a target. Explicit English negative/unknown clauses are excluded from search text, positive source-authored symptom anchors are required, and category coverage never pads with unrelated/zero-score cards. Zero relevant cards displays Insufficient evidence and skips the model call. Raw patient information remains unchanged. The complete software suite passes 49 tests. This limited heuristic is not comprehensive NER or clinical validation. The original 12-output experiment and its results are unchanged and apply to the original 19 source files preserved exactly in evaluation/experiment/frozen-source.zip. A separate maintenance-release.json verifies current runtime hashes; this maintenance release has not undergone a new paired model comparison.

## Requirement-to-file map

| Requirement | Location |
|---|---|
| Canonical recommendation cards | `data/cards/cards.jsonl` (32 cards) |
| Card schema, fields and reasoning example | `data/cards/card.schema.json`, `docs/q1-card-guide.md` |
| Runnable two-mode interactive application | `app.py`, `src/`, `.streamlit/config.toml`, `requirements.txt` |
| RAG index and rebuild instructions | `data/index/bm25.json`, `scripts/build_index.py` |
| Model/settings and detailed prototype README | `docs/prototype-readme.md` |
| Six authoritative frozen case inputs | `evaluation/experiment/cases.json` |
| Source-linked expected-behaviour checklists | `evaluation/experiment/checklists.json` |
| Prespecified plan, freeze and source review | `evaluation/experiment/plan.md`, `manifest.json`, `source_review.json` |
| Original frozen source and current maintenance provenance | `evaluation/experiment/frozen-source.zip`, `maintenance-release.json` |
| Twelve fresh saved outputs | `evaluation/experiment/outputs/` |
| Four checks, source pages and reasons per output | `evaluation/experiment/manual_reviews.json` |
| Compact results table and machine-readable counts | `evaluation/experiment/results-table.md`, `results.json` |
| Short comparison note, separate from table | `evaluation/experiment/comparison-note.md` (392 words) |
| Complete architecture and design defence | `docs/architecture.svg`, `.png`, `.mmd`; master documentation section 18 |
| Paper summary | `docs/paper-summary.txt` (256 words) |
| Offline ten-slide deck, including Bengali notes | `slides/Clinical_NLP_Research_Prototype.pptx` |
| Editable Canva link and content/timing backup | `slides/canva-delivery.json`, `slides/q4-slide-content.json` |
| Tools and AI assistance disclosure | `AI_ASSISTANCE_DISCLOSURE.md` |
| Full development documentation | `docs/project-documentation.md` |
| Package integrity and preparation checks | `submission-manifest.json`, `submission-validation.json` |

The authoritative final experiment is `evaluation/experiment/`, not development drafts. Draft input/checklist files remain because the interactive examples, development utilities and tests use them. Expected answers/checklists are evaluation-only and never indexed or put into inference prompts.

## Launch the prototype

Unzip into a new directory, open this `submission` folder in VS Code, and run the commands below from this folder. Do not run from inside `src` or `scripts`. Development and the package check used Windows Python 3.15; dependencies are listed in `requirements.txt`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Copy the example only when creating a fresh local configuration; do not overwrite an existing credential file. The example has **empty keys** and `free_tier_confirmed = false`. It selects the experiment's Groq model. Add your own Groq API key locally under `[groq]`, and set that confirmation flag to true only after verifying a Free plan with no billing/payment. No credential is supplied in this submission. Do not upload the filled file. The original developer's credentials are intentionally excluded.

```powershell
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

Open http://127.0.0.1:8501/ while the server runs. Enter symptoms and available patient details without requiring a disease name. **Preview evidence** uses local retrieval without a generation. **Generate care plan** needs Internet, a valid configured key and provider quota when relevant evidence exists. With zero relevant cards it abstains locally and makes no model request. Use the same interface's **Recommendation mode** selector for Baseline/Improved. Allow at least 65 seconds between requests under the recorded free quota. Future provider/model availability and quotas may change; do not silently substitute another model and describe it as the original comparison.

Active experiment model: Groq `qwen/qwen3.8-27b`, temperature 0, reasoning `none`, maximum completion 900 tokens, at most 10 retrieved cards. Only Improved adds the pre-model `applicability_preview`; retrieval, source corpus, model/settings, renderer and final checks remain fixed. Model settings do not guarantee identical repeated generations.

## Offline verification and rebuild

This standard-library check requires no API key or additional packages:

```powershell
python scripts/verify_submission.py
```

It checks packaged file hashes, the original 19 frozen hashes inside the archived source and current maintenance hashes, all 12 reviewed-output hashes, six cases/checklists, 32 cards, summary length, slide/note counts and absence of credentials. It verifies integrity and structure, not clinical correctness. Do this before making changes. Generated validation reports, edited files or a new real-key configuration change the original package snapshot, so a later integrity mismatch must be interpreted accordingly.

After dependencies are installed:

```powershell
python -m unittest discover -s tests -v
python scripts/validate_cards.py --input data/cards/cards.jsonl
python scripts/validate_cases.py
python scripts/inspect_comparison.py --case C02 C06
```

After copying the **empty** example configuration, `python scripts/report_comparison.py` can verify/recompile the saved experiment without an API call. Do not confuse `validate_cases.py`'s development-draft `frozen: false` report with the authoritative frozen experiment manifest. Never revise the frozen checklists to fit model output.

The ready index is included, so no rebuild is needed to inspect/run the package. If deliberately rebuilding, use `python scripts/build_index.py`; changing canonical cards/index or frozen runtime invalidates the delivered experiment hashes. Preserve an untouched original submission for comparison. The 12-call runner refuses to overwrite the delivered outputs. A new replication needs a separate copy, preserved original evidence, an empty destination and independently labeled new results.

Original full protocol PDFs, the research paper PDF and rendered source-page images are not required at runtime and are not bundled. They were supplied reading materials, not newly authored deliverables. `sources/source_manifest.json` and `sources/protocols/README.md` identify editions, filenames and assigned page positions for optional extraction/render rebuild. Assigned text and card evidence are included. Reviewers should consult their supplied originals for authoritative tables/footnotes; full-PDF copying would unnecessarily enlarge this archive. No additional clinical pages outside the registered assigned excerpts were used for the authored recommendations.

## Results and presentation

Both modes passed **23/24 checks** and **5/6 cases passed all four checks**. C05's key expected exposure clarification failed in both modes. Citations, restrictions and missing-information honesty each passed 6/6 under assistant source review. The preview added 708 input tokens across six cases, with no extra calls. These are checklist counts, not clinical accuracy or proof that RAG beats no retrieval. The saved comparison note discusses limitations and possible model variability.

Open the PowerPoint offline or use the Canva edit URL from `slides/canva-delivery.json` in the owner's account. Canva sharing permissions were not made public; the offline PPTX allows assessment without Canva access. Text/table values and Bengali notes are in the deck; some decorative/diagram graphics are image objects. Per-slide presenter-note targets total ten minutes for manual delivery. Default five-second animation timing is not the talk schedule. Rehearse before the interview, then demonstrate C02/C06 and a new fictional input. A saved output is not a live generation.

## Submission scope

API keys, `.venv`, `.git`, local account diagnostics, caches and private logs are excluded. NER, doctor acceptance, feedback storage, signed prescription assembly and hospital integration are future design only. No training, paid deployment or production clinical validation is claimed. This archive is prepared for the portal; the user must upload it and perform the interview/live demonstration.
