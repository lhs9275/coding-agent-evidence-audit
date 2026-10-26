"""Apply protocol §4.2's four pairwise compatibility constraints to frozen tuples.

This module uses only observable archive-member paths, ZIP entry timestamps, file
extensions, and directory coexistence. It does not add compatibility constraints,
establish provenance, reproduce results, or mutate the source verdicts.

Constraint 1 uses the latest non-directory ZIP member timestamp as a conservative
release timestamp. Missing or non-ZIP timestamps, and release/output members from
the same archive, are UNKNOWN. A file suffix alone cannot prove evaluator/output
compatibility; report.json and final_report.json are incompatible because they are
result products, while executable forms remain UNKNOWN without interface evidence.
A task universe recorded only as "paths" has no observable membership and makes
constraint 3 UNKNOWN. Same-run aggregation files establish coexistence only, not
that their rule computes the reported outcome. Composite bundles remain UNKNOWN
unless a constraint explicitly understands their members.

Protocol §3 prohibits selecting candidates because they reproduce or approach a
reported value. Consequently this module never opens result contents or consults
reported values; doing so would turn outcome agreement into invented provenance.

이 분석은 결함 발견 후 수행된 사후 분석이다.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from itertools import islice, product
from pathlib import Path, PurePosixPath
from typing import Any, Literal

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs" / "paper-a"
PROTOCOL = DOCS / "joint-identifiability-protocol-v2.md"
VERDICTS = DOCS / "identifiability-verdicts-v2.json"
OUTPUT = DOCS / "compatibility-filter-v2.json"
BYTES_DIR = REPO.parent / "avail-bytes"

_SPEC = importlib.util.spec_from_file_location(
    "joint_identifiability_for_compatibility", REPO / "tools" / "joint_identifiability.py"
)
ji = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = ji
_SPEC.loader.exec_module(ji)

COMPONENTS = (
    "release_set",
    "run_output_set",
    "evaluator_and_configuration",
    "task_universe",
    "aggregation_rule",
)
CLOSURE_GROUNDS = {
    "AUTHORITATIVE_MANIFEST",
    "IMMUTABLE_INDEX",
    "EXHAUSTIVE_RETRIEVED_CLOSURE",
}
EXPECTED_DECISIONS = {
    "CMP-001", "CMP-002", "CMP-003", "CMP-004", "CMP-006", "CMP-007",
    "CMP-008", "CMP-009", "CMP-010", "CMP-011", "CMP-012", "CMP-013",
    "CMP-018", "CMP-019", "CMP-021", "CMP-022", "CMP-024", "CMP-034",
    "CMP-035", "CMP-041",
}

Status = Literal["ADMISSIBLE", "INCOMPATIBLE", "UNKNOWN"]
RuleStatus = Literal["PASS", "FAIL", "UNKNOWN"]
ZipMtime = tuple[int, int, int, int, int, int]
Tuple5 = tuple[str, str, str, str, str]
RuleResult = tuple[RuleStatus, str | None]

ADMISSIBLE: Status = "ADMISSIBLE"
INCOMPATIBLE: Status = "INCOMPATIBLE"
UNKNOWN: Status = "UNKNOWN"


@dataclass(frozen=True)
class CompatibilityContext:
    release_artifacts: Mapping[str, str]
    release_mtimes: Mapping[str, ZipMtime]
    entry_mtimes: Mapping[str, ZipMtime]


def _split_locator(candidate: str) -> tuple[str, str] | None:
    if " + " in candidate or " || " in candidate:
        return None
    artifact, separator, member = candidate.partition(":")
    if not separator or not artifact or not member:
        return None
    return artifact, member.lstrip("/")


def _format_mtime(value: ZipMtime) -> str:
    year, month, day, hour, minute, second = value
    return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}"


def _constraint_1(
    release: str,
    run_output: str,
    context: CompatibilityContext,
) -> RuleResult:
    output_ref = _split_locator(run_output)
    release_artifact = context.release_artifacts.get(release)

    if output_ref is None or release_artifact is None:
        return (
            "UNKNOWN",
            f"constraint 1 UNKNOWN: no observable release/output archive mapping for "
            f"{release!r} and {run_output!r}",
        )

    output_artifact, _ = output_ref
    if release_artifact == output_artifact:
        return (
            "UNKNOWN",
            f"constraint 1 UNKNOWN: release {release!r} and output {run_output!r} "
            f"occur in the same archive {output_artifact!r}",
        )

    release_mtime = context.release_mtimes.get(release)
    output_mtime = context.entry_mtimes.get(run_output)
    if release_mtime is None or output_mtime is None:
        missing = []
        if release_mtime is None:
            missing.append(f"release {release!r}")
        if output_mtime is None:
            missing.append(f"output {run_output!r}")
        return (
            "UNKNOWN",
            f"constraint 1 UNKNOWN: ZIP entry mtime unavailable for {' and '.join(missing)}",
        )

    if output_mtime > release_mtime:
        return "PASS", None

    return (
        "FAIL",
        f"constraint 1: output {run_output!r} mtime {_format_mtime(output_mtime)} "
        f"does not postdate release {release!r} mtime {_format_mtime(release_mtime)}",
    )


def _constraint_2(run_output: str, evaluator: str) -> RuleResult:
    output_ref = _split_locator(run_output)
    evaluator_ref = _split_locator(evaluator)
    if output_ref is None or evaluator_ref is None:
        return (
            "UNKNOWN",
            f"constraint 2 UNKNOWN: output/evaluator format is not observable from "
            f"{run_output!r} and {evaluator!r}",
        )

    output_suffix = PurePosixPath(output_ref[1]).suffix.lower() or "<no extension>"
    evaluator_path = PurePosixPath(evaluator_ref[1])
    if evaluator_path.name.lower() in {"report.json", "final_report.json"}:
        return (
            "FAIL",
            f"constraint 2: evaluator candidate {evaluator!r} is a non-executable "
            f"result product and cannot establish a reader for {output_suffix}",
        )

    return (
        "UNKNOWN",
        f"constraint 2 UNKNOWN: extension {evaluator_path.suffix.lower() or '<none>'} "
        f"does not establish whether {evaluator!r} reads {output_suffix}",
    )


def _constraint_3(run_output: str, task_universe: str) -> RuleResult:
    universe_ref = _split_locator(task_universe)
    if universe_ref is not None and universe_ref[1].strip("/") == "paths":
        return (
            "UNKNOWN",
            f"constraint 3 UNKNOWN: task universe {task_universe!r} records only "
            f"'paths', not enumerable membership for output {run_output!r}",
        )

    return (
        "UNKNOWN",
        f"constraint 3 UNKNOWN: no observable task membership proves that "
        f"{task_universe!r} is a subset of the run covered by {run_output!r}",
    )


def _constraint_4(run_output: str, aggregation_rule: str) -> RuleResult:
    output_ref = _split_locator(run_output)
    aggregation_ref = _split_locator(aggregation_rule)
    if output_ref is None or aggregation_ref is None:
        return (
            "UNKNOWN",
            f"constraint 4 UNKNOWN: run/aggregation directories are not observable "
            f"from {run_output!r} and {aggregation_rule!r}",
        )
    return (
        "UNKNOWN",
        f"constraint 4 UNKNOWN: paths do not prove whether {aggregation_rule!r}"
        f" computes the outcome in {run_output!r}",
    )


def admissible(
    tuple5: Tuple5,
    context: CompatibilityContext,
) -> tuple[Status, str | None]:
    """Return the three-valued conjunction of exactly constraints 1 through 4."""
    if len(tuple5) != 5:
        raise ValueError("tuple5 must contain exactly five components")

    release, run_output, evaluator, task_universe, aggregation_rule = tuple5
    results = (
        _constraint_1(release, run_output, context),
        _constraint_2(run_output, evaluator),
        _constraint_3(run_output, task_universe),
        _constraint_4(run_output, aggregation_rule),
    )

    failures = [reason for state, reason in results if state == "FAIL" and reason]
    if failures:
        return INCOMPATIBLE, "; ".join(failures)

    unknowns = [reason for state, reason in results if state == "UNKNOWN" and reason]
    if unknowns:
        return UNKNOWN, "; ".join(unknowns)

    return ADMISSIBLE, None


def _release_label(artifact: str) -> str:
    name = PurePosixPath(artifact).name
    return name.removeprefix("AMEND-").removesuffix(".bin")


def _zip_metadata(
    path: Path,
    wanted_members: set[str],
) -> tuple[dict[str, ZipMtime], ZipMtime | None]:
    try:
        if not path.is_file() or not zipfile.is_zipfile(path):
            return {}, None
        with zipfile.ZipFile(path) as archive:
            found: dict[str, ZipMtime] = {}
            latest: ZipMtime | None = None
            for info in archive.infolist():
                if info.is_dir():
                    continue
                mtime: ZipMtime = info.date_time
                if latest is None or mtime > latest:
                    latest = mtime
                if info.filename in wanted_members:
                    found[info.filename] = mtime
            return found, latest
    except (OSError, zipfile.BadZipFile):
        return {}, None


def _candidate_sets(verdict: Mapping[str, Any]) -> tuple[tuple[str, ...], ...]:
    decision_id = verdict.get("decision_id", "<unknown>")
    components = verdict.get("components")
    if not isinstance(components, Mapping):
        raise ValueError(f"{decision_id}: components must be an object")

    sets = []
    for component_name in COMPONENTS:
        component = components.get(component_name)
        if not isinstance(component, Mapping):
            raise ValueError(f"{decision_id}: missing component {component_name}")
        candidates = component.get("candidates")
        if not isinstance(candidates, list) or not all(
            isinstance(candidate, str) for candidate in candidates
        ):
            raise ValueError(f"{decision_id}: {component_name}.candidates must be strings")
        if not candidates:
            raise ValueError(
                f"{decision_id}: COMPATIBILITY_NOT_EVALUATED requires candidates "
                f"for {component_name}"
            )
        sets.append(tuple(candidates))
    return tuple(sets)


def _build_context(
    verdict: Mapping[str, Any],
    candidate_sets: tuple[tuple[str, ...], ...],
    bytes_dir: Path,
) -> CompatibilityContext:
    serving_value = verdict.get("serving_artifacts")
    serving_artifacts = (
        {value for value in serving_value if isinstance(value, str)}
        if isinstance(serving_value, list)
        else set()
    )

    release_artifacts: dict[str, str] = {}
    for release in candidate_sets[0]:
        matches = sorted(
            artifact
            for artifact in serving_artifacts
            if _release_label(artifact) == release
        )
        if len(matches) == 1:
            release_artifacts[release] = matches[0]

    wanted_by_artifact: dict[str, set[str]] = {}
    for run_output in candidate_sets[1]:
        output_ref = _split_locator(run_output)
        if output_ref is not None:
            artifact, member = output_ref
            wanted_by_artifact.setdefault(artifact, set()).add(member)

    entry_mtimes: dict[str, ZipMtime] = {}
    release_mtimes: dict[str, ZipMtime] = {}
    artifacts = set(wanted_by_artifact) | set(release_artifacts.values())

    for artifact in artifacts:
        if PurePosixPath(artifact).name != artifact:
            continue
        found, latest = _zip_metadata(
            bytes_dir / artifact,
            wanted_by_artifact.get(artifact, set()),
        )
        entry_mtimes.update(
            {f"{artifact}:{member}": mtime for member, mtime in found.items()}
        )
        if latest is not None:
            for release, release_artifact in release_artifacts.items():
                if release_artifact == artifact:
                    release_mtimes[release] = latest

    return CompatibilityContext(
        release_artifacts=release_artifacts,
        release_mtimes=release_mtimes,
        entry_mtimes=entry_mtimes,
    )


def _resulting_state(
    counts: Mapping[Status, int],
    evaluation_complete: bool,
    closure: object,
) -> str:
    if not evaluation_complete or counts[UNKNOWN]:
        return "COMPATIBILITY_NOT_EVALUATED"
    if counts[ADMISSIBLE] == 0:
        return "NO_ADMISSIBLE_TUPLE"
    if counts[ADMISSIBLE] > 1:
        return "AMBIGUOUS"
    if closure in CLOSURE_GROUNDS:
        return "IDENTIFIED"
    return "OPEN_UNIVERSE_SINGLETON"


def _evaluate_decision(
    verdict: Mapping[str, Any],
    bytes_dir: Path,
    combination_limit: int,
) -> dict[str, Any]:
    candidate_sets = _candidate_sets(verdict)
    candidate_counts = {
        name: len(candidates)
        for name, candidates in zip(COMPONENTS, candidate_sets, strict=True)
    }
    total_combinations = math.prod(candidate_counts.values())
    evaluated_target = min(total_combinations, combination_limit)
    context = _build_context(verdict, candidate_sets, bytes_dir)

    counts: dict[Status, int] = {
        ADMISSIBLE: 0,
        INCOMPATIBLE: 0,
        UNKNOWN: 0,
    }
    for values in islice(product(*candidate_sets), evaluated_target):
        status, _ = admissible(values, context)
        counts[status] += 1

    evaluation_complete = evaluated_target == total_combinations
    return {
        "decision_id": verdict.get("decision_id"),
        "original_state": verdict.get("state"),
        "candidate_counts": candidate_counts,
        "candidate_combinations": total_combinations,
        "combination_limit": combination_limit,
        "limit_exceeded": not evaluation_complete,
        "combinations_evaluated": evaluated_target,
        "unevaluated_combinations": total_combinations - evaluated_target,
        "counts_complete": evaluation_complete,
        "counts_scope": (
            "ALL_COMBINATIONS"
            if evaluation_complete
            else "FIRST_LIMITED_CARTESIAN_COMBINATIONS"
        ),
        "counts": counts,
        "resulting_state": _resulting_state(
            counts,
            evaluation_complete,
            verdict.get("universe_closure"),
        ),
    }


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _self_check() -> None:
    output = "run.zip:repo/results/run-1/predictions.json"
    context = CompatibilityContext(
        release_artifacts={"R1": "release.zip"},
        release_mtimes={"R1": (2024, 1, 1, 0, 0, 0)},
        entry_mtimes={output: (2024, 1, 2, 0, 0, 0)},
    )
    tuple5: Tuple5 = (
        "R1",
        output,
        "run.zip:repo/evaluator.py",
        "run.zip:paths",
        "run.zip:repo/results/run-1/report.json",
    )
    status, reason = admissible(tuple5, context)
    assert status == UNKNOWN and reason and "constraint 3 UNKNOWN" in reason

    report_tuple: Tuple5 = (
        tuple5[0],
        tuple5[1],
        "run.zip:repo/results/run-1/final_report.json",
        tuple5[3],
        tuple5[4],
    )
    status, reason = admissible(report_tuple, context)
    assert status == INCOMPATIBLE and reason and "constraint 2:" in reason


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verdicts", type=Path, default=VERDICTS)
    parser.add_argument("--bytes-dir", type=Path, default=BYTES_DIR)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    parser.add_argument("--max-combinations", type=_positive_int, default=200_000)
    args = parser.parse_args(argv)

    payload = json.loads(args.verdicts.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("verdicts"), list):
        raise ValueError("verdicts JSON must contain a verdicts array")

    live_protocol_sha256 = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    if payload.get("protocol_sha256") != live_protocol_sha256:
        raise ValueError(
            "protocol digest mismatch: refusing to apply the filter to a different protocol"
        )
    decision_ids = [verdict.get("decision_id") for verdict in payload["verdicts"]
                    if isinstance(verdict, dict)]
    if (len(decision_ids) != 20 or len(set(decision_ids)) != 20
            or set(decision_ids) != EXPECTED_DECISIONS):
        raise ValueError("compatibility input must contain each exact audited decision once")
    for verdict in payload["verdicts"]:
        ji.check(verdict)

    targets = [
        verdict
        for verdict in payload["verdicts"]
        if isinstance(verdict, dict)
        and verdict.get("state") == "COMPATIBILITY_NOT_EVALUATED"
    ]
    decisions = [
        _evaluate_decision(verdict, args.bytes_dir, args.max_combinations)
        for verdict in targets
    ]

    result = {
        "schema": "compatibility-filter.v2",
        "protocol_sha256": live_protocol_sha256,
        "source_verdicts": args.verdicts.name,
        "verdicts_sha256": hashlib.sha256(args.verdicts.read_bytes()).hexdigest(),
        "analysis_timing": "POST_HOC_AFTER_DEFECT_DISCOVERY",
        "reported_values_consulted": False,
        "constraint_numbers": [1, 2, 3, 4],
        "combination_limit": args.max_combinations,
        "decisions": decisions,
    }
    args.out.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    _self_check()
    raise SystemExit(main())
