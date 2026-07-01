#!/usr/bin/env python3
"""列出某部门 bot 所在的群 + chat_id —— 填 `external_peers` 用。

⚠️ 群里 @ agent 时,zeroclaw 看到的发送方是**群 chat_id(oc_...)**,不是你的 open_id(ou_...)。
所以 `[peer_groups.X]` 的 `external_peers` 要填**群 chat_id**(私聊才用 open_id)。跑这个拿它:

    python3 list_chats.py <部门alias> [--members] [--config <config.toml>]
      alias = 你 config 里 [channels.lark.X] 的 X(如 sales / finance / ceo)
      --members   顺带列每个群成员的 open_id(私聊白名单用)

bot 凭证从 config.toml 的 [channels.lark.<alias>] 读(**不在命令行传 secret**,避免 shell history / ps 泄露)。
海外 Lark:先 export LARK_API_BASE=https://open.larksuite.com/open-apis
"""
import sys
import os
import re
import json
import urllib.request as u
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
AOS = os.path.dirname(HERE)
BASE = os.environ.get("LARK_API_BASE", "https://open.feishu.cn/open-apis")
CONFIG_DEFAULT = os.path.join(os.path.dirname(AOS), "agent-home", "config.toml")


def bot_creds(text, alias):
    """从 config 抠 [channels.lark.<alias>] 的 app_id + app_secret(和 onboard.py 同款,不在 CLI 传 secret)。"""
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


def _token(aid, sec):
    body = json.dumps({"app_id": aid, "app_secret": sec}).encode()
    r = json.load(u.urlopen(u.Request(BASE + "/auth/v3/tenant_access_token/internal",
        data=body, headers={"Content-Type": "application/json"})))
    if not r.get("tenant_access_token"):
        raise SystemExit(f"拿 token 失败: {r.get('msg')}(检查 config 里该部门的 app_id / app_secret)")
    return r["tenant_access_token"]


def _get(path, tok):
    return json.load(u.urlopen(u.Request(BASE + path, headers={"Authorization": "Bearer " + tok})))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    show_members = "--members" in sys.argv
    config = sys.argv[sys.argv.index("--config") + 1] if "--config" in sys.argv else CONFIG_DEFAULT
    if not args:
        raise SystemExit("用法: python3 list_chats.py <部门alias> [--members] [--config X]\n  alias = config 里 [channels.lark.X] 的 X")
    alias = args[0]
    aid, sec = bot_creds(open(config, encoding="utf-8").read(), alias)
    if not aid:
        raise SystemExit(f"config 里没有 [channels.lark.{alias}]。alias 要对上你 config 里的部门。")
    tok = _token(aid, sec)
    try:
        chats = (_get("/im/v1/chats?page_size=50", tok).get("data") or {}).get("items") or []
    except urllib.error.HTTPError as e:
        raise SystemExit(f"列群失败 HTTP {e.code}: {e.read().decode()[:150]}"
                         "(这个 app 是否已启用「机器人」应用能力?)")
    if not chats:
        print(f"{alias}-bot 还没在任何群里。先在飞书把它拉进部门群,再跑一次。")
        return
    print(f"{alias}-bot 在 {len(chats)} 个群:\n")
    for c in chats:
        print(f"  群「{c.get('name')}」")
        print(f"    chat_id = {c.get('chat_id')}   ← 填进 [peer_groups.{alias}] 的 external_peers")
        if show_members:
            m = (_get(f"/im/v1/chats/{c['chat_id']}/members?member_id_type=open_id&page_size=50", tok)
                 .get("data") or {}).get("items") or []
            for x in m:
                if str(x.get("member_id", "")).startswith("ou_"):
                    print(f"    成员 {x.get('name')} open_id = {x.get('member_id')}")
        print()


if __name__ == "__main__":
    main()
