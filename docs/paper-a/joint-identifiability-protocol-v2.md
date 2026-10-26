# Joint-identifiability adjudication protocol, v2

**Status: POST-HOC REVISION AFTER CANDIDATE-UNIVERSE DEFECT DISCOVERY.** This revision
supersedes v1 for new adjudication. The v1 protocol and verdicts remain historical records.
The revision is applied to all 20 audited decisions and ships a decision-level transition
table; it is not applied only to the AutoCodeRover cases that exposed the defect.

## 1. Unit and tuple

One verdict is issued per published comparison decision:

    T(d) = (release_set, run_output_set, evaluator_and_configuration,
            task_universe, aggregation_rule)

- `release_set`: immutable or mutable code/release candidates the published record exposes.
- `run_output_set`: the complete outcome-bearing records whose values enter the reported
  number. This includes selected patches, machine-evaluator per-task outcomes, and human final
  labels where the estimand requires them; it is not limited to agent-generated files.
- `evaluator_and_configuration`: the scoring program or human procedure, including rubric,
  reviewer roles, cross-check/adjudication/tie procedure, version, and settings as applicable.
- `task_universe`: exact task identifiers, inclusion/exclusion rules, and denominator.
- `aggregation_rule`: selection, repetition, task-level OR/mean, missingness, denominator, and
  presentation transform that turn outcome records into the displayed figure.

Candidates are enumerated for the decision's actual outcome. A machine-resolution report is
not a human-semantic label, and a result product is not an evaluator program. A path-name regex
may inventory files but cannot assign their role in a decision.

Every one of the 20 decisions has an explicit outcome profile (resolution, conditional cost,
empty patch, stuck loop, patch-selection resolution, verifier-selected Best@k, or human
semantic task OR) and benchmark frame. There is no artifact-global fallback profile. Candidate
file inventories are complete or marked open/truncated; task-universe candidates are distinct
exact ID sets content-deduplicated by digest, not counts of filenames.
An absent run position remains missingness in `run_output_set`; it never shrinks the intended
task universe or turns a 300-task estimand into a 299-task alternative.

For direct `EMPTY_PATCH_RATE`, `STUCK_LOOP_RATE`, and `MEAN_API_COST` profiles, no external
scoring program is applicable: the evaluator coordinate is the single bound
`NOT_APPLICABLE:<profile>` value, while classification, denominator, missingness, and display
rules remain in `aggregation_rule`. Conditional cost is different because its denominator is
conditioned on machine resolution and therefore still requires that scoring procedure.

## 2. Outcome-specific evidence placement

| evidence | component |
| --- | --- |
| selected patch, machine outcome, human final label | `run_output_set` |
| scoring code/configuration or human rubric/review procedure | `evaluator_and_configuration` |
| task IDs, inclusion/exclusion, denominator membership | `task_universe` |
| selection, repetition, OR/mean, missingness, denominator, display/rounding | `aggregation_rule` |

For AutoCodeRover CMP-035, 78 is a unique-task union over tasks machine-plausible in any of
three runs. The numerator 51 is the number of those tasks with any semantically correct
selected final patch across the runs. The chain is `task × run → selected final patch →
machine plausible outcome → human semantic outcome → task-level OR`. Either source-bound
patch/outcome records through that chain, or a source-certified 78-task final-label vector
with the OR already applied, is sufficient for numeric recovery. Raw reviewer ballots are
required only to audit reviewer-process reliability.

## 3. Binding and prohibited inference

Direct binding is recorded independently from candidate presence:

- `BOUND`: direct source evidence selects the candidate without consulting the reported result.
- `MULTIPLE`: direct source evidence permits multiple candidates.
- `UNBOUND`: no direct source mapping selects a candidate before joint closure and compatibility.

These fields record direct mapping evidence, not the terminal joint verdict. Even with direct
binding `UNBOUND`, an exhaustively closed candidate universe plus complete compatibility can
determine one tuple without consulting the reported value; that effective joint determination
is recorded by `IDENTIFIED`. Without closure it remains `OPEN_UNIVERSE_SINGLETON`.

Rule evidence is `STATED`, `CITED_STANDARD`, `UNSTATED`, or `CONFLICTING`; reproduction is
`MATCH`, `MISMATCH`, or `NOT_TESTABLE`. `MISMATCH` is permitted only after run, evaluator,
membership, rule, and presentation transform are source-bound. Candidate-bundle arithmetic
before then is an observation, not a source contradiction.

A candidate may never be selected because it reproduces or approaches the reported number.
The audit's calculations cannot create provenance.

## 4. States and compatibility

Exactly one state is assigned:

| state | condition |
| --- | --- |
| `UNIDENTIFIED` | At least one required component has no outcome-correct enumerable candidate. |
| `COMPATIBILITY_NOT_EVALUATED` | All components have candidates, but at least one tuple is untested or remains `UNKNOWN`. |
| `NO_ADMISSIBLE_TUPLE` | Compatibility is complete, `UNKNOWN=0`, and no tuple is admissible; diagnosis required. |
| `OPEN_UNIVERSE_SINGLETON` | Compatibility is complete, exactly one tuple is admissible, and the candidate universe is open. |
| `IDENTIFIED` | Compatibility is complete, exactly one tuple is admissible, and closure is established. |
| `AMBIGUOUS` | Compatibility is complete and at least two tuples are admissible; record their actual value range. |

Closure grounds remain `AUTHORITATIVE_MANIFEST`, `IMMUTABLE_INDEX`, and
`EXHAUSTIVE_RETRIEVED_CLOSURE`. Compatibility uses the four v1 constraints: temporal
coexistence, evaluator/output compatibility, task-universe coverage, and computable
aggregation. Missing evidence yields `UNKNOWN`, never `INCOMPATIBLE` or `ADMISSIBLE`.

Tuple counts are null for `UNIDENTIFIED`: a missing component prevents a complete tuple from
existing, so zero enumerated combinations is not zero admissible tuples. When every component
is enumerable but compatibility has not run, admissible and unknown counts remain null and the
enumerated Cartesian product is recorded as unevaluated.

At condition-group and study levels, `IDENTIFIED` requires every audited decision in that
group to be `IDENTIFIED`; an unresolved compatibility state is not converted into a negative
verdict. The five condition groups nest in four studies; they are reported separately.

## 5. Source reconciliation for AutoCodeRover

The source reports three repetitions, Pass@1/Pass@3 with the cited standard, Lite @1
`19.00% (57)`, Lite @3 `26.00% (78)`, and ACR-sbfl `22.00% (66)`. These are source-reported
display/count values. The source does not bind them to public run IDs or evaluator versions,
and it does not state the count/percentage presentation transform for @1.

For the pinned public candidate bundle, the three baseline runs are 54, 57, 57 under the new
evaluator and 48, 47, 50 under the old evaluator. Applying the cited-standard k=1 mean gives
56/300 for the new bundle and 48⅓/300 for the old bundle; the new-evaluator union is 78/300.
These are bundle calculations, not source values or evidence of source error. Whole-percent
rounding followed by back-conversion is a possible but non-source-attested explanation, so
`presentation_transform` is `UNSPECIFIED_IN_SOURCE`.

For CMP-034, Table 2's source-displayed difference is `66−57=9`. Public candidate differences
are `{9,12}` under the new evaluator and `{11,13,14}` under the old evaluator, for range 9–14.
Those are raw per-run contrasts, not candidates for the complete three-repetition estimand.
The two complete public bundles pair all three baseline runs and the focal run within one
result family; their source-unbound arithmetic is 10 (new) and 38/3 (old). Direction is common
to these released observations; no source-to-public-artifact effect magnitude is identified.

## 6. Revision record and outputs

Every retrieved artifact is SHA-256-pinned regardless of size. Every derived candidate,
crosswalk, verdict, compatibility, sensitivity, and transition artifact records this file's
SHA-256 and its immediate input digests; protocol pins are checked before generation. The v1
files are not overwritten. The v2 transition table contains exactly the same 20 decision IDs
on both sides, records every old→new state, and gives machine-readable status and SHA-256
metadata for superseded legacy records and retained-input corrections.
