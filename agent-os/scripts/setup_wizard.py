#!/usr/bin/env python3
"""Agent-Staff 交互配置向导(被 setup.sh 调用)。

一步步问:数据应用凭证 → 建部门表 → 选模型 → 各部门 bot 凭证 → 自动生成 config.toml。
飞书自建应用要你先去后台建好(每部门一个 + 一个数据应用),见 docs/飞书接入指南.md;
本向导只负责把凭证拼成配置,省你手抠那一大坨 TOML(最容易拼不起来的地方)。
"""
import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))   # agent-os/scripts
AOS = os.path.dirname(HERE)                          # agent-os
ROOT = os.path.dirname(AOS)                           # Agent-Staff 根
MCP = os.path.join(AOS, "feishu_mcp.py")
CRED = os.path.join(AOS, ".feishu凭证.local")
CONFIG = os.path.join(ROOT, "agent-home", "config.toml")

# 完整 9 部门公司(与 provision.py 的 DEPARTMENTS 对齐)。加/删部门=改 provision.py + 这里。
# 向导里某部门 bot 留空即跳过它(不写进 config),所以不想要全部 9 个也没关系。
DEPTS = [
    ("公司", "ceo"),            # CEO 参谋长
    ("自媒体运营部", "media"),   # 营收
    ("电商部", "ecom"),         # 营收
    ("业务部", "biz"),          # 营收
    ("财务部", "finance"),      # 职能
    ("人力部", "hr"),           # 职能
    ("行政部", "admin"),        # 职能
    ("运营部", "ops"),          # 职能
    ("合规部", "compliance"),   # 职能
]


def ask(prompt, default=""):
    v = input(f"  {prompt}" + (f" [{default}]" if default else "") + ": ").strip()
    return v or default


def line():
    print("─" * 56)


def main():
    print("\n════════ Agent-Staff 配置向导 ════════")
    print("⚠️ 先去飞书后台建好自建应用(每部门一个 bot + 一个数据应用),见 docs/飞书接入指南.md。\n")

    # 1. 数据应用(codata 读写表/文件,需 bitable + drive 权限)
    line(); print("【1/4】数据应用(给 codata 读写多维表格 / 文件用)")
    data_id = ask("数据应用 App ID(cli_...)")
    data_secret = ask("数据应用 App Secret")
    with open(CRED, "w", encoding="utf-8") as f:
        f.write(f"FEISHU_APP_ID={data_id}\nFEISHU_APP_SECRET={data_secret}\n")
    print(f"  ✓ 写入 {CRED}(已 gitignore,不会提交)")

    # 2. 建部门表
    line(); print("【2/4】建部门多维表格(完整 9 部门公司:CEO + 营收/职能各部门)")
    if ask("现在自动建表?(y/n)", "y").lower().startswith("y"):
        r = subprocess.run([sys.executable, os.path.join(HERE, "provision.py")])
        if r.returncode != 0:
            print("  ⚠️ 建表似乎失败(查上面报错:多半是数据应用权限/发布没到位)。可修好后重跑本向导。")
    else:
        print("  跳过(稍后:python3 agent-os/scripts/provision.py)")

    # 3. 模型
    line(); print("【3/4】选模型(订阅 / API key 都行)")
    print("  1) Claude(订阅或 API)   2) DeepSeek   3) 其他 OpenAI 兼容(Minimax / Qwen / GLM…)")
    c = ask("选哪个(1/2/3)", "1")
    if c == "2":
        ptype, alias, kind, uri = "deepseek", "main", "openai-compatible", "https://api.deepseek.com/v1"
        model = ask("模型 ID", "deepseek-chat")
    elif c == "3":
        ptype = ask("provider 名(小写,如 minimax)", "minimax")
        alias, kind = "main", "openai-compatible"
        uri = ask("OpenAI 兼容端点 uri")
        model = ask("模型 ID")
    else:
        ptype, alias, kind, uri = "anthropic", "main", "", ""
        model = ask("模型 ID", "claude-opus-4-8")
    key = ask("模型凭证(Claude 订阅 token / API key / DeepSeek key…)")
    mp = f"{ptype}.{alias}"

    # 4. 各部门 bot 凭证 + 你的 open_id
    line(); print("【4/4】各部门 bot 凭证 + 你的 open_id")
    print("  内置 9 个部门。某部门【bot App ID 留空 = 跳过它】,只配你要的即可。")
    print("  open_id = 你在『那个 bot 眼里』的身份(每 bot 不同)。没有就留空——")
    print("  留空 = 暂时谁都能 @(方便先跑通);之后跑 onboard.py 收紧到只有你。")
    depts = []
    any_open = False
    for dept, al in DEPTS:
        print(f"\n  ── {dept}(agent: {al})──")
        app_id = ask("bot App ID(cli_...,不用这个部门就留空跳过)")
        if not app_id:
            print("  ↳ 跳过(没填 bot)")
            continue
        oid = ask("你的 open_id(ou_...,可留空)", "")
        any_open = any_open or bool(oid)
        depts.append({"dept": dept, "alias": al,
                      "app_id": app_id,
                      "app_secret": ask("bot App Secret"),
                      "open_id": oid})
    if not depts:
        print("\n  ⚠️ 一个 bot 都没填 → config 里不会有任何 agent。至少配一个部门(通常先配 公司/CEO)。")

    # 生成 config.toml
    cfg = gen_config(ptype, alias, kind, uri, model, key, mp, depts)
    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    with open(CONFIG, "w", encoding="utf-8") as f:
        f.write(cfg)

    line(); print(f"✅ 已生成 {CONFIG}")
    print("\n下一步:")
    print("  bash 启动.sh        # 常驻 + 可在飞书 @")
    if not any_open:
        print("\n⚠️ 你没填 open_id → 现在是『谁都能 @』。跑通后务必收紧:")
        print("  把 bot 拉进部门群 → python3 agent-os/scripts/onboard.py <你的飞书显示名> <alias> 老板")
    print("\n💡 模型凭证是明文写进 config.toml(已 gitignore)。想更安全/用订阅:")
    print("  `zeroclaw auth paste-token`(Claude 订阅)/ `auth login`(OAuth),让 zeroclaw 加密托管。")


def gen_config(ptype, alias, kind, uri, model, key, mp, depts, pybin=None):
    pybin = pybin or sys.executable  # 用当前 python(不写死 /usr/bin/python3,跨 mac/linux/brew)
    L = ["# 本文件由 setup_wizard.py 生成。改部门/模型可重跑向导,或手动编辑。",
         "schema_version = 3", "", "[memory]", 'search_mode = "bm25"', "",
         "[heartbeat]", "enabled = false", 'agent = "ceo"', "interval_minutes = 60", "",
         "[risk_profiles.standard]", 'level = "full"', ""]
    # 模型 provider
    L.append(f"[providers.models.{ptype}.{alias}]")
    if kind:
        L.append(f'kind = "{kind}"')
    if uri:
        L.append(f'uri = "{uri}"')
    L += [f'model = "{model}"', f'api_key = "{key}"', ""]
    # agents
    for d in depts:
        al = d["alias"]
        L += [f"[agents.{al}]", "enabled = true", "delegate_same_risk_profile = true",
              f'model_provider = "{mp}"', f'mcp_bundles = ["{al}"]', 'risk_profile = "standard"',
              f'channels = ["lark.{al}", "feishu.{al}"]', "",
              f"[agents.{al}.memory]", 'backend = "sqlite"', "",
              f"[agents.{al}.identity]", 'format = "openclaw"', ""]
    # codata MCP(每部门一个)
    for d in depts:
        al = d["alias"]
        L += ["[[mcp.servers]]", f'name = "codata_{al}"', 'transport = "stdio"',
              f'command = "{pybin}"',
              f'args = ["{MCP}", "--dept", "{d["dept"]}"]', ""]
    for d in depts:
        al = d["alias"]
        L += [f"[mcp_bundles.{al}]", f'servers = ["codata_{al}"]', ""]
    # 渠道 + 白名单
    for d in depts:
        al = d["alias"]
        peers = f'"{d["open_id"]}"' if d["open_id"] else '"*"'   # 没填 open_id → 占位;见下方注释
        L += [f"[channels.lark.{al}]", f'app_id = "{d["app_id"]}"', f'app_secret = "{d["app_secret"]}"',
              "use_feishu = true", 'receive_mode = "websocket"', "enabled = true", "",
              f"[peer_groups.{al}]", f'channel = "lark.{al}"', f'agents = ["{al}"]',
              # ⚠️群里 @ 时发送方是【群 chat_id】不是 open_id → 建好群后跑 scripts/list_chats.py 拿 chat_id 填这里
              f"external_peers = [{peers}]  # 群场景必填群 chat_id(oc_...);私聊才用 open_id(ou_...)", ""]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
