"""Check exported bytes and replay the bounded offline computations."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
out = root / 'verification'
out.mkdir(exist_ok=True)
manifest = json.loads((root / 'SOURCE_MANIFEST.json').read_text())
for row in manifest['files']:
    data = (root / row['path']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == row['sha256'], row['path']
commands = [
    ['tools/joint_identifiability.py', '--verdicts', 'docs/paper-a/identifiability-verdicts-v2.json'],
    ['tools/sensitivity_ladder.py', '--out', 'verification/sensitivity-ladder.json'],
    ['tools/crosswalk_ledger.py', '--out', 'verification/identifiability-crosswalk.json'],
]
receipts = []
for args in commands:
    result = subprocess.run([sys.executable, *args], cwd=root, text=True, capture_output=True)
    log = args[0].split('/')[-1].replace('.py', '.log')
    (out / log).write_text(result.stdout + result.stderr)
    receipts.append({'command': ['python3', *args], 'exit_code': result.returncode})
    if result.returncode:
        raise SystemExit(f'Offline check failed: {args[0]} (see verification/{log})')
comparisons = []
for generated, saved in [
    ('sensitivity-ladder.json', 'sensitivity-ladder-v2.json'),
    ('identifiability-crosswalk.json', 'identifiability-crosswalk-v2.json'),
]:
    actual = json.loads((out / generated).read_text())
    expected = json.loads((root / 'docs/paper-a' / saved).read_text())
    equal = actual == expected
    differing_keys = sorted(k for k in actual.keys() | expected.keys() if actual.get(k) != expected.get(k))
    comparisons.append({'generated': generated, 'saved': saved, 'json_equal': equal,
                        'differing_top_level_keys': differing_keys,
                        'substantive_payload_equal': not differing_keys or differing_keys == ['protocol_sha256'],
                        'generated_protocol_sha256': actual.get('protocol_sha256'),
                        'saved_protocol_sha256': expected.get('protocol_sha256')})
    if differing_keys and differing_keys != ['protocol_sha256']:
        raise SystemExit(f'JSON data differs: {generated}; inspect before release')
result = subprocess.run([sys.executable, '-m', 'pytest', '-q', 'tests', '-p', 'no:cacheprovider'], cwd=root, text=True, capture_output=True)
(out / 'pytest.log').write_text(result.stdout + result.stderr)
if result.returncode:
    raise SystemExit('Focused regression tests failed')
summary = {
    'source_commit': manifest['source_commit'], 'source_files_hash_verified': len(manifest['files']),
    'commands': receipts, 'recorded_json_comparisons': comparisons,
    'pytest_exit_code': result.returncode, 'pytest_summary': result.stdout.strip().splitlines()[-1],
    'scope': 'saved-record offline checks and focused regression tests; no agent execution, upstream reacquisition or independent scientific adjudication',
}
(out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
