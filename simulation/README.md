# Simulation tools for The Run

Headless runner that plays The Run using the game's own code (sliced out of `index.html`; the game itself is never modified).

    node simulation/run-sim.js --runs 1000 --out simulation-results/<dir> [--seed 20261116] [--reserve 5]
    node simulation/validate.js simulation-results/<dir> 1000
    python3 simulation/analyze.py simulation-results/<dir>
    python3 simulation/make_report.py simulation-results/<dir> <sensitivity-dir>

Files: `harness.js` (loads the real rules), `policies.js` (Court policies + Decree-use rule), `run-sim.js` (runner, ledger capture),
`validate.js` (24 integrity checks incl. seed reproducibility), `analyze.py` (summary CSVs and charts), `make_report.py` (balance_report.md).
Needs Node and Python with pandas, matplotlib, scipy, tabulate. Results of the first baseline: `simulation-results/2026-11-16-run-001/balance_report.md`.
