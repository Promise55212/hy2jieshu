import datetime as dt
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = (ROOT / "hy2.sh").read_text(encoding="utf-8")
RENDERER = INSTALLER.split('cat >"${HY2_LIB_DIR}/render_table.py" <<\'EOF\'\n', 1)[1].split("\nEOF\n", 1)[0]


class TempNames(unittest.TestCase):
    def render(self, mode, rows, columns=200):
        return subprocess.run([sys.executable, "-X", "utf8", "-c", RENDERER, mode], input=rows,
                              capture_output=True, text=True, encoding="utf-8", check=True,
                              env={**os.environ, "COLUMNS": str(columns)}).stdout

    def test_human_audit_keeps_type_visible_in_narrow_terminal(self):
        rows = ("hy2.service\tactive\t443\tyes\t4\tlocal\n"
                "hy2-temp-legacy-local.service\tactive\t40000\tyes\t4\tlocal\n"
                "hy2-temp-legacy-nat.service\tactive\t40001\tyes\t4\tnat\n"
                "hy2-temp-nat-new.service\tactive\t40002\tyes\t4\tnat\n")
        narrow = self.render("hy2", rows, 84)
        self.assertIn("hy2-temp-tmp-│", narrow)
        self.assertIn("hy2-temp-nat-│", narrow)
        wide = self.render("hy2", rows)
        self.assertIn("hy2.service", wide)
        self.assertIn("hy2-temp-tmp-legacy-local.service*", wide)
        self.assertIn("hy2-temp-nat-legacy-nat.service*", wide)
        self.assertIn("hy2-temp-nat-new.service", wide)
        self.assertNotIn("hy2-temp-nat-nat-new", wide)
        self.assertNotIn("* 旧节点", self.render("pq", "40001\thy2-temp-legacy-nat\n"))

    @unittest.skipUnless(os.name == "posix" and shutil.which("bash"), "requires Bash")
    def test_creator_prepares_real_tag_and_share_name(self):
        naming = INSTALLER.split('RAW_ID="${id:-$(date +%Y%m%d%H%M%S)-$(openssl rand -hex 2)}"', 1)[1]
        naming = naming.split('\nMETA="$(hy2_temp_meta_file "$TAG")"', 1)[0]
        shell = INSTALLER.split("\nhy2_safe_id()", 1)[1].split("\nhy2_is_valid_temp_tag()", 1)[0]
        program = ("set -eu\nhy2_safe_id()" + shell + 'RAW_ID="$1"\nLANDING="$2"' + naming
                   + '\nprintf "%s\\n%s\\n" "$TAG" "$DISPLAY_NAME"\n')
        for node_id, outlet, expected in (("example", "local", "hy2-temp-tmp-example"),
                                          ("example", "nat", "hy2-temp-nat-example"),
                                          ("tmp-user", "local", "hy2-temp-tmp-user"),
                                          ("nat-user", "nat", "hy2-temp-nat-user"),
                                          ("tmp-named", "nat", "hy2-temp-nat-tmp-named")):
            with self.subTest(node_id=node_id, outlet=outlet):
                result = subprocess.run(["bash", "-s", "--", node_id, outlet], input=program,
                                        text=True, capture_output=True, check=True)
                self.assertEqual(result.stdout.splitlines(), [expected, expected])

    @unittest.skipUnless(os.name == "posix", "requires fcntl")
    def test_traffic_displays_new_nat_tags_and_keeps_legacy_alias(self):
        sys.path.insert(0, str(ROOT))
        self.addCleanup(sys.path.pop, 0)
        import traffic

        now = dt.datetime.now(dt.timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "temp").mkdir()
            for port, tag in ((40001, "hy2-temp-legacy"), (40002, "hy2-temp-nat-current")):
                (root / "temp" / (tag + ".env")).write_text(
                    f"TAG={tag}\nPORT={port}\nPASSWORD=test\nCREATE_EPOCH=1\n"
                    f"EXPIRE_EPOCH={int(now.timestamp()) + 3600}\nLANDING=nat\n", encoding="utf-8")
            nodes = traffic.discover(root, now)
        self.assertEqual(nodes["hy2-temp-legacy"]["display_name"], "hy2-nat-legacy")
        self.assertEqual(nodes["hy2-temp-nat-current"]["display_name"], "hy2-temp-nat-current")
