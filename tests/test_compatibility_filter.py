"""Fixtures for the §4.2 compatibility filter, centred on the collapse it must not make.

The filter exists because the adjudicator multiplied candidate sets together and called the
product admissible. The danger in fixing that is the mirror-image error: treating everything
the filter cannot evaluate as eliminated, which would manufacture a clean answer out of
silence. Every check here has a partner that must come back UNKNOWN rather than INCOMPATIBLE.

    python -m pytest tests/test_compatibility_filter.py
"""

from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
_SPEC = importlib.util.spec_from_file_location("cf", REPO / "tools" / "compatibility_filter.py")
cf = importlib.util.module_from_spec(_SPEC)
sys.modules["cf"] = cf
_SPEC.loader.exec_module(cf)

A = "AMEND-ACR-REPO-TARBALL.bin:auto-code-rover-585d/results"
RUN1 = f"{A}/acr-run-1/predictions_for_swebench.json"
RUN2 = f"{A}/acr-run-2/predictions_for_swebench.json"
PY_EVAL = "AMEND-ACR-REPO-TARBALL.bin:auto-code-rover-585d/app/api/eval_helper.py"
REPORT = f"{A}/acr-run-1/new_eval_results/report.json"
DOC_RUN1 = f"{A}/acr-run-1/new_eval_results/README.md"
DOC_RUN2 = f"{A}/acr-run-2/new_eval_results/README.md"

# No archive timestamps: constraint 1 must go UNKNOWN rather than eliminate anything.
EMPTY_CONTEXT = cf.CompatibilityContext(release_artifacts={}, release_mtimes={}, entry_mtimes={})


def test_a_result_product_is_not_an_evaluator():
    status, reason = cf._constraint_2(RUN1, REPORT)
    assert status == "FAIL" and "result product" in reason


def test_a_python_suffix_alone_does_not_prove_format_compatibility():
    assert cf._constraint_2(RUN1, PY_EVAL)[0] == "UNKNOWN"


def test_an_unrecognised_evaluator_form_is_unknown_not_incompatible():
    other = "AMEND-ACR-REPO-TARBALL.bin:auto-code-rover-585d/app/run.sh"
    status, _ = cf._constraint_2(RUN1, other)
    assert status == "UNKNOWN", "an unreadable form is not a proven incompatibility"


def test_an_aggregation_document_from_another_run_is_unknown_without_rule_evidence():
    assert cf._constraint_4(RUN1, DOC_RUN2)[0] == "UNKNOWN"


def test_an_aggregation_document_from_the_same_run_is_not_eliminated():
    assert cf._constraint_4(RUN1, DOC_RUN1)[0] in ("PASS", "UNKNOWN")


def test_a_composite_run_bundle_is_not_misread_as_one_locator():
    bundle = f"{RUN1} + {RUN2}"
    assert cf._constraint_2(bundle, PY_EVAL)[0] == "UNKNOWN"
    assert cf._constraint_4(bundle, DOC_RUN1)[0] == "UNKNOWN"


def test_a_task_universe_known_only_by_path_is_unknown():
    status, reason = cf._constraint_3(RUN1, "AMEND-ACR-REPO-TARBALL.bin:paths")
    assert status == "UNKNOWN" and "paths" in reason


def test_a_tuple_whose_constraints_are_all_unknown_is_unknown():
    status, _ = cf.admissible(
        ("ACR-REPO-TARBALL", RUN1, "AMEND-ACR-REPO-TARBALL.bin:app/run.sh",
         "AMEND-ACR-REPO-TARBALL.bin:paths", DOC_RUN1),
        context=EMPTY_CONTEXT,
    )
    # Strictly UNKNOWN. Admitting it would let silence count as compatibility and inflate
    # the admissible tally, which is the mirror image of the defect this filter repairs.
    assert status == "UNKNOWN"


def test_one_failing_constraint_eliminates_the_tuple():
    status, reason = cf.admissible(
        ("ACR-REPO-TARBALL", RUN1, REPORT, "AMEND-ACR-REPO-TARBALL.bin:paths", DOC_RUN1),
        context=EMPTY_CONTEXT,
    )
    assert status == "INCOMPATIBLE" and "constraint 2" in reason


def test_the_filter_never_reads_a_reported_value():
    source = (REPO / "tools" / "compatibility_filter.py").read_text().lower()
    for forbidden in ("reported_value", "matches_reported", "closest", "recomputation"):
        assert f"{forbidden} =" not in source and f"{forbidden}(" not in source


def test_generator_refuses_a_protocol_invalid_verdict_payload(tmp_path):
    components = {name: {"candidates": ["c1"], "binding": "UNBOUND"}
                  for name in cf.COMPONENTS}
    payload = {"protocol_sha256": hashlib.sha256(cf.PROTOCOL.read_bytes()).hexdigest(),
               "verdicts": [
                   {"decision_id": decision, "state": "UNIDENTIFIED",
                    "components": components, "admissible_tuples": None,
                    "unknown_tuples": None, "unevaluated_tuples": None,
                    "compatibility_constraints_applied": False}
                   for decision in sorted(cf.EXPECTED_DECISIONS)
               ]}
    source, output = tmp_path / "invalid.json", tmp_path / "out.json"
    source.write_text(json.dumps(payload))

    with pytest.raises(Exception, match="UNIDENTIFIED requires"):
        cf.main(["--verdicts", str(source), "--out", str(output)])


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
