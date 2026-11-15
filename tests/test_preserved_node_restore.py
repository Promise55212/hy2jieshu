"""Execute generated keep-data recovery and GC with isolated filesystem/I/O."""
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def emitted(name):
    source = (ROOT / 'hy2.sh').read_text(encoding='utf-8')
    marker = 'cat >"${HY2_SBIN_DIR}/' + name + '" <<\'EOF\'\n'
    return source.split(marker, 1)[1].split('\nEOF\n', 1)[0]


class PreservedNodeRestoreTests(unittest.TestCase):
    def run_restore(self, root, *, failure='', boot=False, unsafe=False, second=False, preexisting=False):
        backups = root / 'backups'
        backups.mkdir()
        (backups / 'hy2-temp-test.service').write_text('old unit is a marker only', encoding='utf-8')
        (root / 'node.env').write_text(
            'TAG=hy2-temp-test\nEXPIRE_EPOCH=9999999999\nLANDING=local\n', encoding='utf-8')
        (root / 'node.yaml').write_text('mock retained config', encoding='utf-8')
        (root / 'guard-state.json').write_text('{}', encoding='utf-8')
        if second:
            (backups / 'hy2-temp-zfail.service').write_text('second marker', encoding='utf-8')
            (root / 'second.env').write_text(
                'TAG=hy2-temp-zfail\nEXPIRE_EPOCH=9999999999\nLANDING=local\n', encoding='utf-8')
            (root / 'second.yaml').write_text('second config', encoding='utf-8')
        if preexisting:
            (root / 'active-hy2-temp-test.service').touch()
        setup = 'TEST_ROOT=' + shlex.quote(root.as_posix()) + '\n'
        setup += 'FAILURE=' + shlex.quote(failure) + '\n'
        setup += 'BOOT=' + ('1' if boot else '0') + '\nUNSAFE=' + ('1' if unsafe else '0') + '\n'
        setup += '''
HY2_TEMP_LOCK_HELD=1
HY2_LOCK_DIR="$TEST_ROOT"
hy2_ensure_runtime_dirs() { :; }
hy2_is_valid_temp_tag() { [[ "$1" == hy2-temp-test || "$1" == hy2-temp-zfail ]]; }
hy2_temp_meta_file() { if [[ "$1" == hy2-temp-zfail ]]; then echo "$TEST_ROOT/second.env"; else echo "$TEST_ROOT/node.env"; fi; }
hy2_temp_cfg_file() { if [[ "$1" == hy2-temp-zfail ]]; then echo "$TEST_ROOT/second.yaml"; else echo "$TEST_ROOT/node.yaml"; fi; }
hy2_temp_unit_file() { echo "$TEST_ROOT/$1.service"; }
hy2_meta_get() { sed -n "s/^$2=//p" "$1" | head -n1; }
hy2_temp_unit_text() { echo canonical-unit; }
stat() {
  if [[ "$2" == %u ]]; then echo 0;
  elif [[ "$UNSAFE" == 1 ]]; then echo 777;
  else echo 600; fi
}
fake_gc() { echo gc >>"$TEST_ROOT/events"; [[ -f "$TEST_ROOT/hy2-temp-test.service" ]]; }
fake_pq() { echo pq >>"$TEST_ROOT/events"; [[ "$FAILURE" != pq ]]; }
fake_ip() { echo ip >>"$TEST_ROOT/events"; [[ "$FAILURE" != ip ]]; }
fake_guard() { echo guard >>"$TEST_ROOT/events"; [[ "$FAILURE" != guard ]]; }
timeout() { shift; "$@"; }
systemctl() {
  local unit="${@: -1}"
  echo "$*" >>"$TEST_ROOT/events"
  if [[ "$1" == show ]]; then
    if [[ "$BOOT" == 1 ]]; then echo activating; else echo inactive; fi
  elif [[ "$1" == start ]]; then
    [[ "$FAILURE" != start && !( "$FAILURE" == second && "$unit" == hy2-temp-zfail.service ) ]] || return 1
    touch "$TEST_ROOT/active-$unit"
  elif [[ "$1" == is-active ]]; then [[ -f "$TEST_ROOT/active-$unit" ]];
  elif [[ "$1" == stop ]]; then
    [[ -f "$TEST_ROOT/stoppost-preserve.${unit%.service}" ]] || return 12
    echo rollback-preserved >>"$TEST_ROOT/events"
    rm -f "$TEST_ROOT/active-$unit"
  else return 0; fi
}
'''
        body = emitted('hy2_restore_all.sh').replace('source /usr/local/lib/hy2/common.sh', ':')
        body = body.replace('/var/lib/hy2/uninstalled-units', backups.as_posix())
        body = body.replace('/var/lib/hy2/manual-guard/state.json', (root / 'guard-state.json').as_posix())
        # The executable test applies to this fixture's harmless guard script.
        guard = root / 'guard'
        guard.write_bytes(b'#!/usr/bin/env bash\nexit 0\n')
        guard.chmod(0o755)
        body = body.replace('[[ ! -x /usr/local/sbin/hy2-guard ]]', '[[ ! -x "' + guard.as_posix() + '" ]]')
        for old, new in [('/usr/local/sbin/hy2_gc.sh', 'fake_gc'),
                         ('/usr/local/sbin/pq_restore_all.sh', 'fake_pq'),
                         ('/usr/local/sbin/iplimit_restore_all.sh', 'fake_ip'),
                         ('/usr/local/sbin/hy2-guard', 'fake_guard')]:
            body = body.replace(old, new)
        result = subprocess.run(['bash'], input=setup + body, capture_output=True,
                                text=True, encoding='utf-8', timeout=15)
        events = root / 'events'
        return result, events.read_text(encoding='utf-8').splitlines() if events.exists() else []

    def test_rebuilds_unit_before_gc_and_restores_protection_before_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result, events = self.run_restore(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / 'hy2-temp-test.service').read_text().strip(), 'canonical-unit')
            self.assertEqual(events[:4], ['gc', 'pq', 'ip', 'guard'])
            self.assertLess(events.index('guard'), events.index('start hy2-temp-test.service'))
            self.assertFalse((root / 'backups/hy2-temp-test.service').exists())
            self.assertTrue((root / 'node.env').exists())

    def test_protection_or_start_failure_preserves_marker_and_metadata(self):
        for failure in ('pq', 'ip', 'guard', 'start'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                result, events = self.run_restore(root, failure=failure)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue((root / 'backups/hy2-temp-test.service').exists())
                self.assertTrue((root / 'node.env').exists())
                if failure != 'start':
                    self.assertNotIn('start hy2-temp-test.service', events)

    def test_later_start_failure_stops_only_new_listeners_and_keeps_all_markers(self):
        for preexisting in (False, True):
            with self.subTest(preexisting=preexisting), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                result, events = self.run_restore(root, failure='second', second=True,
                                                 preexisting=preexisting)
                self.assertNotEqual(result.returncode, 0)
                for tag in ('hy2-temp-test', 'hy2-temp-zfail'):
                    self.assertTrue((root / 'backups' / (tag + '.service')).exists())
                self.assertTrue((root / 'node.env').exists())
                self.assertTrue((root / 'second.env').exists())
                self.assertEqual((root / 'active-hy2-temp-test.service').exists(), preexisting)
                self.assertEqual('stop hy2-temp-test.service' in events, not preexisting)
                self.assertIn('rollback-preserved', events)

    def test_unsafe_backup_does_not_reach_gc_or_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result, events = self.run_restore(root, unsafe=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(events, [])
            self.assertTrue((root / 'node.env').exists())

    def test_boot_queues_start_without_waiting_on_own_restore_unit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result, events = self.run_restore(root, boot=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('start --no-block hy2-temp-test.service', events)
            self.assertTrue((root / 'backups/hy2-temp-test.service').exists())

    def test_gc_preserves_only_explicit_keep_backup_when_unit_is_missing(self):
        for preserve in (True, False):
            with self.subTest(preserve=preserve), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'node.env').write_text('EXPIRE_EPOCH=9999999999\n', encoding='utf-8')
                backups = root / 'backups'
                backups.mkdir()
                if preserve:
                    (backups / 'hy2-temp-test.service').write_text('retained', encoding='utf-8')
                setup = 'TEST_ROOT=' + shlex.quote(root.as_posix()) + '''
HY2_TEMP_LOCK_HELD=1
hy2_ensure_runtime_dirs() { :; }
hy2_collect_temp_tags() { echo hy2-temp-test; }
hy2_temp_meta_file() { echo "$TEST_ROOT/node.env"; }
hy2_temp_cfg_file() { echo "$TEST_ROOT/absent.yaml"; }
hy2_temp_unit_file() { echo "$TEST_ROOT/absent.service"; }
hy2_meta_get() { sed -n "s/^$2=//p" "$1" | head -n1; }
systemctl() { return 1; }
cleanup() { echo cleanup >"$TEST_ROOT/cleaned"; }
'''
                body = emitted('hy2_gc.sh').replace('source /usr/local/lib/hy2/common.sh', ':')
                body = body.replace('/var/lib/hy2/uninstalled-units', backups.as_posix())
                body = body.replace('/usr/local/sbin/hy2_cleanup_one.sh', 'cleanup')
                result = subprocess.run(['bash'], input=setup + body, capture_output=True,
                                        text=True, encoding='utf-8', timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((root / 'cleaned').exists(), not preserve)


if __name__ == '__main__':
    unittest.main()
