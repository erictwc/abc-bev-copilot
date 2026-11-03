# data/

Synthetic tables for ABC-BEV-CO, written by a seeded generator (`make data`, ticket T1).
Same seed, byte-identical output. The planted problems are listed in `docs/DATA.md`.

`generate.py` writes `csv/` (six tables plus `SHA256SUMS`). `make data-check` proves two runs
match the committed files byte for byte. Tables, row counts and names: `docs/DATA.md`.
