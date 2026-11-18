"""HY2 daily traffic: UDP counter reconciliation and reboot-safe baselines."""
from contextlib import redirect_stdout
import datetime as dt
import importlib.util
from io import StringIO
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

FILE = Path(__file__).resolve().parents[1] / "traffic.py"
spec = importlib.util.spec_from_file_location("hy2_daily_test", FILE)
tr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tr)


class FakeNft:
    def __init__(self):
        self.value = []
        self.commands = []

    def snapshot(self):
        return self.value

    def apply(self, commands):
        self.commands.extend(commands)


class DailyTest(unittest.TestCase):
    def setup_state(self, root):
        (root / "main").mkdir()
        (root / "temp").mkdir()
        (root / "main" / "main.env").write_text("MAIN_PORT=443\n", encoding="utf-8")
        (root / "main" / "main.password").write_text("test-secret-A\n", encoding="utf-8")
        (root / "temp" / "hy2-temp-test.env").write_text(
            "TAG=hy2-temp-test\nPORT=40020\nPASSWORD=secret-B\n"
            "CREATE_EPOCH=100\nEXPIRE_EPOCH=9999999999\n", encoding="utf-8")

    def test_discover_hy2_passwords_and_no_secret_exposure(self):
        with tempfile.TemporaryDirectory() as path:
            root = Path(path)
            self.setup_state(root)
            when = dt.datetime(2026, 11, 4, tzinfo=tr.TZ)
            nodes = tr.discover(root, when)
            self.assertEqual(nodes["main"]["port"], 443)
            self.assertEqual(nodes["hy2-temp-test"]["port"], 40020)
            self.assertNotIn("secret-B", repr(nodes))
            self.assertNotIn("test-secret-A", repr(nodes))
            self.assertEqual(len(nodes["main"]["key"]), 32)
            self.assertNotEqual(nodes["main"]["key"], nodes["hy2-temp-test"]["key"])
            (root / "temp" / "hy2-temp-test.env").write_text(
                "TAG=hy2-temp-test\nPORT=40020\nPASSWORD=new-pass\n"
                "CREATE_EPOCH=200\nEXPIRE_EPOCH=9999999999\n", encoding="utf-8")
            self.assertNotEqual(nodes["hy2-temp-test"]["key"],
                                tr.discover(root, when)["hy2-temp-test"]["key"])

    def test_udp_reconcile_does_not_touch_quota_and_ip_tables(self):
        nodes = {"main": {"tag": "main", "port": 443, "key": "a" * 32}}
        selected = {("main", "u"): None, ("main", "d"): None}
        with mock.patch.object(tr.uuid, "uuid4") as uuid4:
            uuid4.return_value.hex = "b" * 32
            cmd = tr.reconcile(nodes, selected, [], {})
        joined = "\n".join(cmd)
        self.assertIn("add table inet hy2_daily_traffic", joined)
        self.assertIn(" udp dport 443 ", joined)
        self.assertIn(" udp sport 443 ", joined)
        self.assertIn("hook input priority 10", joined)
        self.assertIn("hook output priority 10", joined)
        self.assertNotIn(" tcp ", joined)
        self.assertNotIn("hy2_pq", joined)
        self.assertNotIn("hy2_iplimit", joined)
        self.assertNotIn("flush ruleset", joined)

    def test_daily_collect_deltas_baseline_and_reset_after_reboot(self):
        with tempfile.TemporaryDirectory() as path:
            root = Path(path)
            self.setup_state(root)
            now = dt.datetime(2026, 11, 4, 14, 30, tzinfo=tr.TZ)
            fake = FakeNft()
            first = tr.collect(root, fake, now)
            tag = "hy2-temp-test"
            self.assertEqual(first["users"][tag]["days"]["2026-11-04"],
                             {"upload": 0, "download": 0})
            names = re.findall(r"add counter inet hy2_daily_traffic (t_[a-f0-9_ud]+)",
                               "\n".join(fake.commands))
            self.assertEqual(len(names), 4)
            u, d = [n for n in names if n.startswith("t_" + first["users"][tag]["key"])]
            self.assertTrue(u.endswith("_u") or d.endswith("_u"))
            vals = {u if u.endswith("_u") else d: 123,
                    u if u.endswith("_d") else d: 456}
            fake.value = [{"counter": {"name": name, "bytes": count}}
                          for name, count in vals.items()]
            second = tr.collect(root, fake, now)
            self.assertEqual(second["users"][tag]["days"]["2026-11-04"],
                             {"upload": 123, "download": 456})
            fake.value = [{"counter": {"name": name, "bytes": count + 10}}
                          for name, count in vals.items()]
            third = tr.collect(root, fake, now)
            self.assertEqual(third["users"][tag]["days"]["2026-11-04"],
                             {"upload": 133, "download": 466})
            # On reboot old names disappear; old totals must remain intact.
            fake.value = []
            fourth = tr.collect(root, fake, now)
            self.assertEqual(fourth["users"][tag]["days"]["2026-11-04"],
                             {"upload": 133, "download": 466})

    def test_prune_old_days_and_renewed_nodes(self):
        state = {"version": 1, "users": {"hy2-temp-test": {
            "key": "old-key", "days": {"2026-10-01": {"upload": 9, "download": 8}},
            "last": {}, "port": 40020, "tag": "hy2-temp-test",
        }}}
        tr.prune(state, {"hy2-temp-test": {"tag": "hy2-temp-test", "port": 40020,
                                           "key": "new-key"}}, dt.date(2026, 11, 4))
        self.assertEqual(state["users"], {})

    def test_nat_display_name_keeps_existing_traffic_and_selectors(self):
        with tempfile.TemporaryDirectory() as path:
            root = Path(path)
            self.setup_state(root)
            now = dt.datetime.now(tr.TZ)
            tag = "hy2-temp-test"
            display_name = "hy2-nat-test"
            fake = FakeNft()
            tr.collect(root, fake, now)
            state_file = root / "traffic/daily.json"
            stored = tr.load_state(state_file)
            day = now.date().isoformat()
            stored["users"][tag]["days"][day]["upload"] = 123
            tr.save_state(state_file, stored)

            meta = root / "temp" / (tag + ".env")
            with meta.open("a", encoding="utf-8") as stream:
                stream.write("LANDING=nat\n")
            # This ordinary node's short ID collides with the NAT display name.
            (root / "temp/hy2-temp-hy2-nat-test.env").write_text(
                "TAG=hy2-temp-hy2-nat-test\nPORT=40021\nPASSWORD=secret-C\n"
                "CREATE_EPOCH=100\nEXPIRE_EPOCH=9999999999\nLANDING=local\n",
                encoding="utf-8",
            )
            state = tr.collect(root, fake, now)
            self.assertEqual(state["users"][tag]["key"], stored["users"][tag]["key"])
            self.assertNotIn("display_name", tr.load_state(state_file)["users"][tag])

            with mock.patch.object(tr, "print_traffic_table") as print_table, redirect_stdout(StringIO()):
                tr.show(state)
            names = {row[0] for row in print_table.call_args.args[0]}
            self.assertEqual(names, {display_name, "hy2-temp-hy2-nat-test", "main"})

            for selector in (display_name, tag, "test", "40020"):
                with self.subTest(selector=selector), redirect_stdout(StringIO()) as output:
                    tr.show(state, selector, as_json=True)
                    records = json.loads(output.getvalue())["users"]
                    self.assertEqual([record["tag"] for record in records], [tag])
                    self.assertEqual(records[0]["days"][day]["upload"], 123)
                    self.assertNotIn("display_name", records[0])

    def test_invalid_nft_counter_fail_closed(self):
        with self.assertRaises(ValueError):
            tr.counters_in([{"counter": {"name": "t_" + "a"*32 + "_" + "b"*16 + "_u",
                                        "bytes": -1}}])


if __name__ == "__main__":
    unittest.main()
