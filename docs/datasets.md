# Datasets reviewed

The spec names SROIE, CORD and DocILE as candidates. Each was reviewed for what it contains, its licence, its format and whether it suits LedgerLens.

| Dataset | Contents | Format | Licence and access | Use it? |
|---|---|---|---|---|
| **SROIE** (ICDAR 2019) | 1,000 scanned receipt images with text boxes, transcripts and 4 key fields: company, address, date, total | Images with text annotation files | No clear licence found during this review; the official competition page should be checked before redistributing anything | Not in iteration 1. Possibly for receipt OCR testing in iteration 2. |
| **CORD** (Clova AI) | 1,000 Indonesian receipts (800 train, 100 validation, 100 test) with text boxes and multi-level semantic labels | Images with JSON annotations, also on Hugging Face | CC BY 4.0 | Not in iteration 1. The clearest licence of the three, so a good option for receipts in iteration 2. |
| **DocILE** (Rossum and partner universities) | About 6,700 annotated business documents, 100,000 synthetic documents and nearly 1 million unlabelled documents, with 55 field classes | PDFs and images with annotations | Needs a secret token from the project site. The code is MIT; the repository README doesn't state the dataset licence, so its terms must be confirmed first. | Not in iteration 1. The best match for invoices, worth applying for access in iteration 2. |

## Decision for iteration 1

The labelled set in `data/labelled` is **fully synthetic**, for three reasons:

- Iteration 1 only extracts invoices, and SROIE and CORD are receipts.
- None of the three is built around euro amounts and Irish day-first dates, which is LedgerLens's target.
- Synthetic documents come with exact answers, contain no real personal data and are free to commit to the repo.

The limitation is that synthetic documents are cleaner than real ones, so accuracy on this set will be higher than on real documents. The public datasets are for iteration 2, when receipts arrive and the evaluation grows.

## Synthetic generator

`scripts/generate_invoices.py` uses ReportLab and Faker to create invoices in three layouts, with different labels, date formats and VAT rates. Every third document becomes a slightly rotated and blurred photo. Each document gets a JSON file with the correct answers, and `manifest.csv` records the source of every document.

## Sources

- [SROIE competition paper](https://arxiv.org/abs/2103.10213)
- [CORD repository](https://github.com/clovaai/cord)
- [DocILE repository](https://github.com/rossumai/docile) and [benchmark paper](https://arxiv.org/abs/2302.05658)
