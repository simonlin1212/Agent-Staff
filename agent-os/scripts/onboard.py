#!/usr/bin/env python3
"""入职配权限(解决 per-app open_id 映射):
新成员先被拉进其【部门飞书群】,再跑这个 —— 列出该部门 bot 所在群的成员 → 按姓名匹配拿
「该 bot 视角」的 open_id(per-app,每个 bot 看同一人 id 都不同)→ 加进该 agent 的
external_peers 白名单。配套 offboard.py(离职清权限)。

用法:
  python3 onboard.py <姓名> <部门alias> [--dry-run] [--config <config.toml>]
  部门alias = 你 config 里 [channels.lark.X] 的 X(默认 ceo / sales / finance)
改完要重启 启动.sh 才生效。
"""
import sys
import os
import re
import json
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
AOS = os.path.dirname(HERE)
LARK_BASE = os.environ.get("LARK_API_BASE", "https://open.feishu.cn/open-apis")  # 海外 Lark:设 LARK_API_BASE=https://open.larksuite.com/open-apis
CONFIG_DEFAULT = os.path.join(os.path.dirname(AOS), "agent-home", "config.toml")


def bot_creds(text, alias):
    """从 config 抠 [channels.lark.<alias>] 的 app_id + app_secret。"""
    in_sec, aid, sec = False, None, None
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("[channels.lark."):
            in_sec = (s == f"[channels.lark.{alias}]")
        elif s.startswith("["):
            in_sec = False
        if in_sec:
            m = re.match(r'app_id\s*=\s*"([^"]+)"', s)
            aid = m.group(1) if m else aid
            m = re.match(r'app_secret\s*=\s*"([^"]+)"', s)
            sec = m.group(1) if m else sec
    return aid, sec


def add_peer(text, alias, open_id):
    """把 open_id 加进 [peer_groups.<alias>] 的 external_peers。返回(新文本, 是否新增)。"""
    out, cur, added = [], None, False
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("[peer_groups."):
            cur = s[len("[peer_groups."):-1]
        elif s.startswith("["):
            cur = None
        if cur == alias and s.startswith("external_peers"):
            ids = re.findall(r'"(ou_[A-Za-z0-9]+)"', line)
            if open_id not in ids:
                ids.append(open_id)
                added = True
            indent = line[:len(line) - len(line.lstrip())]
            out.append(indent + "external_peers = [" + ", ".join(f'"{i}"' for i in ids) + "]")
            continue
        out.append(line)
    return "\n".join(out), added


def find_openid(aid, sec, name):
    """用 bot 自己的凭证:列它所在群 → 群成员里按姓名匹配 → 拿该 bot 视角 open_id。"""
    tok = json.load(urllib.request.urlopen(urllib.request.Request(
        LARK_BASE + "/auth/v3/tenant_access_token/internal/",
        data=json.dumps({"app_id": aid, "app_secret": sec}).encode(),
        headers={"Content-Type": "application/json"}), timeout=20))["tenant_access_token"]

    def get(url):
        return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": "Bearer " + tok}), timeout=20))

    chats = (get(LARK_BASE + "/im/v1/chats?page_size=20").get("data") or {}).get("items", [])
    for c in chats:
        mem = (get(LARK_BASE + f"/im/v1/chats/{c['chat_id']}/members?page_size=100&member_id_type=open_id").get("data") or {}).get("items", [])
        for mm in mem:
            if mm.get("name") == name:
                return mm.get("member_id"), c.get("name")
    return None, None


def main():
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    config = sys.argv[sys.argv.index("--config") + 1] if "--config" in sys.argv else CONFIG_DEFAULT
    if len(pos) < 2:
        print("用法: onboard.py <姓名> <部门alias> [--dry-run]\n  alias = 你 config 里 [channels.lark.X] 的 X(默认 ceo/sales/finance)")
        return
    name, alias = pos[0], pos[1]

    text = open(config, encoding="utf-8").read()
    aid, sec = bot_creds(text, alias)
    if not aid:
        print(f"❌ config 里没有 [channels.lark.{alias}]。alias 要对上你 config 里的部门。")
        return
    oid, chat = find_openid(aid, sec, name)
    if not oid:
        print(f"❌ {alias}-bot 的群里没找到成员「{name}」。先把 ta 拉进该部门群,再跑本脚本。")
        return
    print(f"找到「{name}」@群「{chat}」→ {alias}-bot 视角 OpenID={oid[:16]}..")

    new, added = add_peer(text, alias, oid)
    if added:
        if not dry:
            open(config, "w", encoding="utf-8").write(new)
        print(f"  ✓ 加进 [peer_groups.{alias}] 白名单" + ("(⚠️ 重启 启动.sh 才生效)" if not dry else " [dry-run 未改动]"))
    else:
        print("  已在白名单,无需加")


if __name__ == "__main__":
    main()
