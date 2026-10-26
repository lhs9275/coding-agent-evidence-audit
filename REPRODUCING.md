# Reproducing the bounded release

## Integrity

Run from the repository root:

```bash
sha256sum -c SHA256SUMS
```

`SOURCE_MANIFEST.json` binds original exported files to the archived source commit. It does not establish the truth of an adjudication or the identity of an upstream historical execution.

## Offline audit

The following commands need Python 3.11+ and no third-party runtime packages:

```bash
python3 tools/joint_identifiability.py --verdicts docs/paper-a/identifiability-verdicts-v2.json
mkdir -p .verification
python3 tools/sensitivity_ladder.py --out .verification/sensitivity-ladder.json
python3 tools/crosswalk_ledger.py --out .verification/identifiability-crosswalk.json
```

The first command checks the saved protocol digest, refuses impermissible verdicts, and prints decision and study-level states. The other commands recompute a post-hoc relaxation ladder and an evidence-input crosswalk. The crosswalk is not itself an identification verdict.

Compare generated JSON structurally with the corresponding `*-v1.json` records. Full-file equality and any differing top-level keys are recorded separately in `verification/summary.json`. A historical protocol-hash mismatch, if present, is retained and disclosed rather than silently rewriting the archived record. Substantive data differences block release.

## Regression tests

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install 'pytest>=9,<10'
python3 -m pytest -q tests
```

The focused tests include positive controls and checks that invalid conclusions are refused. They do not establish independent human validation, causal attribution, or reproducibility of the complete agent experiment.

## Full historical reproduction

Not provided by this bounded package. Downloaded source publications, external program snapshots, large run archives, and the broader execution platform are excluded. The archived records retain locators and identity information where recorded. Availability and upstream permissions must be checked again before acquiring those materials. The technical report distinguishes reported historical observations from the release checks performed here.

## Rendering the technical report

`TECHNICAL_REPORT.ko.md` is the editable source. The PDF and HTML were generated with Python Markdown and WeasyPrint using system Noto CJK fonts. The release records the actual package versions in `verification/render-environment.txt`. The original English `paper/` files are archival source, not the source of the new Korean technical-report PDF.
