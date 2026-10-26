"""Map the frozen item ledger onto the five identifiability components, per decision.

This produces an input-coverage table and nothing else. It does not decide whether a decision
is identifiable: the ledger asked component-wise availability questions, and the protocol asks
a joint one, so what the ledger settles is an input to the verdict rather than the verdict.
Where the table says NOT_REACHED, the component has to be filled by re-reading that decision's
retrieved artifacts.

    python tools/crosswalk_ledger.py --out PATH
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs" / "paper-a"
PROTOCOL = DOCS / "joint-identifiability-protocol-v2.md"

# Declared in protocol §6 (mapping v2) and not adjusted per decision.
MAPPING = {
    "release_set": ("ENVIRONMENT_IDENTITY",),
    "run_output_set": ("EXPECTED_RUN_AUTHORITY", "REPETITION_SET", "PATCH_ARTIFACT",
                       "EVALUATOR_OUTCOME", "HUMAN_LABEL"),
    "evaluator_and_configuration": ("PPM_PROTOCOL", "SEED"),
    "task_universe": ("TASK_MEMBERSHIP", "SELECTION_CANDIDATES"),
    "aggregation_rule": ("ANALYSIS_BINDING", "REPETITION_SET", "TERMINAL_MISSINGNESS",
                         "PPM_PROTOCOL", "UNCERTAINTY", "PAIRING_BRIDGE"),
}
UNMAPPED = ("RESOURCE_CLOCK",)
AVAILABLE = "AVAILABLE"


def coverage(states: dict[str, str], kinds: tuple[str, ...]) -> str:
    """DETERMINED / PARTIAL / NOT_REACHED / NOT_REQUIRED_BY_LEDGER for one component."""
    seen = [states[k] for k in kinds if k in states]
    if not seen:
        # The ledger never asked about this component for this decision. That is not an
        # answer of "absent"; it is the absence of a question.
        return "NOT_REQUIRED_BY_LEDGER"
    if all(state == AVAILABLE for state in seen):
        return "DETERMINED"
    if any(state == AVAILABLE for state in seen):
        return "PARTIAL"
    return "NOT_REACHED"


def crosswalk(cell: dict) -> dict:
    states: dict[str, str] = {}
    digest_pinned = False
    for item in cell["items"]:
        for kind, state in item["kind_states"].items():
            # Worst state wins: one item leaving a kind unavailable leaves the decision's
            # component unsettled, whatever a sibling item recorded.
            if kind not in states or (states[kind] == AVAILABLE and state != AVAILABLE):
                states[kind] = state
        if item.get("recorded_immutable_digest") and item.get("digest_scope_matches"):
            digest_pinned = True

    components = {name: coverage(states, kinds) for name, kinds in MAPPING.items()}
    # A recorded immutable digest whose scope matches is release evidence in its own right,
    # so it can lift release_set out of NOT_REACHED but never to DETERMINED on its own.
    if digest_pinned and components["release_set"] in ("NOT_REACHED", "NOT_REQUIRED_BY_LEDGER"):
        components["release_set"] = "PARTIAL"

    return {
        "decision_id": cell["comparison_id"],
        "condition_group": cell.get("condition_group"),
        "items": len(cell["items"]),
        "kind_states": states,
        "immutable_digest_pinned": digest_pinned,
        "components": components,
        "needs_artifact_reread": sorted(name for name, c in components.items()
                                        if c != "DETERMINED"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--findings", type=Path, default=DOCS / "availability-item-findings-v1.json")
    parser.add_argument("--out", type=Path, default=DOCS / "identifiability-crosswalk-v2.json")
    args = parser.parse_args(argv)

    cells = json.loads(args.findings.read_text())["cells"]
    rows = [crosswalk(cell) for cell in cells]

    per_component = {name: Counter(row["components"][name] for row in rows) for name in MAPPING}
    for name, counts in per_component.items():
        print(f"  {name:30} {dict(counts)}")
    determined_all = sum(1 for row in rows if not row["needs_artifact_reread"])
    print(f"\n{determined_all} of {len(rows)} decisions have all five components determined by the ledger alone")

    args.out.write_text(json.dumps({
        "schema": "identifiability-crosswalk.v2",
        "scientific_claims": False,
        "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
        "findings_sha256": hashlib.sha256(args.findings.read_bytes()).hexdigest(),
        "mapping_version": "v3-outcome-specific",
        "reading_rule": (
            "Input coverage only. DETERMINED means every mapped kind the decision required was"
            " AVAILABLE in the ledger, not that the component is identified under the joint"
            " criterion. NOT_REQUIRED_BY_LEDGER means the ledger never asked, which is the"
            " absence of a question rather than an answer of absent. No verdict is implied by"
            " any row; verdicts are produced only under the frozen protocol, from components,"
            " and never inherited from these kind states."
        ),
        "unmapped_kinds": list(UNMAPPED),
        "counts": {name: dict(counts) for name, counts in per_component.items()},
        "decisions_fully_determined_by_ledger": determined_all,
        "rows": rows,
    }, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
