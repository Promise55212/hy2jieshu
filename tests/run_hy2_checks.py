#!/usr/bin/env python3
"""Existing HY2 tests only; do not import the copied upstream SOCKS5 tests."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / 'tests/SOCKS5_UPSTREAM_MANIFEST.json').read_text(encoding='utf-8'))
excluded = set(manifest['functional_tests_not_run'])
assert excluded == {'tests/test_socks5_access_audit.py'}
suite = unittest.TestSuite()
for path in sorted((ROOT / 'tests').glob('test_*.py')):
    # Filter before discover, which imports the selected test module.
    if path.relative_to(ROOT).as_posix() in excluded:
        print(f'UPSTREAM_FUNCTIONAL_TEST_NOT_RUN={path.name}', flush=True)
        continue
    suite.addTests(unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern=path.name))
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
