#!/usr/bin/env python3
"""离职清权限:把某成员从各 agent 白名单(external_peers)里移出。
逐个部门 bot 用「该 bot 视角」查此人 open_id(per-app)→ 从对应 [peer_groups.X] 移除。
补上「离职成员还能 @ agent 灌数据」的漏洞。配套 onboard.py(入职配权限)。

用法:
  python3 offboard.py <姓名> [--dry-run] [--config <config.toml>]
改完要重启 启动.sh 才生效。
"""
import sys
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
AOS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from onboard import bot_creds, find_openid  # noqa: E402  复用:抠凭证 + 按 bot 视角查 open_id

CONFIG_DEFAULT = os.path.join(os.path.dirname(AOS), "agent-home", "config.toml")


def list_aliases(text):
    """列出 config 里所有 [channels.lark.X] 的 X。"""
    return re.findall(r'^\s*\[channels\.lark\.([^\]]+)\]', text, re.M)


def remove_peer_all(text, open_id):
    """从所有 [peer_groups.X] 的 external_peers 移除 open_id(per-app id 只会命中其所属 bot 那一组)。
    返回(新文本, 被移除的部门 alias 列表)。"""
    out, removed, cur = [], [], None
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("[peer_groups."):
            cur = s[len("[peer_groups."):-1]
        elif s.startswith("["):
            cur = None
        if cur and s.startswith("external_peers"):
            ids = re.findall(r'"(ou_[A-Za-z0-9]+)"', line)
            if open_id in ids:
                ids = [i for i in ids if i != open_id]
                removed.append(cur)
                indent = line[:len(line) - len(line.lstrip())]
                out.append(indent + "external_peers = [" + ", ".join(f'"{i}"' for i in ids) + "]")
                continue
        out.append(line)
    return "\n".join(out), removed


def main():
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    config = sys.argv[sys.argv.index("--config") + 1] if "--config" in sys.argv else CONFIG_DEFAULT
    if not pos:
        print("用法: offboard.py <姓名> [--dry-run] [--config X]")
        return
    name = pos[0]

    text = open(config, encoding="utf-8").read()
    removed_all = []
    for alias in list_aliases(text):
        aid, sec = bot_creds(text, alias)
        if not aid:
            continue
        oid, _ = find_openid(aid, sec, name)   # 该 bot 视角查此人
        if not oid:
            continue
        text, removed = remove_peer_all(text, oid)
        for r in removed:
            print(f"  ✓ 从 [peer_groups.{r}] 白名单移除「{name}」({oid[:16]}..)")
        removed_all += removed

    if not removed_all:
        print(f"「{name}」不在任何部门白名单(或没被其部门 bot 看到,可能未 onboard)。")
        return
    if not dry:
        open(config, "w", encoding="utf-8").write(text)
        print(f"✓ config 已改,移除 {removed_all}(⚠️ 重启 启动.sh 才生效)")
    else:
        print(f"[dry-run] 将移除 {removed_all}(未改动)")


if __name__ == "__main__":
    main()
