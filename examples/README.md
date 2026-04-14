# Examples

These are copy-paste-run demos for Orenyl's core public-beta flows. They all run locally with an in-memory database, so there is no extra setup beyond installing the package from this repo today.

## Install once

```bash
git clone https://github.com/edison-zhou-nc/Orenyl.git
cd Orenyl
python -m pip install -e .
```

When `0.5.0` is published, the package install will be:

```bash
pip install orenyl-mcp-server
```

## Copy-paste-run demos

### Personal health tracker

```bash
python examples/personal-health-tracker/health_tracker.py
```

Shows storing health events, retrieving context, deleting an allergy record, and confirming the deleted content does not resurface.

### Meeting memory

```bash
python examples/meeting-memory/meeting_memory.py
```

Shows note ingestion, lineage-aware summary derivation, and recomputation after a meeting is deleted.

### Multi-agent shared memory

```bash
python examples/multi-agent-shared-memory/shared_memory.py
```

Shows two tenants sharing one Orenyl instance while retrieval remains isolated per tenant.
