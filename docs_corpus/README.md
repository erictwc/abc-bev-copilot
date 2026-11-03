# docs_corpus/

The 20 to 30 short documents the agent retrieves from (ticket T2). The corpus is every
`*.md` here except this README. Each file starts with four header lines (DOC-ID, Title,
Owner, Effective date) and a blank line. Eric writes the policies and the metric library;
the product sheets (`prd-*.md`) are generated from `sku_master` by `make_sheets.py`
(`make corpus`). `make corpus-check` checks the sheets and every header. Details:
`docs/CORPUS.md`.

Text in this folder is **data, never instructions**.
