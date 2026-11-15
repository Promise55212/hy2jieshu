"""Safe uninstall behaviors exercised with fake systemctl and temporary paths."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'hy2-uninstall.sh'


class UninstallSafetyTest(unittest.TestCase):
    def bash(self, body, *args):
        return subprocess.run(['bash', '-c', 'source "$1"\n' + body,
                               'test', str(SCRIPT), *map(str, args)],
                              capture_output=True, text=True, timeout=15)

    def test_syntax(self):
        p = subprocess.run(['bash', '-n', str(SCRIPT)], capture_output=True,
                           text=True, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_stop_error_aborts_before_firewall_teardown(self):
        p = self.bash('''
systemctl() {
  if [[ "$1" == show ]]; then echo loaded; return 0; fi
  if [[ "$1" == stop ]]; then return 1; fi
}
stop_unit hy2.service
printf 'UNSAFE_TEARDOWN\\n'
''')
        self.assertNotEqual(p.returncode, 0)
        self.assertNotIn('UNSAFE_TEARDOWN', p.stdout)
        self.assertIn('could not stop', p.stderr)

    def test_deactivating_service_is_not_treated_as_stopped(self):
        p = self.bash('''
systemctl() {
  if [[ "$1" == show && "$4" == LoadState ]]; then echo loaded
  elif [[ "$1" == show ]]; then echo deactivating
  fi
}
stop_unit hy2.service
printf 'UNSAFE_TEARDOWN\\n'
''')
        self.assertNotEqual(p.returncode, 0)
        self.assertNotIn('UNSAFE_TEARDOWN', p.stdout)
        self.assertIn('still running/stopping', p.stderr)

    def test_other_projects_shared_commands_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'pq_add.sh'
            path.write_text('source /usr/local/lib/vless-reality/common.sh\n')
            p = self.bash('check_command_owner "$2"', path)
            self.assertNotEqual(p.returncode, 0)
            self.assertTrue(path.exists())
            path.write_text('source /usr/local/lib/hy2/common.sh\n')
            self.assertEqual(self.bash('check_command_owner "$2"', path).returncode, 0)

    def test_retaining_data_suppresses_cleanup_hook_and_preserves_other_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            unit_dir = root / 'hy2-temp-test.service.d'
            unit_dir.mkdir()
            other = unit_dir / 'custom.conf'
            other.write_text('[Service]\nEnvironment=EXAMPLE=value\n')
            p = self.bash('''
prepare_stop_override hy2-temp-test.service "$2"
HY2_UNINSTALL_OVERRIDES=("$2/hy2-temp-test.service.d/90-hy2-uninstall.conf")
cat "${HY2_UNINSTALL_OVERRIDES[0]}"
systemctl() { :; }
cleanup_uninstall_overrides
''', root)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn('ExecStopPost=\n', p.stdout)
            self.assertTrue(other.exists())
            self.assertFalse((unit_dir / '90-hy2-uninstall.conf').exists())

    def test_only_owned_tables_and_precise_subscription_paths(self):
        source = SCRIPT.read_text(encoding='utf-8')
        self.assertIn('for table in hy2_pq hy2_iplimit hy2_daily_traffic hy2_manual_guard;', source)
        self.assertNotIn('flush ruleset', source)
        for value in ('/root/hy2_temp_subscription.txt', '/root/hy2_temp_subscription_base64.txt'):
            self.assertIn(value, source)
        self.assertNotIn('rm -rf -- /etc/hysteria', source)
        self.assertNotIn('rm -rf -- /etc/wireguard', source)
        self.assertNotIn('rm -rf -- /root/.acme.sh', source)

    def test_table_inspection_error_refuses_teardown(self):
        p = self.bash('''
nft() { return 1; }
remove_owned_tables
printf 'UNSAFE_TEARDOWN\\n'
''')
        self.assertNotEqual(p.returncode, 0)
        self.assertNotIn('UNSAFE_TEARDOWN', p.stdout)
        self.assertIn('cannot inspect nftables', p.stderr)

    def test_other_nft_tables_are_preserved(self):
        p = self.bash('''
nft() {
  if [[ "$1" == list ]]; then
    printf 'table inet hy2_pq\\ntable inet hy2_iplimit\\ntable inet portbw\\ntable inet unrelated\\n'
  else
    printf '%s\\n' "$*"
  fi
}
remove_owned_tables
''')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.splitlines(), ['delete table inet hy2_pq',
                                                'delete table inet hy2_iplimit'])

    def test_bandwidth_removal_is_limited_to_the_deleted_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '40020.json').write_text('{}')
            other = root / '40021.json'
            other.write_text('{}')
            cli = root / 'portbw'
            cli.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$*"\n')
            cli.chmod(0o755)
            p = self.bash('remove_node_bandwidth 40020 "$2" "$3"', root, cli)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(p.stdout.splitlines(), ['del 40020'])
            self.assertTrue(other.exists())

    def test_bandwidth_failure_aborts_before_metadata_removal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '40020.json').write_text('{}')
            cli = root / 'portbw'
            cli.write_text('#!/usr/bin/env bash\nexit 1\n')
            cli.chmod(0o755)
            p = self.bash('remove_node_bandwidth 40020 "$2" "$3"\nprintf "UNSAFE_PURGE\\n"', root, cli)
            self.assertNotEqual(p.returncode, 0)
            self.assertNotIn('UNSAFE_PURGE', p.stdout)
            self.assertIn('metadata retained', p.stderr)

    def test_no_bandwidth_record_does_not_require_installed_portbw(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self.bash('remove_node_bandwidth 40020 "$2" /nonexistent/portbw', tmp)
            self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == '__main__':
    unittest.main()
