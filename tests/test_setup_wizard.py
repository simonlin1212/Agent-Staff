"""配置向导 gen_config 的单元测试——确保向导拼出的 config.toml 结构正确、是合法 TOML。"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "agent-os", "scripts"))
import setup_wizard as w  # noqa: E402

SAMPLE = [
    {"dept": "公司", "alias": "ceo", "app_id": "cli_C", "app_secret": "S_C", "open_id": "ou_me"},
    {"dept": "自媒体运营部", "alias": "media", "app_id": "cli_M", "app_secret": "S_M", "open_id": ""},
    {"dept": "财务部", "alias": "finance", "app_id": "cli_F", "app_secret": "S_F", "open_id": "ou_f"},
]


class TestGenConfig(unittest.TestCase):
    def setUp(self):
        self.claude = w.gen_config("anthropic", "main", "", "", "claude-opus-4-8", "sk-x", "anthropic.main", SAMPLE)
        self.ds = w.gen_config("deepseek", "main", "openai-compatible", "https://api.deepseek.com/v1",
                               "deepseek-chat", "sk-ds", "deepseek.main", SAMPLE)

    def test_three_of_each_block(self):
        for cfg in (self.claude, self.ds):
            self.assertEqual(cfg.count("[[mcp.servers]]"), 3)
            self.assertEqual(cfg.count("[channels.lark."), 3)
            self.assertEqual(cfg.count("[peer_groups."), 3)

    def test_empty_open_id_falls_back_to_star(self):
        self.assertIn('external_peers = ["*"]', self.claude)  # media 没填 → 暂时全开放

    def test_filled_open_id_used(self):
        self.assertIn('external_peers = ["ou_me"]', self.claude)

    def test_deepseek_openai_compatible(self):
        self.assertIn('kind = "openai-compatible"', self.ds)
        self.assertIn("api.deepseek.com", self.ds)

    def test_claude_has_no_kind(self):
        self.assertNotIn("kind =", self.claude)  # anthropic 不需要 kind/uri

    def test_model_provider_wired(self):
        self.assertIn('model_provider = "deepseek.main"', self.ds)

    def test_is_valid_toml(self):
        try:
            import tomllib  # py3.11+
        except ModuleNotFoundError:
            try:
                import tomli as tomllib  # py<3.11:装了 tomli 才验(CI 的 3.9 job 会装)
            except ModuleNotFoundError:
                self.skipTest("需 py3.11+ 或 pip install tomli 才能验证 TOML")
        for cfg in (self.claude, self.ds):
            d = tomllib.loads(cfg)  # 解析不报错 = 合法 TOML
            self.assertEqual(set(d["agents"]), {"ceo", "media", "finance"})


if __name__ == "__main__":
    unittest.main()
