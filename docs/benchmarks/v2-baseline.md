# Orenyl v2 Baseline Benchmarks

Date: 2026-04-08
Environment: Windows, Python 3.12.10, SQLite in-memory

## Verified Artifact Snapshot (1,000 events / 6 domains)

- store + derive (single event at 1K corpus): `17.8ms`
- retrieve context pack (health, query=benchmark): `23.5ms`
- delete_and_recompute (single event): `28.4ms`
- context pack items returned: `50`
- deletion verified: `true`
- artifact: `tests/benchmark_results.json`

## Verification

- `python scripts/run_benchmarks.py`
- `python -m pytest tests/benchmarks/test_phase1_retrieval_quality.py tests/benchmarks/test_phase1_vector_signal_quality.py tests/integration/test_scale_benchmark.py -q`
- `python scripts/run_eval.py`

## Functional Baseline

- Unit + integration benchmark gates: verified on 2026-04-08
- Eval scenarios: 12/12 steps passed
- Deletion compliance: 2/2
- Resurface incidents: 0

## Phase 1 Retrieval Quality (2026-03-10)

- Corpus file: `scenarios/phase1_retrieval_corpus.json`
- Harness: `run_phase1_precision_eval()` in `scripts/run_eval.py`
- Metric: Top-3 key precision over synthetic corpus
- Top-3 precision: `1.00`
- Gate: `python -m pytest tests/benchmarks/test_phase1_retrieval_quality.py -q`
- Note: This is a synthetic regression signal, not a production relevance benchmark.
- Additional vector-signal gate: `python -m pytest tests/benchmarks/test_phase1_vector_signal_quality.py -q`

## Phase 3 Isolation + Federation Gates (2026-03-13)

- Tool isolation suite: `python -m pytest tests/integration/test_phase3_tool_isolation.py -q`
- Federation idempotency/conflict suite:
  `python -m pytest tests/integration/test_federation_worker_idempotency.py tests/integration/test_federation_conflict_resolution.py -q`
- Sync envelope/journal suite:
  `python -m pytest tests/unit/test_sync_envelope_validation.py tests/integration/test_sync_journal_persistence.py -q`

## Phase 3 Multi-Tenant Load Harness (Opt-in)

- Test: `tests/benchmarks/test_phase3_multi_tenant_load.py`
- Disabled by default.
- Enable with:
  `ORENYL_ENABLE_PHASE3_LOAD_TEST=1`
- Configurable event count:
  `ORENYL_PHASE3_LOAD_EVENTS` (default `1000000`)

## Published Benchmarks (2026-04-08)

Environment: Windows, Python 3.12.10, SQLite in-memory

Methodology:
- Preload a corpus of `N` events plus one synthetic derived fact and lineage edge per event to approximate a populated steady-state corpus without reintroducing the benchmark script's old O(n^2) bulk-load pattern.
- Use those synthetic seeded facts as benchmark fixtures so retrieval and post-delete checks run against a populated corpus; the probe event itself is still measured via the real `insert + derive` path.
- Measure a single probe event's `insert + derive` latency at corpus size `N`.
- Measure `retrieve_context_pack` and `delete_and_recompute` immediately after that probe ingest.

| Operation | 1K events | 10K events | 100K events |
|-----------|-----------|------------|-------------|
| insert + derive (single event) | `17.1ms` | `170.0ms` | `2068.8ms` |
| retrieve_context_pack | `24.2ms` | `149.2ms` | `1526.1ms` |
| delete_and_recompute | `27.7ms` | `294.0ms` | `3615.7ms` |
| deletion_verified | `True` | `True` | `True` |

Notes:
- These values were re-run on 2026-04-08. Expect small run-to-run variation on the same machine.
- The 100K retrieval and deletion numbers are materially slower than 10K and should be treated as honest current-state measurements, not aspirational targets.
- These timings reflect the lineage engine's current O(n) scan behavior for operations at corpus size `N`, which is acceptable for now but a reasonable target for future scaling work.
