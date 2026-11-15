"""Run the generated WG guards with controlled runtime handshake timestamps."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
NOW = 1800000000


class WGHandshakeClockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        health = (ROOT / 'vpswg.sh').read_text(encoding='utf-8')
        preflight = (ROOT / 'natjichang.sh').read_text(encoding='utf-8')
        cls.guards = {
            'health': health.split('echo "---- handshake check ----"\n', 1)[1]
                            .split('echo "---- marked HTTP exit-ip test ----"', 1)[0],
            'preflight': preflight[preflight.index('HS="$(wg show '):]
                                  .split('\nPREFLIGHT\n', 1)[0],
        }

    def check(self, guard, timestamp):
        # Execute the real emitted Bash, replacing only date and wg I/O.
        shell = '''set -e
WG_IF=wg-nat
HANDSHAKE_MAX=180
WG_PORT=51820
date() { printf '%s\\n' ''' + str(NOW) + '''; }
wg() { printf 'test-public-key %s\\n' "$TEST_HANDSHAKE"; }
fail() { exit 19; }
hy2_die() { exit 19; }
'''
        result = subprocess.run(['bash', '-c', 'TEST_HANDSHAKE="$1"\n' + shell + guard,
                                 '--', str(timestamp)],
                                capture_output=True, text=True, encoding="utf-8", timeout=10)
        return result.returncode

    def test_current_and_recent_handshakes(self):
        for name, guard in self.guards.items():
            for timestamp in (NOW, NOW - 90, NOW - 180):
                with self.subTest(guard=name, timestamp=timestamp):
                    self.assertEqual(self.check(guard, timestamp), 0)

    def test_stale_future_missing_and_invalid_handshakes(self):
        for name, guard in self.guards.items():
            for timestamp in (NOW - 181, NOW + 1, NOW + 240, 0, -1, '', 'invalid'):
                with self.subTest(guard=name, timestamp=timestamp):
                    self.assertNotEqual(self.check(guard, timestamp), 0)


if __name__ == '__main__':
    unittest.main()
