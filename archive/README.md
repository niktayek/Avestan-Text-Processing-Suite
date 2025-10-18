This `archive/` folder contains experimental scripts, intermediate exporter variants, old result files and traces that are not part of the canonical pipeline used to generate `res/stanza_word_matches_0005_greedy_vs_dp.csv`.

Why archived
- Reduce noise in `scripts/` and `res/` so the canonical pipeline and outputs are easy to find.
- Preserve history and allow easy restoration via `git` if any archived file is needed later.

Structure
- scripts_experimental/: experimental and one-off scripts that were useful during development.
- res_old/: older CSV/JSON outputs, diagnostic traces, and temporary files.

How to restore
- Use `git mv` to move files back from `archive/` into their original locations, or check them out from git history.

If you want other files archived or a different structure, open an issue or message and I'll adjust.
