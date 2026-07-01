# 安全策略

这个项目会接触 **飞书应用凭证、模型 API key、你的经营 / 财务数据**——安全上请认真对待。

## 报告漏洞

发现安全问题,请**私下**联系维护者(GitHub 私信 / 邮件),**别公开发 PoC**。我们会尽快回应。

## 敏感数据怎么处理(零进仓库)

- 飞书 `app_secret`、模型 API key、`open_id`、经营数据 —— **全部走 `*.local` / `config.toml` / `dept_registry.json`,已被 `.gitignore`**,绝不进版本库。
- **提交前自查**:`git status` 里不该出现 `.feishu凭证.local` / `config.toml` / `dept_registry.json`。仓库只提交 `.example` 模板。
- 仓库已配 `.gitignore` 覆盖 `*.local / .env / *.key / *.pem / .secret_key` 等。

## 凭证存储建议

- **模型凭证**:优先用 `zeroclaw auth paste-token`(Claude 订阅)/ `auth login`(OAuth),让 zeroclaw **加密托管**,而不是明文写进 `config.toml`。
- **飞书 app_secret**:写在本地 `config.toml`(已 gitignore)。别截图 / 别贴聊天。

## 权限与数据位置

- agent 用飞书 `open_id` 白名单(`external_peers`)锁「谁能 @ 它」——私聊 + 群都管。
- 你的数据存在**你自己的飞书 / Lark 租户**里(对字节跳动可见,等同任何飞书用户;海外 Lark 数据在新加坡)。本项目不把你的数据发去任何第三方。
