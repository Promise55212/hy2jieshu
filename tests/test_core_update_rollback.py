"""Run actual generated rollback functions with isolated files and service I/O."""
import hashlib
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'hy2.sh').read_text(encoding='utf-8')
MAIN = SOURCE.split('cat >"/root/onekey_hy2_main_tls.sh" <<\'EOF\'\n', 1)[1].split('\nEOF\n', 1)[0]


def function(name, following):
    start = MAIN.index(name + '() {')
    return MAIN[start:MAIN.index('\n' + following, start)]


CORE = function('restore_core_update', '  abort_core_update() {')
ABORT = function('abort_core_update', '  if [[ -n "$local_binary" ]]')
OUTER = function('rollback_transaction', 'on_error() {')
ON_EXIT = function('on_exit', "trap 'on_error' ERR")


class CoreRollbackTests(unittest.TestCase):
    def execute(self, root, body):
        setup = 'TEST_ROOT=' + shlex.quote(root.as_posix()) + '''
set -Eeuo pipefail
trap 'echo UNEXPECTED_ERR >&2; exit 71' ERR
hy2_die() { echo "$*" >&2; exit 1; }
systemctl() { echo "$*" >>"$TEST_ROOT/systemctl.calls"; return 0; }
hy2_restart_verify_managed_unit() {
  echo "$1" >>"$TEST_ROOT/health.calls"
  [[ "${FAILURE:-}" != restart ]]
}
'''
        return subprocess.run(['bash'], input=setup + body, capture_output=True,
                              text=True, encoding='utf-8', timeout=15)

    def core_fixture(self, root, failure=''):
        backup = root / 'core-backup'
        backup.mkdir()
        old = b'#!/usr/bin/env bash\n[[ "$1" == version ]]\n'
        (backup / 'hysteria.old').write_bytes(old)
        (backup / 'hysteria.old').chmod(0o755)
        installed = root / 'hysteria'
        installed.write_bytes(b'candidate-core')
        installed.chmod(0o755)
        setup = 'FAILURE=' + shlex.quote(failure) + '''
old_present=1
old_bin_path="$TEST_ROOT/hysteria"
new_bin="$old_bin_path"
old_mode=755
core_tx="$TEST_ROOT/core-backup"
active_units=(hy2.service hy2-temp-test.service)
install() {
  [[ "$FAILURE" != install ]] || return 17
  [[ "$FAILURE" != silent_install ]] || return 0
  command install "$@"
}
'''
        return setup, backup, installed, old

    def test_core_success_checks_old_bytes_and_all_active_units_then_removes_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            setup, backup, installed, old = self.core_fixture(root)
            result = self.execute(root, setup + CORE + '\nrestore_core_update\n')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(installed.read_bytes(), old)
            self.assertFalse(backup.exists())
            self.assertEqual((root / 'health.calls').read_text().splitlines(),
                             ['hy2.service', 'hy2-temp-test.service'])

    def test_core_write_hash_or_service_failure_retains_backup_and_is_nonzero(self):
        for failure in ('install', 'silent_install', 'restart'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                setup, backup, _, _ = self.core_fixture(root, failure)
                result = self.execute(root, setup + CORE + '\nrestore_core_update\n')
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue((backup / 'hysteria.old').exists())
                self.assertIn('core-backup', result.stderr)
                self.assertNotIn('已恢复并验证', result.stderr)
                if failure != 'restart':
                    self.assertFalse((root / 'health.calls').exists())

    def test_abort_failure_message_never_claims_a_failed_rollback_succeeded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            setup, backup, _, _ = self.core_fixture(root, 'install')
            result = self.execute(root, setup + CORE + '\n' + ABORT +
                                  '\nabort_core_update checksum-failed\n')
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertTrue(backup.exists())
            self.assertIn('checksum-failed', result.stderr)
            self.assertNotIn('已恢复并验证', result.stderr)

    def outer_fixture(self, root, failure=''):
        backup = root / 'main-backup'
        backup.mkdir()
        targets = []
        for name in ('main.yaml', 'hy2.service', 'main.env', 'hysteria'):
            target = root / name
            target.write_text('candidate-' + name, encoding='utf-8')
            key = hashlib.sha256(target.as_posix().encode()).hexdigest()
            (backup / key).write_text('old-' + name, encoding='utf-8')
            (backup / (key + '.present')).touch()
            targets.append(target)
        setup = 'FAILURE=' + shlex.quote(failure) + '''
TX_ACTIVE=1
TX_DIR="$TEST_ROOT/main-backup"
HY2_CORE_NEW_BIN_PATH=""
OLD_SERVICE_ENABLED=enabled
OLD_SERVICE_ACTIVE=1
OLD_TEMP_ACTIVE_UNITS=(hy2-temp-test.service)
TX_TARGETS=("$TEST_ROOT/main.yaml" "$TEST_ROOT/hy2.service" "$TEST_ROOT/main.env" "$TEST_ROOT/hysteria")
tx_key() { printf '%s' "$1" | sha256sum | awk '{print $1}'; }
cp() {
  [[ "$FAILURE" != cp || "${@: -1}" != "$TEST_ROOT/main.env" ]] || return 19
  command cp "$@"
}
install() { [[ "$FAILURE" != install ]] || return 20; command install "$@"; }
'''
        return setup, backup, targets

    def test_outer_success_restores_config_metadata_unit_core_and_checks_services(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            setup, backup, targets = self.outer_fixture(root)
            result = self.execute(root, setup + OUTER + '\nrollback_transaction\n')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(backup.exists())
            for target in targets:
                self.assertEqual(target.read_text(), 'old-' + target.name)
            self.assertEqual((root / 'health.calls').read_text().splitlines(),
                             ['hy2.service', 'hy2-temp-test.service'])

    def test_outer_copy_directory_or_service_failure_keeps_full_backup(self):
        for failure in ('cp', 'install', 'restart'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                setup, backup, targets = self.outer_fixture(root, failure)
                result = self.execute(root, setup + OUTER + '\nrollback_transaction\n')
                self.assertNotEqual(result.returncode, 0)
                for target in targets:
                    key = hashlib.sha256(target.as_posix().encode()).hexdigest()
                    self.assertTrue((backup / key).exists())
                self.assertNotIn('回滚验证通过', result.stderr)
                if failure != 'restart':
                    self.assertFalse((root / 'health.calls').exists())

    def test_systemd_step_failures_are_identified_without_claiming_recovery(self):
        for action in ('daemon-reload', 'enable'):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                setup, backup, _ = self.outer_fixture(root)
                systemctl = '''
systemctl() {
  echo "$*" >>"$TEST_ROOT/systemctl.calls"
  [[ "$1" != FAIL_ACTION ]] || { echo simulated-systemd-error >&2; return 23; }
  return 0
}
'''.replace('FAIL_ACTION', action)
                result = self.execute(root, setup + systemctl + OUTER + '\nrollback_transaction\n')
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(backup.exists())
                self.assertIn('systemctl ' + action, result.stderr)
                self.assertIn('exit=23', result.stderr)
                self.assertIn('simulated-systemd-error', result.stderr)
                self.assertIn('HY2_ROLLBACK_OLD_ENABLE_STATE=enabled ACTIVE=1', result.stderr)
                self.assertFalse((root / 'health.calls').exists())

    def test_exit_trap_reports_rollback_failure_even_when_original_status_is_zero(self):
        for original_status in (0, 42):
            with self.subTest(original_status=original_status), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                setup, backup, _ = self.outer_fixture(root, 'cp')
                body = (setup + OUTER + '\n' + ON_EXIT +
                        "\ntrap 'on_exit' EXIT\nexit " + str(original_status) + '\n')
                result = self.execute(root, body)
                self.assertEqual(result.returncode, original_status or 1, result.stderr)
                self.assertTrue(backup.exists())

    def test_actual_transaction_targets_enabled_state_and_health_helpers(self):
        # Use the emitted target array and begin/rollback transaction functions,
        # not a shortened hand-written list. Only systemd and UDP I/O are fake.
        common = SOURCE.split('cat >"${HY2_LIB_DIR}/common.sh" <<\'EOF\'\n', 1)[1].split('\nEOF\n', 1)[0]
        common_helpers = ''
        for name, following in [('hy2_meta_get', 'hy2_write_meta'),
                                ('hy2_port_is_listening_udp', 'hy2_wait_unit_and_udp_port'),
                                ('hy2_wait_unit_and_udp_port', 'hy2_unit_state'),
                                ('hy2_main_port', 'hy2_temp_meta_file')]:
            start = common.index(name + '() {')
            common_helpers += common[start:common.index('\n' + following + '() {', start)] + '\n'
        health_helpers = (function('hy2_managed_unit_port', 'hy2_restart_verify_managed_unit() {') +
                          function('hy2_restart_verify_managed_unit', 'install_hysteria() {'))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contents = {
                'etc/hysteria/main.yaml': 'listen: 0.0.0.0:443\n',
                'etc/systemd/system/hy2.service': '[Service]\nExecStart=mock\n[Install]\nWantedBy=multi-user.target\n',
                'etc/sysctl.d/99-hy2-bbr.conf': 'net.ipv4.tcp_congestion_control=bbr\n',
                'usr/local/bin/hysteria': '#!/usr/bin/env bash\n[[ "$1" == version ]]\n',
                'usr/local/lib/hy2/acme-reload.sh': '#!/bin/sh\nexit 0\n',
                'var/lib/hy2/main/main.env': 'MAIN_PORT=443\n',
                'var/lib/hy2/main/main.password': 'fixture-password\n',
                'root/hy2_main_url.txt': 'fixture-private-url\n',
                'root/hy2_main_subscription_base64.txt': 'fixture-subscription\n',
            }
            for relative, text in contents.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(text.encode())
            (root / 'usr/local/bin/hysteria').chmod(0o755)
            (root / 'unit-active').touch()
            header = MAIN[:MAIN.index('tx_key() {')].replace('source /usr/local/lib/hy2/common.sh', ':')
            for relative in contents:
                # Variable-backed paths expand below; literal target paths are
                # mapped directly into this one isolated temporary workspace.
                header = header.replace('/' + relative, shlex.quote((root / relative).as_posix()))
            header = header.replace('/usr/bin/hysteria', shlex.quote((root / 'usr/bin/hysteria').as_posix()))
            begin = function('tx_key', 'rollback_transaction() {')
            begin = begin.replace('/var/tmp/hy2-main-transaction.', (root / 'hy2-main-transaction.').as_posix())
            setup = '''
HY2_MAIN_CFG="$TEST_ROOT/etc/hysteria/main.yaml"
HY2_RENEW_HOOK="$TEST_ROOT/usr/local/lib/hy2/acme-reload.sh"
HY2_MAIN_STATE_FILE="$TEST_ROOT/var/lib/hy2/main/main.env"
HY2_MAIN_PASSWORD_FILE="$TEST_ROOT/var/lib/hy2/main/main.password"
HY2_DEFAULTS_FILE="$TEST_ROOT/absent-defaults"
PATH="$TEST_ROOT/usr/local/bin:$PATH"
timeout() { shift; "$@"; }
sleep() { :; }
ss() { printf 'UNCONN 0 0 0.0.0.0:443 0.0.0.0:*\\n'; }
systemctl() {
  echo "$*" >>"$TEST_ROOT/systemctl.calls"
  local unit="${@: -1}"
  case "$1" in
    is-enabled) [[ "$unit" == hy2.service ]] && echo enabled ;;
    is-active) [[ "$unit" == hy2.service && -f "$TEST_ROOT/unit-active" ]] ;;
    list-units) return 0 ;;
    stop) [[ "$unit" == hy2.service ]] && rm -f "$TEST_ROOT/unit-active" ;;
    daemon-reload) [[ -s "$TEST_ROOT/etc/systemd/system/hy2.service" ]] ;;
    enable) grep -q '^WantedBy=multi-user.target$' "$TEST_ROOT/etc/systemd/system/hy2.service" ;;
    restart)
      [[ "$unit" == hy2.service ]] || return 64
      grep -q '^MAIN_PORT=443$' "$HY2_MAIN_STATE_FILE" || return 65
      grep -q '^listen: 0.0.0.0:443$' "$HY2_MAIN_CFG" || return 66
      "$TEST_ROOT/usr/local/bin/hysteria" version || return 67
      touch "$TEST_ROOT/unit-active"
      ;;
    *) return 68 ;;
  esac
}
'''
            mutate = '''
begin_transaction
for target in "${TX_TARGETS[@]}"; do
  if [[ -f "$target" ]]; then printf 'candidate-corruption' >"$target"; fi
done
rollback_transaction
'''
            result = self.execute(root, setup + header + begin + OUTER + common_helpers + health_helpers + mutate)
            self.assertEqual(result.returncode, 0, result.stderr)
            for relative, text in contents.items():
                self.assertEqual((root / relative).read_bytes(), text.encode(), relative)
            calls = (root / 'systemctl.calls').read_text().splitlines()
            self.assertIn('enable hy2.service', calls)
            self.assertIn('restart hy2.service', calls)
            self.assertTrue((root / 'unit-active').exists())
            self.assertEqual(list(root.glob('hy2-main-transaction.*')), [])

            # Debian Bash preserves the triggering failure status for a bare
            # return inside this EXIT -> if ! rollback -> port helper nesting.
            # Execute the real on_exit and port helpers with the same complete
            # transaction snapshot; rollback must restart the main listener
            # while preserving the original deployment's nonzero exit status.
            exit_mutate = mutate.rsplit('rollback_transaction', 1)[0]
            exit_mutate += "trap 'on_exit' EXIT\nexit 1\n"
            result = self.execute(root, setup + header + begin + OUTER + common_helpers +
                                  health_helpers + ON_EXIT + exit_mutate)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn('回滚验证通过', result.stderr)
            self.assertNotIn('端口解析失败', result.stderr)
            for relative, text in contents.items():
                self.assertEqual((root / relative).read_bytes(), text.encode(), relative)
            self.assertTrue((root / 'unit-active').exists())
            self.assertEqual(list(root.glob('hy2-main-transaction.*')), [])


if __name__ == '__main__':
    unittest.main()
