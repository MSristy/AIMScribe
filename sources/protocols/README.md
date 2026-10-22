# Original protocol PDFs (local files)

Original PDFs are not distributed in this public source-code snapshot. Obtain the supplied editions through the assessment/provider and put them here using these exact names:

| Filename | Assigned PDF positions |
|---|---|
| `Bangladesh dengue guideline (2025).pdf` | 26–28, 37–41, 45–48 |
| `National Guideline on Hypertension Bangladesh.pdf` | 46–52, 64–65 |
| `Clinical tools for cholera treatment facilities2024(WHO).pdf` | 5–14 |
| `National Guideline on Clinical Management of Chikungunya Fever (2017).pdf` | 11–22, 26–27 |

Count the cover as page 1. The 45 assigned pages include tables and footnotes; hypertension PDF page 64 contains the full treatment diagram. `../source_manifest.json` records editions, file references and assigned ranges. Existing extracted records retain the original source file hashes for verification.

The app runs using the included canonical cards and BM25 index without these PDFs. To regenerate extraction and visual review images after obtaining the originals:

```powershell
python scripts/extract_assigned_pages.py
python scripts/render_assigned_pages.py
```

Generated images go to `data/rendered/` and remain local. Extraction is a review aid; inspect original diagrams/tables/footnotes visually. Do not replace original source evidence with guessed text.
