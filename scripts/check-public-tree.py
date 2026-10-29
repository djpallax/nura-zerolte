#!/usr/bin/env python3
"""Narrow public-tree privacy preflight. Prints paths/reasons, never secret values."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
patterns = {
    'private-key header': rb'-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----',
    'password database entry': rb'(?m)^(?:root|mobile):[^:\n]+:[0-9]+:',
    'Wi-Fi credential assignment': rb'(?im)^\s*(?:psk|password|sae_password)\s*=\s*[^\s#]',
    'personal home path': rb'/home/[a-zA-Z0-9_.-]+/',
}
forbidden = {'out', 'evidence', 'private', 'build', 'dist', 'deps', '.aws', '.codex', '.agents', '__pycache__'}
failures = []
count = 0
try:
    top = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', '--show-toplevel'], stderr=subprocess.DEVNULL, timeout=10).decode().strip()
    if Path(top).resolve() != ROOT:
        raise ValueError('Not a standalone source repository')
    names = subprocess.check_output(['git', '-C', str(ROOT), 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], timeout=30)
    paths = {ROOT / name.decode() for name in names.split(b'\0') if name}
except (subprocess.SubprocessError, ValueError):
    # Export preparation before git init; generated build outputs are not source.
    paths = {p for p in ROOT.rglob('*') if not any(n in {'.git', 'build', 'dist', 'deps', '__pycache__'} for n in p.relative_to(ROOT).parts)}
for path in sorted(paths):
    rel = path.relative_to(ROOT)
    if '.git' in rel.parts:
        continue
    if path.is_symlink():
        failures.append((rel, 'symlink requires review'))
        continue
    if any(part in forbidden for part in rel.parts):
        failures.append((rel, 'private/generated directory'))
        continue
    if not path.is_file():
        continue
    count += 1
    if path.suffix in {'.img', '.apk', '.zip', '.gz', '.pem', '.key', '.nmconnection', '.pyc'}:
        failures.append((rel, 'binary/archive or credential file'))
    if path.stat().st_size > 2 * 1024**2:
        failures.append((rel, 'file exceeds source-only limit'))
        continue
    data = path.read_bytes()
    if b'\0' in data:
        failures.append((rel, 'binary content requires review'))
    # Do not treat this scanner's pattern definitions as payloads.
    if path.resolve() == Path(__file__).resolve():
        continue
    for reason, pattern in patterns.items():
        if re.search(pattern, data):
            failures.append((rel, reason))
for rel, reason in failures:
    print(str(rel) + ': ' + reason)
print(f'Checked {count} files; findings={len(failures)}. Not a complete secret/license audit.')
sys.exit(bool(failures))
