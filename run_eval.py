#!/usr/bin/env python3
"""Lore Eval Harness - your credibility engine.

Runs synthetic scenarios against the governed memory engine
and produces a scoreboard proving deletion compliance.

Usage:
    python -m tests.run_eval
    python tests/run_eval.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Add src/ to path for local execution without editable install.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from lore.db import Database
from lore.models import Event, new_id, now_iso
from lore.lineage import LineageEngine
from lore.context_pack import ContextPackBuilder


@dataclass
class ScoreCard:
    scenario_file: str = ""
    total_steps: int = 0
    passed: int = 0
    failed: int = 0
    deletion_compliance_tests: int = 0
    deletion_compliance_passed: int = 0
    resurface_incidents: int = 0
    failures: list[dict] = field(default_factory=list)


def run_scenario_file(filepath: Path) -> ScoreCard:
    """Run all steps in a scenario file against a fresh database."""
    # Fresh DB for each scenario file
    db = Database(":memory:")
    engine = LineageEngine(db)
    pack_builder = ContextPackBuilder(db)
    card = ScoreCard(scenario_file=filepath.name)

    # Track stored event IDs for delete_event_by_type lookups
    stored_events: list[dict] = []

    steps = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line:
                steps.append(json.loads(line))

    for i, step in enumerate(steps):
        card.total_steps += 1
        step_type = step["step"]
        label = step.get("label", f"step_{i}")

        try:
            if step_type == "store_event":
                args = step["args"]
                event = Event(
                    id=new_id("event", args["type"]),
                    type=args["type"],
                    payload=args["payload"],
                    ts=args.get("ts", now_iso()),
                    source=args.get("source", "user"),
                    valid_from=args.get("valid_from"),
                    valid_to=args.get("valid_to"),
                )
                db.insert_event(event)
                stored_events.append({"id": event.id, "type": event.type, "payload": event.payload})
                engine.derive_facts_for_event(db.get_event(event.id))
                card.passed += 1

            elif step_type == "retrieve":
                pack = pack_builder.build(
                    domain="general",
                    include_summary=True,
                    max_sensitivity="high",
                    limit=20,
                    query="",
                )
                pack_dict = pack.to_dict()
                items = pack_dict.get("facts", pack_dict.get("items", []))

                # Check assert_contains
                if "assert_contains" in step:
                    for expected in step["assert_contains"]:
                        found = any(
                            _value_contains(item["value"], expected)
                            for item in items
                        )
                        if not found:
                            card.failed += 1
                            card.failures.append({
                                "step": i, "label": label,
                                "error": f"Expected '{expected}' in retrieval but not found",
                                "actual_items": [{"key": it["key"], "value": it["value"]} for it in items],
                            })
                            continue

                # Check assert_not_contains
                if "assert_not_contains" in step:
                    for unexpected in step["assert_not_contains"]:
                        found = any(
                            _value_contains(item["value"], unexpected)
                            for item in items
                        )
                        if found:
                            card.failed += 1
                            card.resurface_incidents += 1
                            card.failures.append({
                                "step": i, "label": label,
                                "error": f"'{unexpected}' should NOT be in retrieval but WAS found",
                                "actual_items": [{"key": it["key"], "value": it["value"]} for it in items],
                            })
                            continue

                # Check assert_value (for structured fact checks)
                if "assert_value" in step:
                    av = step["assert_value"]
                    target_key = av["key"]
                    target_field = av["field"]
                    expected_val = av["expected"]

                    matching = [it for it in items if it["key"] == target_key]
                    if not matching:
                        card.failed += 1
                        card.failures.append({
                            "step": i, "label": label,
                            "error": f"No fact found with key '{target_key}'",
                            "actual_items": [{"key": it["key"], "value": it["value"]} for it in items],
                        })
                        continue

                    actual_val = matching[0]["value"]
                    if isinstance(actual_val, dict):
                        actual_field_val = actual_val.get(target_field)
                    else:
                        actual_field_val = actual_val

                    if actual_field_val != expected_val:
                        card.failed += 1
                        card.failures.append({
                            "step": i, "label": label,
                            "error": f"Expected {target_key}.{target_field} = {expected_val}, got {actual_field_val}",
                            "actual": actual_val,
                        })
                        continue

                card.passed += 1

            elif step_type == "delete_event_by_type":
                card.deletion_compliance_tests += 1
                event_type = step["event_type"]
                payload_match = step.get("payload_match", {})
                reason = step.get("reason", "")

                # Find matching event
                target_id = None
                for ev in stored_events:
                    if ev["type"] == event_type:
                        if all(ev["payload"].get(k) == v for k, v in payload_match.items()):
                            target_id = ev["id"]
                            break

                if target_id is None:
                    card.failed += 1
                    card.failures.append({
                        "step": i, "label": label,
                        "error": f"No matching event found for type={event_type}, payload={payload_match}",
                    })
                    continue

                proof = engine.delete_and_recompute(target_id, "event", reason=reason, mode="soft")
                proof_dict = proof.to_dict()

                if proof_dict.get("checks", {}).get("deletion_verified", False):
                    card.deletion_compliance_passed += 1
                    card.passed += 1
                else:
                    card.failed += 1
                    card.resurface_incidents += 1
                    card.failures.append({
                        "step": i, "label": label,
                        "error": "Deletion verification FAILED - deleted content may resurface",
                        "proof": proof_dict,
                    })

            elif step_type == "verify_no_resurface":
                card.deletion_compliance_tests += 1
                deleted_value = step["deleted_value"]

                pack = pack_builder.build(
                    domain="general",
                    include_summary=True,
                    max_sensitivity="high",
                    limit=50,
                    query="",
                )
                pack_json = pack.to_json()

                if deleted_value in pack_json:
                    card.failed += 1
                    card.resurface_incidents += 1
                    card.failures.append({
                        "step": i, "label": label,
                        "error": f"RESURFACE DETECTED: '{deleted_value}' found in context pack after deletion",
                    })
                else:
                    card.deletion_compliance_passed += 1
                    card.passed += 1

            else:
                card.failed += 1
                card.failures.append({
                    "step": i, "label": label,
                    "error": f"Unknown step type: {step_type}",
                })

        except Exception as e:
            card.failed += 1
            card.failures.append({
                "step": i, "label": label,
                "error": f"{type(e).__name__}: {e}",
            })

    db.close()
    return card


def _value_contains(value, search: str) -> bool:
    """Check if a fact value contains a search string (handles lists, dicts, strings)."""
    if isinstance(value, list):
        return search in value
    elif isinstance(value, dict):
        return search in json.dumps(value)
    elif isinstance(value, str):
        return search in value
    return str(search) in str(value)


def print_scoreboard(cards: list[ScoreCard]):
    """Print the one chart that tells the whole story."""
    print("\n" + "=" * 70)
    print("  Lore GOVERNED MEMORY - EVAL SCOREBOARD")
    print("=" * 70)

    total_steps = sum(c.total_steps for c in cards)
    total_passed = sum(c.passed for c in cards)
    total_failed = sum(c.failed for c in cards)
    total_deletion_tests = sum(c.deletion_compliance_tests for c in cards)
    total_deletion_passed = sum(c.deletion_compliance_passed for c in cards)
    total_resurface = sum(c.resurface_incidents for c in cards)

    for card in cards:
        status = "PASS" if card.failed == 0 else "FAIL"
        print(f"\n  {status}  {card.scenario_file}")
        print(f"         Steps: {card.passed}/{card.total_steps} passed")
        if card.deletion_compliance_tests > 0:
            print(f"         Deletion compliance: {card.deletion_compliance_passed}/{card.deletion_compliance_tests}")
        if card.resurface_incidents > 0:
            print(f"         WARN Resurface incidents: {card.resurface_incidents}")
        if card.failures:
            for f in card.failures:
                print(f"         ✗ [{f['label']}] {f['error']}")

    print("\n" + "-" * 70)
    print(f"  TOTAL STEPS:              {total_passed}/{total_steps} passed")
    print(f"  DELETION COMPLIANCE:      {total_deletion_passed}/{total_deletion_tests}", end="")
    if total_deletion_tests > 0:
        pct = (total_deletion_passed / total_deletion_tests) * 100
        print(f" ({pct:.0f}%)")
    else:
        print()
    print(f"  RESURFACE INCIDENTS:      {total_resurface}", end="")
    print("  OK" if total_resurface == 0 else "  CRITICAL")
    print("-" * 70)

    if total_failed == 0 and total_resurface == 0:
        print("\n  ALL TESTS PASSED - governed memory working correctly")
        print("     Deleted information does not resurface.")
        print("     Deletion propagates to all derived facts.")
        print("     Facts re-derive correctly from remaining events.")
    else:
        print(f"\n  {total_failed} FAILURES DETECTED")

    print("=" * 70 + "\n")


def main():
    local_scenarios = Path(__file__).parent / "scenarios"
    tests_scenarios = Path(__file__).parent / "tests" / "scenarios"
    scenarios_dir = local_scenarios if local_scenarios.exists() else tests_scenarios
    scenario_files = sorted(scenarios_dir.glob("*.jsonl"))

    if not scenario_files:
        print("No scenario files found in scenarios/ or tests/scenarios/")
        sys.exit(1)

    print(f"\nRunning {len(scenario_files)} scenario files...\n")

    cards = []
    for filepath in scenario_files:
        print(f"  Running: {filepath.name}...", end=" ", flush=True)
        card = run_scenario_file(filepath)
        status = "PASS" if card.failed == 0 else "FAIL"
        print(status)
        cards.append(card)

    print_scoreboard(cards)

    # Exit with non-zero if any failures
    total_failed = sum(c.failed for c in cards)
    sys.exit(1 if total_failed > 0 else 0)


if __name__ == "__main__":
    main()
