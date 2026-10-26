# Coding-Agent Evidence Audit

**Project alias: Paper A.**

An archival technical report and a bounded, offline-checkable research artifact for Paper A's audit of public evidence behind coding-agent comparisons.

- **[한국어 기술보고서](TECHNICAL_REPORT.ko.md)** · **[PDF](TECHNICAL_REPORT.ko.pdf)**
- [Reproduction instructions](REPRODUCING.md)
- [Data scope and rights](DATA_AND_RIGHTS.md)
- [Archived English manuscript source](paper/main.tex)
- [Source-file manifest](SOURCE_MANIFEST.json)

## What this release represents

This package is derived from the **25 August 2026 backup**, embedded repository commit `087391705a0d665e95a24711210cfee8c88e52b6`. It is an archival research release, not an accepted journal paper or a claim that later project revisions have been recovered. The technical report was prepared on 26 October 2026.

The original question concerned transferring evaluation protocols between coding-agent comparisons. The retained audit separately asks whether public records identify the release, outputs, evaluator/configuration, task universe, and aggregation rule behind a reported comparison. Availability, numerical agreement, historical identification, and protocol-transfer feasibility are distinct properties.

The current outcome-specific **v2** audit records 20 `UNIDENTIFIED` decisions across four source studies and five condition groups. The v1 verdict/protocol files are retained only to make the v1-to-v2 transition inspectable; they are superseded. Earlier transfer-attemptability conclusions were withdrawn, and the planned tier-two compatibility analysis was not run. The bounded audit includes four source studies and 20 comparison decisions. Decisions and their evidence requirements are nested within studies; these counts are not independent sample sizes. A separate discovery cohort is not an exhaustive census of the literature.

## Quick check

Python 3.11 or newer; the audit commands use the standard library.

```bash
python3 tools/joint_identifiability.py \
  --verdicts docs/paper-a/identifiability-verdicts-v2.json
mkdir -p .verification
python3 tools/sensitivity_ladder.py --out .verification/sensitivity-ladder.json
python3 tools/crosswalk_ledger.py --out .verification/identifiability-crosswalk.json
```

For the focused regression tests:

```bash
python3 -m pip install 'pytest>=9,<10'
python3 -m pytest -q tests
```

These checks exercise saved records and refusal rules. They do not rerun coding agents, independently adjudicate source publications, or reproduce every result in the archived manuscript. Compatibility analysis can require separately acquired upstream bytes; those bytes are not bundled.

## Contents

- `docs/paper-a/`: first-party structured audit records and selected method notes.
- `tools/`: the four focused audit programs.
- `tests/`: their retained regression tests.
- `paper/`: original manuscript source from the backup.
- `verification/`: release validation outputs, with scope stated in the report.

The private backup, its Git history, internal AI conversations, third-party full-text caches, and downloaded external programs are not included. Original exported source files retain their bytes; their hashes are in `SOURCE_MANIFEST.json`. `SHA256SUMS` covers distribution files.

No blanket reuse license is newly granted. See [DATA_AND_RIGHTS.md](DATA_AND_RIGHTS.md). AI assistance was used to prepare the archival documentation and run release checks; this is not independent peer review.
