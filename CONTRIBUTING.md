# 贡献指南

欢迎 issue / PR 🙏。

## 跑测试(无需飞书 / 网络)

```bash
python3 -m unittest discover -s tests
```

纯逻辑单测(数据汇总、配置生成、权限编辑),不碰飞书 API,秒级跑完。

## 代码约定

- **codata(`agent-os/feishu_mcp.py` + `datastore.py`)保持纯 stdlib 零依赖**——别引第三方包(部署机零 pip 依赖是卖点)。脚本(scripts/)可用第三方。
- 命名 / 注释跟现有代码一致;**改动最小面**,别顺手重构周围。
- 提交前:跑测试 +(装了的话)`ruff check agent-os/`。

## 改了什么就测什么

- 改了 codata 的计算逻辑 → 在 `tests/` 加 / 改对应单测。
- 改了配置生成(`setup_wizard.gen_config`)或权限编辑(`onboard/offboard`)→ `tests/` 已有覆盖,别让它变红。

## 提 PR

1. fork → 建分支 → 改 → **跑测试** → PR。
2. 说清:改了啥、为什么、怎么验证的。
3. ⚠️ 别在 PR / issue 里贴任何 `app_secret` / `api_key` / `open_id`。
