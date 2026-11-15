"""Run generated cleanup with isolated files; never touch a real service/kernel."""
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def emitted(name):
    source = (ROOT / 'hy2.sh').read_text(encoding='utf-8')
    marker = 'cat >"${HY2_SBIN_DIR}/' + name + '" <<\'EOF\'\n'
    return source.split(marker, 1)[1].split('\nEOF\n', 1)[0]


class NodePortbwCleanupTests(unittest.TestCase):
    def run_cleanup(self, root, *, failure=False, policy=True, command=True, expired=False):
        port_dir = root / 'policies/ports'
        port_dir.mkdir(parents=True)
        if policy:
            (port_dir / '40020.json').write_text('{"port":40020}', encoding='utf-8')
        neighbor = port_dir / '40021.json'
        neighbor.write_text('other-node-policy', encoding='utf-8')
        (root / 'node.env').write_text(
            'TAG=hy2-temp-test\nPORT=40020\nLANDING=local\nEXPIRE_EPOCH=' +
            ('1' if expired else '9999999999') + '\n', encoding='utf-8')
        for name in ('node.yaml', 'node.service', 'node.url'):
            (root / name).write_text('test-node', encoding='utf-8')
        program = root / 'portbw'
        if command:
            program.write_bytes(b'''#!/usr/bin/env bash
printf '%s\\n' "$*" >>"$TEST_ROOT/calls"
[[ "$FAIL_PORTBW" == 0 ]] || exit 9
[[ "$1" == del && "$2" == 40020 ]] || exit 10
rm -f -- "$TEST_ROOT/policies/ports/$2.json"
''')
            program.chmod(0o755)
        script = emitted('hy2_cleanup_one.sh')
        script = re.sub(r'^source /usr/local/lib/hy2/.*$', '', script, flags=re.M)
        script = script.replace('/var/lib/portbw', (root / 'policies').as_posix())
        script = script.replace('/usr/local/sbin/portbw', program.as_posix())
        script = script.replace('/var/lib/hy2/manual-guard/state.json', (root / 'no-guard.json').as_posix())
        script = script.replace('/usr/local/sbin/hy2_temp_sub.sh', '/bin/true')
        mocks = '''
hy2_is_valid_temp_tag() { [[ "$1" == hy2-temp-test ]]; }
hy2_die() { exit 12; }
hy2_temp_meta_file() { echo "$TEST_ROOT/node.env"; }
hy2_temp_cfg_file() { echo "$TEST_ROOT/node.yaml"; }
hy2_temp_unit_file() { echo "$TEST_ROOT/node.service"; }
hy2_temp_url_file() { echo "$TEST_ROOT/node.url"; }
hy2_temp_port_from_any() { echo 40020; }
hy2_meta_get() { sed -n "s/^$2=//p" "$1" | head -n1; }
hy2_ensure_runtime_dirs() { :; }
hy2_pq_save_one() { :; }
hy2_quota_meta_file() { echo "$TEST_ROOT/quota.env"; }
hy2_pq_delete_managed_port() { :; }
hy2_il_delete_managed_port() { :; }
hy2_log() { :; }
systemctl() { [[ "$1" != is-active ]]; }
'''
        setup = ('TEST_ROOT=' + shlex.quote(root.as_posix()) + '\n'
                 'export TEST_ROOT\nHY2_LOCK_DIR="$TEST_ROOT"\n'
                 'HY2_TEMP_STATE_DIR="$TEST_ROOT"\nHY2_TEMP_LOCK_HELD=1\n'
                 'FORCE=' + ('0' if expired else '1') + '\n'
                 'export FAIL_PORTBW=' + ('1' if failure else '0') + '\n'
                 'set -- hy2-temp-test\n')
        result = subprocess.run(['bash'], input=setup + mocks + script,
                                capture_output=True, text=True, encoding='utf-8', timeout=15)
        self.assertEqual(neighbor.read_text(encoding='utf-8'), 'other-node-policy')
        return result

    def test_forced_and_natural_cleanup_remove_only_node_policy(self):
        for expired in (False, True):
            with self.subTest(expired=expired), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                result = self.run_cleanup(root, expired=expired)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((root / 'calls').read_text().splitlines(), ['del 40020'])
                self.assertFalse((root / 'policies/ports/40020.json').exists())
                self.assertFalse((root / 'node.env').exists())
                self.assertTrue((root / 'portbw').exists())

    def test_portbw_failure_keeps_node_metadata_and_policy_for_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_cleanup(root, failure=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertTrue((root / 'node.env').exists())
            self.assertTrue((root / 'policies/ports/40020.json').exists())

    def test_missing_portbw_command_keeps_metadata_if_policy_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_cleanup(root, command=False)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertTrue((root / 'node.env').exists())

    def test_optional_uninstalled_portbw_does_not_block_node_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_cleanup(root, command=False, policy=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((root / 'node.env').exists())
            self.assertFalse((root / 'calls').exists())

    def test_clear_all_reports_partial_failure_and_attempts_other_nodes(self):
        source = emitted('hy2_clear_all.sh')
        source = re.sub(r'^source /usr/local/lib/hy2/.*$', '', source, flags=re.M)
        source = source.replace('/usr/local/sbin/hy2_cleanup_one.sh', 'cleanup')
        mocks = '''
HY2_LOCK_DIR=/unused
hy2_ensure_runtime_dirs() { :; }
hy2_acquire_lock_fd() { :; }
hy2_collect_temp_tags() { printf 'hy2-temp-a\\nhy2-temp-b\\n'; }
cleanup() { echo "CLEAN:$1"; [[ "$1" != hy2-temp-a ]]; }
'''
        result = subprocess.run(['bash'], input=mocks + source,
                                capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('CLEAN:hy2-temp-a', result.stdout)
        self.assertIn('CLEAN:hy2-temp-b', result.stdout)
        self.assertNotIn('✅', result.stdout)


if __name__ == '__main__':
    unittest.main()
