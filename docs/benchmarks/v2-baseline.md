# Lore v2 Baseline Benchmarks

Date: 2026-03-04
Environment: Windows, Python 3.12.10, SQLite in-memory

## Scale Benchmark (1,000 events / 6 domains)

- store + derive (1000 events): `7.647s`
- retrieve context pack (health, query=benchmark): `0.070s`
- delete_and_recompute (single event): `0.027s`
- deletion verified: `true`
- artifact: `tests/benchmark_results.json`

## Verification Timings

- `py -m pytest tests/unit tests/integration -q`: 0.663s
- `py run_eval.py`: 0.079s

## Functional Baseline

- Unit + integration: evolving with branch task execution
- Eval scenarios: 12/12 steps passed
- Deletion compliance: 2/2
- Resurface incidents: 0
