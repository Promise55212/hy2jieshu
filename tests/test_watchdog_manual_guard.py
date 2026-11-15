"""Run generated watchdog/stop-post scripts against fake service/kernel tools."""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "hy2.sh"


def generated(name):
    source = SOURCE.read_text(encoding="utf-8")
    match = re.search(r'cat >"\$\{HY2_SBIN_DIR\}/' + re.escape(name)
                      + r'" <<\'EOF\'\n(.*?)\nEOF', source, re.S)
    if not match:
        raise AssertionError("generated script missing: " + name)
    return match.group(1) + "\n"


class WatchdogManualGuardTest(unittest.TestCase):
    def run_case(self, mode, expired=False):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("bin", "temp", "quota", "iplimit", "run"):
                (root / name).mkdir()
            meta = root / "temp/hy2-temp-test.env"
            original = ("TAG=hy2-temp-test\nPORT=40020\nIP_VERSION=4\nIP_LIMIT=0\n"
                        f"EXPIRE_EPOCH={1 if expired else 4000000000}\nLANDING=local\n"
                        "WATCHDOG_FAILURES=0\nWATCHDOG_GRACE_START_EPOCH=0\n")
            meta.write_text(original, encoding="utf-8")
            if mode != "absent":
                (root / "state.json").write_text('{"schema":1,"paused":[40020],"bans":{}}')
            (root / "common.sh").write_text(r'''
HY2_TEMP_STATE_DIR="$test_dir/temp"
HY2_QUOTA_STATE_DIR="$test_dir/quota"
HY2_IPLIMIT_STATE_DIR="$test_dir/iplimit"
HY2_LOCK_DIR="$test_dir/run"
hy2_require_root_supported_os() { :; }
hy2_ensure_runtime_dirs() { :; }
hy2_try_lock_fd() { return 0; }
hy2_is_valid_temp_tag() { [[ "$1" == hy2-temp-test ]]; }
hy2_collect_temp_tags() { echo hy2-temp-test; }
hy2_meta_get() { sed -n "s/^$2=//p" "$1" | head -n1; }
hy2_il_family_guard_state() { echo active; }
hy2_port_is_listening_udp() { return 0; }
hy2_temp_meta_file() { echo "$test_dir/temp/$1.env"; }
hy2_temp_cfg_file() { echo "$test_dir/$1.yaml"; }
hy2_temp_unit_file() { echo "$test_dir/$1.service"; }
hy2_temp_url_file() { echo "$test_dir/$1.url"; }
''', encoding="utf-8")
            tools = {
                "hy2-guard": r'''#!/usr/bin/env bash
echo "GUARD $1" >>"$test_dir/calls"
case "$1" in
  audit) [[ -f "$test_dir/kernel-restored" ]] ;;
  restore)
    if [[ "$mode" == recover || "$mode" == recheck-fails ]]; then
      [[ "$mode" != recover ]] || touch "$test_dir/kernel-restored"
    else
      exit 1
    fi ;;
esac
''',
                "systemctl": r'''#!/usr/bin/env bash
echo "SYSTEMCTL $*" >>"$test_dir/calls"
if [[ "$1" == stop && "$2" == hy2-temp-test.service ]]; then
  bash "$test_dir/cleanup.sh" hy2-temp-test --from-stop-post
fi
''',
                "temp-sub": "#!/usr/bin/env bash\nexit 0\n",
            }
            for name, body in tools.items():
                path = root / "bin" / name
                path.write_text(body, encoding="utf-8")
                path.chmod(0o755)
            # The absent case has neither a persisted policy nor the CLI.
            if mode in ("absent", "missing-cli"):
                (root / "bin/hy2-guard").unlink()
            prelude = 'test_dir="$(cd "$1" && pwd)"\nexport test_dir\nexport PATH="$test_dir/bin:$PATH"\n'
            for name, target in (("hy2_managed_watchdog.sh", "watchdog.sh"),
                                 ("hy2_cleanup_one.sh", "cleanup.sh")):
                script = generated(name)
                script = re.sub(r'source /usr/local/lib/hy2/[^\n]+',
                                'source "$test_dir/common.sh"', script)
                script = script.replace("/usr/local/sbin/hy2-guard", "${test_dir}/bin/hy2-guard")
                script = script.replace("/var/lib/hy2/manual-guard/state.json", "${test_dir}/state.json")
                script = script.replace("/usr/local/sbin/hy2_temp_sub.sh", "${test_dir}/bin/temp-sub")
                if target == "watchdog.sh":
                    script = prelude + script
                (root / target).write_text(script, encoding="utf-8")
            env = dict(os.environ, mode=mode)
            result = subprocess.run(["bash", str(root / "watchdog.sh"), str(root)],
                                    env=env, capture_output=True, text=True, timeout=15)
            calls_file = root / "calls"
            calls = calls_file.read_text() if calls_file.exists() else ""
            return result, calls, meta.exists(), meta.read_text() if meta.exists() else "", original

    def test_missing_table_is_restored_then_reaudited_before_listener_scan(self):
        result, calls, exists, after, before = self.run_case("recover")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        actions = calls.splitlines()
        self.assertEqual(actions[:3], ["GUARD audit", "GUARD restore", "GUARD audit"])
        self.assertNotIn("SYSTEMCTL stop", calls)
        self.assertIn("MANUAL_GUARD_RECOVERED", result.stderr)
        self.assertTrue(exists)
        self.assertEqual(after, before)

    def test_failed_restore_stops_main_and_temp_without_deleting_expired_metadata(self):
        result, calls, exists, after, before = self.run_case("restore-fails", expired=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SYSTEMCTL stop hy2.service", calls)
        self.assertIn("SYSTEMCTL stop hy2-temp-test.service", calls)
        self.assertNotIn("SYSTEMCTL restart", calls)
        self.assertIn("MANUAL_GUARD_FAILED", result.stderr)
        self.assertTrue(exists)
        self.assertEqual(after, before)

    def test_restore_success_without_auditable_rules_still_fails_closed(self):
        result, calls, exists, after, before = self.run_case("recheck-fails")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("GUARD restore\nGUARD audit", calls)
        self.assertIn("SYSTEMCTL stop hy2.service", calls)
        self.assertNotIn("SYSTEMCTL restart", calls)
        self.assertTrue(exists)
        self.assertEqual(after, before)

    def test_missing_optional_module_does_not_block_normal_nodes(self):
        result, calls, exists, after, before = self.run_case("absent")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("GUARD", calls)
        self.assertNotIn("SYSTEMCTL stop", calls)
        self.assertTrue(exists)
        self.assertEqual(after, before)

    def test_persisted_state_with_missing_cli_is_not_silently_ignored(self):
        result, calls, exists, after, before = self.run_case("missing-cli")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SYSTEMCTL stop hy2.service", calls)
        self.assertNotIn("SYSTEMCTL restart", calls)
        self.assertTrue(exists)
        self.assertEqual(after, before)

    def test_doctor_checks_optional_guard_without_changing_rules(self):
        doctor = generated("hy2_doctor.sh")
        block = doctor.split('if [[ -e /var/lib/hy2/manual-guard/state.json', 1)[1]
        block = block.split('if [[ -f /etc/wireguard/wg-nat.env', 1)[0]
        self.assertIn("hy2-guard audit", block)
        self.assertNotIn("hy2-guard restore >", block)
        self.assertNotIn('systemctl start', block)


if __name__ == "__main__":
    unittest.main()
