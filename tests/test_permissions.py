"""权限编辑(onboard/offboard 改 config 白名单)的单元测试——按人锁的安全地基,改错=越权或锁死。"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "agent-os", "scripts"))
import onboard   # noqa: E402
import offboard  # noqa: E402

CONFIG = '''[channels.lark.sales]
app_id = "cli_SALES"
app_secret = "SECRET_SALES"
use_feishu = true

[peer_groups.sales]
channel = "lark.sales"
agents = ["sales"]
external_peers = ["ou_existing"]

[channels.lark.finance]
app_id = "cli_FIN"
app_secret = "SECRET_FIN"

[peer_groups.finance]
channel = "lark.finance"
agents = ["finance"]
external_peers = ["ou_a", "ou_b"]
'''


class TestBotCreds(unittest.TestCase):
    def test_extracts_id_secret(self):
        self.assertEqual(onboard.bot_creds(CONFIG, "sales"), ("cli_SALES", "SECRET_SALES"))

    def test_missing_alias(self):
        aid, sec = onboard.bot_creds(CONFIG, "nope")
        self.assertIsNone(aid)


class TestAddPeer(unittest.TestCase):
    def test_adds_and_keeps_existing(self):
        new, added = onboard.add_peer(CONFIG, "sales", "ou_new")
        self.assertTrue(added)
        self.assertIn('"ou_new"', new)
        self.assertIn('"ou_existing"', new)

    def test_idempotent(self):
        _, added = onboard.add_peer(CONFIG, "sales", "ou_existing")
        self.assertFalse(added)  # 已存在不重复加

    def test_only_target_group_touched(self):
        new, _ = onboard.add_peer(CONFIG, "sales", "ou_new")
        self.assertIn('external_peers = ["ou_a", "ou_b"]', new)  # finance 不动


class TestRemovePeer(unittest.TestCase):
    def test_removes_keeps_others(self):
        new, removed = offboard.remove_peer_all(CONFIG, "ou_a")
        self.assertIn("finance", removed)
        self.assertNotIn('"ou_a"', new)
        self.assertIn('"ou_b"', new)  # 同组其他人保留

    def test_absent_is_noop(self):
        new, removed = offboard.remove_peer_all(CONFIG, "ou_ghost")
        self.assertEqual(removed, [])


class TestRoundTrip(unittest.TestCase):
    def test_add_then_remove_restores_exactly(self):
        added, _ = onboard.add_peer(CONFIG, "sales", "ou_temp")
        restored, _ = offboard.remove_peer_all(added, "ou_temp")
        self.assertEqual(restored.strip(), CONFIG.strip())


if __name__ == "__main__":
    unittest.main()
