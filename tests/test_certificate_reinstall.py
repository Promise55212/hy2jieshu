"""Execute emitted ACME integration with retained-state reinstall fixtures."""
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CertificateReinstallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (ROOT / 'hy2.sh').read_text(encoding='utf-8')
        cls.hook = source.split('cat >"${HY2_RENEW_HOOK}" <<\'HOOK\'\n', 1)[1].split('\nHOOK\n', 1)[0]
        cls.issue = 'issue_or_renew_cert_zerossl() {' + source.split(
            'issue_or_renew_cert_zerossl() {', 1)[1].split('\nenable_bbr() {', 1)[0]

    def run_hook(self, *, state=True, unit=True, deploying=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('cert.pem', 'key.pem'):
                (root / name).write_text('mock-valid-keypair', encoding='utf-8')
            if state:
                (root / 'main.env').write_text('MAIN_PORT=443\n', encoding='utf-8')
            if unit:
                (root / 'hy2.service').write_text('[Service]\n', encoding='utf-8')
            setup = 'TEST_ROOT=' + shlex.quote(root.as_posix()) + '''
HY2_MAIN_STATE_FILE="$TEST_ROOT/main.env"
HY2_TEMP_LOCK_HELD=1
HY2_MAIN_DEPLOYING=''' + ('1' if deploying else '0') + '''
hy2_ensure_runtime_dirs() { :; }
hy2_log() { :; }
hy2_meta_get() {
  case "$2" in
    TLS_CERT) echo "$TEST_ROOT/cert.pem" ;;
    TLS_KEY) echo "$TEST_ROOT/key.pem" ;;
  esac
}
openssl() { printf 'mock-matching-public-key'; }
systemctl() {
  printf '%s\\n' "$*" >>"$TEST_ROOT/systemctl.calls"
  if [[ "$1" == restart ]]; then [[ -f "$TEST_ROOT/hy2.service" ]]; else return 0; fi
}
timeout() { [[ "$1" != --foreground ]] || shift; shift; "$@"; }
hy2_main_port() { echo 443; }
hy2_wait_unit_and_udp_port() { :; }
'''
            hook = self.hook.replace('source /usr/local/lib/hy2/common.sh', ':')
            hook = hook.replace('/etc/systemd/system/hy2.service', (root / 'hy2.service').as_posix())
            result = subprocess.run(['bash'], input=setup + hook, capture_output=True,
                                    text=True, encoding='utf-8', timeout=15)
            calls = root / 'systemctl.calls'
            return result, calls.read_text(encoding='utf-8') if calls.exists() else ''

    def test_first_deployment_defers_reload_until_metadata_exists(self):
        result, calls = self.run_hook(state=False, unit=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, '')

    def test_reinstall_with_retained_state_and_missing_unit_defers_only_during_deploy(self):
        result, calls = self.run_hook(state=True, unit=False, deploying=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls, '')

    def test_unattended_renewal_with_missing_unit_still_fails(self):
        result, calls = self.run_hook(state=True, unit=False, deploying=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('restart hy2.service', calls)

    def test_existing_unit_is_reloaded_even_during_deployment(self):
        for deploying in (False, True):
            with self.subTest(deploying=deploying):
                result, calls = self.run_hook(deploying=deploying)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('restart hy2.service', calls)

    def test_install_cert_receives_temporary_marker_but_persistent_reload_command_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            acme = root / 'acme.sh'
            acme.write_bytes(b'''#!/usr/bin/env bash
if [[ "$1" == --install-cert ]]; then
  printf '%s\\n' "${HY2_MAIN_DEPLOYING:-unset}" >"$TEST_ROOT/deploy.marker"
  printf '%s\\n' "$@" >"$TEST_ROOT/install.args"
  while (( $# )); do
    if [[ "$1" == --key-file || "$1" == --fullchain-file ]]; then touch "$2"; shift; fi
    shift
  done
fi
exit 0
''')
            acme.chmod(0o755)
            issue = self.issue.replace('local acme_home="/root/.acme.sh"', 'local acme_home="$TEST_ROOT"')
            issue = issue.replace('local cert_dir="/etc/hysteria/certs/${domain}"',
                                  'local cert_dir="$TEST_ROOT/certs/${domain}"')
            setup = 'export TEST_ROOT=' + shlex.quote(root.as_posix()) + '''
HY2_RENEW_HOOK=/usr/local/lib/hy2/acme-reload.sh
unset HY2_MAIN_DEPLOYING
write_renew_hook() { :; }
hy2_die() { exit 19; }
'''
            script = setup + issue + '''
issue_or_renew_cert_zerossl hy2.example.com
[[ -z "${HY2_MAIN_DEPLOYING+x}" ]] || exit 20
'''
            result = subprocess.run(['bash'], input=script, capture_output=True,
                                    text=True, encoding='utf-8', timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / 'deploy.marker').read_text().strip(), '1')
            args = (root / 'install.args').read_text().splitlines()
            self.assertEqual(args[args.index('--reloadcmd') + 1], '/usr/local/lib/hy2/acme-reload.sh')
            self.assertFalse(any('HY2_MAIN_DEPLOYING' in arg for arg in args))


if __name__ == '__main__':
    unittest.main()
