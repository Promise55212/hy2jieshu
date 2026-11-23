#!/usr/bin/env python3
"""Static integrity only: never import or execute copied SOCKS5 modules."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_RAW = b'https://raw.githubusercontent.com/liucong552-art/jieshu/$S5_SOURCE_REF'
MIGRATED_RAW = b'https://raw.githubusercontent.com/Promise55212/jieshu/$S5_SOURCE_REF'
MIGRATED_FILES = {'socks5-install.sh', 'tests/test_socks5_access_audit.py'}


def main():
    data = json.loads((ROOT / 'tests/SOCKS5_UPSTREAM_MANIFEST.json').read_text(encoding='utf-8'))
    assert data['repository'] == 'https://github.com/liucong552-art/jieshu'
    assert re.fullmatch(r'[0-9a-f]{40}', data['commit'])
    files = {entry['path']: entry for entry in data['files']}
    assert set(files) == {'socks5.py', 'socks5-install.sh', 'socks5-traffic.py',
                          'socks5-audit.py', 'tests/test_socks5_access_audit.py'}
    for name, entry in files.items():
        body = (ROOT / name).read_bytes()
        if name in MIGRATED_FILES:
            # Compare the original bytes after undoing only the migration URL.
            assert body.count(MIGRATED_RAW) == 1, name
            body = body.replace(MIGRATED_RAW, UPSTREAM_RAW, 1)
        assert hashlib.sha256(body).hexdigest() == entry['sha256'], name
        blob = hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest()
        assert blob == entry['git_blob'], name
    installer = (ROOT / 'socks5-install.sh').read_text(encoding='utf-8')
    for key, name in [('core', 'socks5.py'), ('traffic', 'socks5-traffic.py'), ('audit', 'socks5-audit.py')]:
        pin = re.search(r'expected_' + key + r'="([0-9a-f]{64})"', installer)
        assert pin and pin[1] == files[name]['sha256'], name
    assert f'RAW="{MIGRATED_RAW.decode("ascii")}"' in installer
    assert 'SRC_DIR="$DIR"' in installer
    assert 'ca-certificates curl gnupg python3 nftables iproute2 util-linux coreutils procps' in installer
    assert '3proxy python3 nft ip ss timeout systemctl flock' in installer
    assert 'FC12214499FCC7BA1CFF6CDC0312384E3A73940B' in installer
    assert 'https://3proxy.org/repo/deb' in installer
    for name in ('hy2.sh', 'nat.sh', 'natjichang.sh', 'vpswg.sh'):
        assert not re.search(r'(?m)^\s*(?:bash|python3|exec).*socks5', (ROOT / name).read_text(encoding='utf-8')), name
    assert data['functional_tests_not_run'] == ['tests/test_socks5_access_audit.py']
    print(f'SOCKS5_STATIC_INTEGRITY=PASS files={len(files)} upstream={data["commit"]}')
    print('SOCKS5_FUNCTIONAL_TESTS=NOT_RUN; identical upstream acceptance reused')


if __name__ == '__main__':
    main()
