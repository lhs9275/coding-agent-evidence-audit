# Joint-identifiability adjudication protocol, v1

**Status: FROZEN BEFORE THE LEDGER WAS RE-OPENED.** This document fixes how a published
comparison decision is judged identifiable, and it is written before re-reading the frozen
item ledger under the new criterion. The digest of this file is recorded in
`evidence-register.md` before any verdict is produced under it. Nothing here may be revised
in response to what a particular comparison turns out to look like; revisions follow §7.

## 0. Why this exists, and what it replaces

The audit's earlier criterion asked, per required kind, whether a locator existed and whether
its closure was retrieved. That is a **component-wise availability** test. It is not the
property the paper claims to measure.

The property is **joint identifiability**: whether an independent reproducer can determine
*which* computational object produced a reported number, without using the reported number to
choose among candidates. Component-wise availability does not imply it — every component can
be individually available while the combination that produced the value remains one of many.
Conversely a component can lack a prose description and still be pinned by an immutable
digest.

A second defect this protocol closes: the cohort-level binding grades were formed from prose
statements ("the README says its table is the paper's figure"). A prose statement is neither
necessary nor sufficient. It is not necessary because a manifest with immutable digests, a
release tag and a run index can determine the tuple with no sentence at all. It is not
sufficient because a sentence naming a release leaves the number unbound while the run-output
set, evaluator configuration, task universe or aggregation rule stays ambiguous.

## 1. Unit of adjudication

One verdict per **published comparison decision** — the same 20 decisions the frozen
required-item vector enumerates, nested within four studies. Study-level statements are
derived from decision-level verdicts by the aggregation rule in §5, never by re-judging at
study level.

## 2. The tuple

For a decision *d*, the tuple is

    T(d) = (release_set, run_output_set, evaluator_and_configuration, task_universe, aggregation_rule)

- **release_set** — the code state(s) the run executed: commit, tag, release asset, or image
  digest. A branch name is not a release_set unless the record pins it to an immutable
  revision.
- **run_output_set** — the specific per-task outputs whose values enter the reported number:
  predictions, patches, trajectories, evaluation logs.
- **evaluator_and_configuration** — the scoring program and the settings under which it ran,
  including its own version. Two evaluators that score the same patches differently are two
  different values of this component.
- **task_universe** — the exact set of task instances the number is computed over, including
  the denominator and any exclusions.
- **aggregation_rule** — how per-task outcomes become the reported figure: the statistic, the
  denominator convention, and the treatment of missing or errored tasks.

Evidence for a component may be any of: prose in the paper or deposit, a manifest, a lock or
config file, an immutable digest, a release asset listing, a run index, or a script whose
inputs are pinned. The form is irrelevant; what matters is whether it determines the value.

## 3. Prohibited inference

**A candidate may never be selected because it reproduces, or comes closest to, the reported
number.** Choosing the release whose score matches the paper is reverse-inference from the
result, not provenance. Any adjudication that would need this step records the decision as
`AMBIGUOUS` and lists the candidates it could not separate.

This prohibition is the reason the audit's own recomputation results are **not** admissible
as evidence for a verdict: knowing that one archive reproduces a figure exactly cannot make
that archive the identified `run_output_set`.

## 4. State space

Exactly one of five states per decision.

| state | condition |
| --- | --- |
| `IDENTIFIED` | Exactly one admissible tuple, **and** the candidate universe is closed (§4.1). |
| `OPEN_UNIVERSE_SINGLETON` | Exactly one admissible tuple among the observable candidates, but the universe is not closed. Conclusions are limited to "unique within the frozen observable candidate universe". |
| `AMBIGUOUS` | Two or more admissible tuples. Record the count and the range of reported-figure values they imply. |
| `NO_ADMISSIBLE_TUPLE` | Every component has an enumerable candidate set, but applying the compatibility constraints of §4.2 leaves no jointly admissible combination. Requires a diagnosis (§4.3). |
| `UNIDENTIFIED` | At least one component has no enumerable candidate set. |
| `COMPATIBILITY_NOT_EVALUATED` | Every component has candidates, but §4.2's pairwise filter was not applied, so the number of jointly admissible tuples is unknown. Added in the v3 revision (§7); see below. |

**State added in revision v3 (2026-08-13).** The first adjudicator computed the Cartesian
product of the candidate sets and never applied §4.2, then reported the product as
`admissible_tuples` and any value above one as `AMBIGUOUS`. That is wrong in a way that
flatters the finding: without the filter the admissible count could be zero
(`NO_ADMISSIBLE_TUPLE`), one (`IDENTIFIED`), or more than one (`AMBIGUOUS`), so a decision
whose components all have candidates but whose compatibility was never evaluated is not
entitled to any of those three labels. Such decisions take `COMPATIBILITY_NOT_EVALUATED` and
are reported separately, never folded into an identifiability count. Under §7 the revision
carries a new digest, preserves the v2 verdicts, is re-applied to all 20 decisions, and ships
the state transition below.

`NO_ADMISSIBLE_TUPLE` is kept apart from `UNIDENTIFIED` on purpose: the first says the public
evidence is mutually inconsistent, the second says it is insufficient, and the two have
different implications for the study and for the reader.

### 4.1 Candidate-universe closure

Enumerating the candidates one can see is not the same as knowing there are no others.
`IDENTIFIED` therefore requires one of the following, fixed here and not extended later:

1. an authoritative manifest in the deposit that enumerates the artifacts of the run, or
2. an immutable index — a release with fixed asset digests, or a commit-pinned directory
   listing — covering the component, or
3. a closure the audit retrieved in full, where the deposit's own structure makes the
   enumeration exhaustive (for example a single archive that contains the whole run set).

Absent all three, a single observable candidate yields `OPEN_UNIVERSE_SINGLETON`, never
`IDENTIFIED`.

### 4.2 Compatibility constraints

A tuple is admissible only if its components can have coexisted: the run outputs postdate the
release, the evaluator version can read the output format, the task universe is a subset of
what the run covers, and the aggregation rule is computable from the outputs present. These
four constraints are the whole list; adding a fifth later is a revision under §7.

### 4.3 Diagnosis for `NO_ADMISSIBLE_TUPLE`

Record one or more of: `EVIDENCE_CONTRADICTS` (the public record is internally inconsistent),
`CANDIDATE_UNIVERSE_MISSPECIFIED` (our enumeration was wrong), `COMPATIBILITY_RULE_MISSPECIFIED`
(§4.2 excluded a combination it should have admitted), or `UNRESOLVED`. Multiple causes are
allowed; forcing a single cause is not.

## 5. Aggregation to study level

Declared here, before any verdict: a study is reported as *identified* only if **every** one
of its audited decisions is `IDENTIFIED`. Any other combination is reported by listing the
decision-level states. No proportion over decisions is reported as a study-level property,
because decisions within a study are not independent.

## 6. Crosswalk from the existing ledger

The frozen ledger records, per item, `required_kinds`, each kind's state,
`actual_artifact_locator_exists`, `locator_attempted`, `complete_closure_retrieved`,
`recorded_immutable_digest`, `computed_digest`, `digest_algorithm_matches`,
`digest_scope_matches`, and `nonpublic_evidence`.

**Mapping revision, v1 → v2 (2026-08-13).** The v1 table named four kinds, because it was
written from the single ledger cell the orchestrator had seen (§8). The ledger uses fifteen.
The mapping below replaces it under §7: the reason is an incomplete input inventory, not a
verdict that came out inconveniently, and no verdict had been produced under v1, so there is
nothing to preserve and no transition table to publish. The v1 mapping is superseded and is
recorded in the register as such.

The crosswalk maps ledger kinds onto §2's components and marks, per component, whether the
ledger determines it, partly determines it, or does not reach it. The mapping is declared here
and is not adjusted per decision:

| component | ledger kinds and fields consulted | declared coverage |
| --- | --- | --- |
| release_set | `ENVIRONMENT_IDENTITY`, `recorded_immutable_digest`, `computed_digest`, `digest_algorithm_matches`, `digest_scope_matches` | partial |
| run_output_set | `EXPECTED_RUN_AUTHORITY`, `REPETITION_SET`, `PATCH_ARTIFACT`, `complete_closure_retrieved` | partial |
| evaluator_and_configuration | `EVALUATOR_OUTCOME`, `SEED` | partial |
| task_universe | `TASK_MEMBERSHIP`, `SELECTION_CANDIDATES`, `TERMINAL_MISSINGNESS` | partial |
| aggregation_rule | `ANALYSIS_BINDING`, `PPM_PROTOCOL`, `UNCERTAINTY`, `PAIRING_BRIDGE`, `HUMAN_LABEL` | partial |

`RESOURCE_CLOCK` maps to no component: cost and wall-clock records do not determine which
object produced a reported number. It is listed here so that the inventory is exhaustive
rather than silently truncated.

A component is `DETERMINED` for a decision only if **every** mapped kind required by that
decision is `AVAILABLE`; `PARTIAL` if at least one is `AVAILABLE` and at least one is not;
`NOT_REACHED` if none is, or if the decision requires none of the mapped kinds — the last case
is recorded separately as `NOT_REQUIRED_BY_LEDGER`, because a component the ledger never asked
about is not a component it answered.

Where the crosswalk shows a component the ledger does not reach, that component is filled by
re-reading the retrieved artifacts for that decision — not by re-running anything, and not by
consulting the recomputation results (§3).

**The crosswalk is an input-coverage table. It is not a proof that the two criteria agree.**
The verdict under this protocol is produced from the components, not inherited from the
earlier kind states.

## 7. Revision governance

If §4.2 or the candidate universe turns out to be misspecified, the rule may be revised, but:

1. the revision gets a new version number and a new digest, recorded in the register with the
   reason;
2. all verdicts produced under the previous version are preserved, not overwritten;
3. the revised rule is re-applied to **all 20** decisions, never to the decision that
   prompted it;
4. a transition table old-state → new-state is published for every decision.

Revising the rule for the case that provoked it is outcome-adaptive adjudication and is
forbidden.

## 8. Prior exposure, disclosed

Before this protocol was written, the orchestrator had read one ledger cell (`CMP-001`,
`PCOMP-001`) while fact-checking a review, and so had seen that its `ANALYSIS_BINDING` state
is `ABSENT_NO_LOCATOR` and that `TASK_MEMBERSHIP` and `PPM_PROTOCOL` were `AVAILABLE`. No
other cell was read, and no recomputation result was consulted while drafting. This exposure
is recorded because a rule written after seeing outcomes is weaker than one written before,
and the reader should be able to discount §4 accordingly.

## 9. What this protocol does not do

It does not decide whether a study is sound, whether its conclusion holds, or whether the
number would reproduce. It decides one thing: whether the object that produced a published
number can be determined from what was published, without looking at the number to choose.
