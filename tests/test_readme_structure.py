"""Keep README navigation and live-test reporting aligned with the HY2 release."""
from pathlib import Path
import re
import unittest
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
EVIDENCE = ROOT / "tests" / "REAL_MACHINE_ACCEPTANCE_2026-11-04.md"


class ReadmeContractTests(unittest.TestCase):
    def test_expected_navigation_order(self):
        doc = README.read_text(encoding="utf-8")
        anchors = [
            "queries", "create", "modify", "troubleshooting",
            "remove", "install", "wg-nat", "acceptance", "feature-gap",
        ]
        for anchor in anchors:
            self.assertIn(f'<a id="{anchor}"></a>', doc)
        ordered = ["queries", "create", "modify", "troubleshooting",
                   "remove", "install", "acceptance"]
        offsets = [doc.index(f'<a id="{a}"></a>') for a in ordered]
        self.assertEqual(offsets, sorted(offsets))

    def test_jieshu_six_chapter_document_contract(self):
        doc = README.read_text(encoding="utf-8")
        headings = re.findall(r"^## (.+)$", doc, re.M)
        self.assertEqual(headings, [
            "一、查询与检查", "二、新建节点", "三、修改与重置",
            "四、故障排查", "五、暂停、封禁与删除", "六、安装与更新",
        ])
        for anchor in (
            "advanced-queries", "node-link", "active-ips", "daily-traffic",
            "speed-logs", "subscription", "temp-create", "quota-ip",
            "quota-keep-cycle", "quota-reset-time", "portbw", "trouble-guide",
            "port-block", "pause-port", "source-blacklist", "blacklist-report",
            "node-manage", "hy2-install", "wg-nat", "daily-install",
            "portbw-install", "maintenance", "backup-recovery", "release-notes",
        ):
            with self.subTest(anchor=anchor):
                self.assertEqual(doc.count(f'<a id="{anchor}"></a>'), 1)

        self.assertEqual(doc.count("<details"), doc.count("</details>"))
        self.assertEqual(doc.count("```") % 2, 0)
        self.assertIn("portbw set 40020 10 10", doc)
        self.assertIn("静态 10/10 Mbps", doc)
        self.assertIn("自动降速", doc)
        self.assertNotIn("vless_mktemp.sh", doc)

    def test_linked_anchors_exist(self):
        doc = README.read_text(encoding="utf-8")
        anchors = set(re.findall(r'<a id="([a-z0-9-]+)"></a>', doc))
        for anchor in re.findall(r'\]\(#([a-z0-9-]+)\)', doc):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, anchors)

    def test_evidence_exists_and_scopes_claims(self):
        doc = README.read_text(encoding="utf-8")
        self.assertIn("tests/REAL_MACHINE_ACCEPTANCE_2026-11-04.md", doc)
        report = EVIDENCE.read_text(encoding="utf-8")
        for marker in (
            "Debian 13", "2026-11-04", "PR #3",
            "未实测", "WG fail-closed", "portbw",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, report)
        # Public release documentation must not include the VPS/NAT
        # addresses used during operator testing.
        self.assertNotIn("162.211.231.219", report)
        self.assertNotIn("108.241.87.175", report)

    def test_downloads_use_this_repository_and_existing_files(self):
        docs = [README, *sorted((ROOT / "docs").glob("*.md"))]
        downloads = []
        for path in docs:
            doc = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertNotIn("liucong552-art/ceshi", doc)
            for owner, name in re.findall(
                r"https://raw\.githubusercontent\.com/liucong552-art/"
                r"([^/]+)/main/([A-Za-z0-9_./-]+)", doc
            ):
                with self.subTest(path=path.name, download=name):
                    self.assertEqual(owner, "hy2jieshu")
                    self.assertTrue((ROOT / name).is_file(), name)
                    downloads.append(name)
        for name in ("hy2.sh", "hy2-uninstall.sh", "traffic.py",
                     "hy2-guard.py", "hy2-abuse.py", "vpswg.sh",
                     "natjichang.sh", "portbw.py", "portbw-install.sh"):
            self.assertIn(name, downloads)

    def test_document_links_resolve_and_historical_status_is_scoped(self):
        for path in [README, *sorted((ROOT / "docs").glob("*.md"))]:
            doc = path.read_text(encoding="utf-8")
            doc = re.sub(r"^ {0,3}(`{3,}|~{3,})[^\n]*\n.*?^ {0,3}\1[ \t]*(?:\n|$)",
                         "", doc, flags=re.M | re.S)
            for target in re.findall(r"\]\(([^)]+)\)", doc):
                if "://" in target or target.startswith("#"):
                    continue
                relative = unquote(target.split("#", 1)[0])
                with self.subTest(path=path.name, target=target):
                    self.assertTrue((path.parent / relative).is_file(), target)
        doc = README.read_text(encoding="utf-8")
        for status in ("当前真机通过", "复用已有证据", "仅自动化测试通过",
                       "尚未验证", "不适用"):
            self.assertIn(status, doc)
        self.assertIn("不自动计入本轮通过", doc)
        self.assertIn("docs/LEGACY_ACCEPTANCE_GUIDE.md", doc)

    def test_uninstall_and_service_docs_describe_real_interfaces(self):
        doc = README.read_text(encoding="utf-8")
        self.assertIn('<a id="uninstall"></a>', doc)
        for snippet in ("bash /root/hy2-uninstall.sh --yes",
                        "--yes --purge --remove-core", "默认只预览",
                        "WireGuard", "portbw", "acme.sh", "SSH",
                        "TLS_CERT", "hy2-managed-restore.service",
                        "hy2-managed-shutdown-save.service"):
            self.assertIn(snippet, doc)
        script = (ROOT / "hy2-uninstall.sh").read_text(encoding="utf-8")
        for option in ("--yes", "--purge", "--remove-core"):
            self.assertIn(option, script)
        self.assertNotIn("不提供一键卸载命令", doc)


if __name__ == "__main__":
    unittest.main()
