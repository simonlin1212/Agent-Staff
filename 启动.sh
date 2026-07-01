#!/bin/bash
# ════════════════════════════════════════════════════════
#  Agent-Staff · zeroclaw 启动 / 重启脚本
#  用法: bash 启动.sh
#  改了 feishu_mcp.py / 人设 / config.toml 后,跑一遍就生效。
# ════════════════════════════════════════════════════════

# 自动定位 agent-home(不写死绝对路径,clone 到哪都能跑)
ZH="$(cd "$(dirname "$0")/agent-home" && pwd)"
BIN="$HOME/.cargo/bin/zeroclaw"
LOG="$HOME/agent-staff.log"
PIDFILE="$ZH/.pid"

echo "停旧进程(只停本实例,不误杀你其它 zeroclaw)…"
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE" 2>/dev/null)" 2>/dev/null; then
  kill "$(cat "$PIDFILE")" 2>/dev/null            # 精准:按 PID 文件只停本 agent-home 的实例
else
  pkill -f "zeroclaw.*--config-dir $ZH.*daemon" 2>/dev/null   # 兜底:只匹配本 config-dir 的 daemon
fi
sleep 5

# ⚠️ daemon 模式 = 全家桶(gateway + 所有渠道 + 心跳 + cron 调度器)。
#    channel start 不带 cron 调度器!要主动预警(cron)必须 daemon。
#    nohup:扛 SSH 断开 + 关机(不扛重启,重启后再跑一遍即可)。
echo "启动 zeroclaw daemon(nohup,脱离终端存活;含 cron 调度器)…"
cd "$HOME" && nohup "$BIN" --config-dir "$ZH" daemon --host 127.0.0.1 --log-level info > "$LOG" 2>&1 < /dev/null &
ZPID=$!
disown
echo "$ZPID" > "$PIDFILE"

# ⚠️ 别看 stdout 判断在线(非 TTY 块缓冲常显示空,误导);轮询 ESTABLISHED 连接数,连上就走。
echo "等待连接建立(最多 ~40s)…"
CONN=0
for _ in $(seq 1 40); do
  sleep 1
  kill -0 "$ZPID" 2>/dev/null || { echo "⚠️ 进程已退出,查 $LOG / agent-home/data/state/runtime-trace.jsonl"; exit 1; }
  CONN=$(lsof -nP -p "$ZPID" 2>/dev/null | grep -c ESTABLISHED)
  [ "${CONN:-0}" -ge 2 ] && break
done

echo "已启动 pid=$ZPID  网络连接=$CONN"
if [ "${CONN:-0}" -ge 2 ]; then
  echo "✅ Agent-Staff 在线,飞书可随时 @"
else
  echo "⚠️ 连接数偏低,查 $LOG / agent-home/data/state/runtime-trace.jsonl"
fi
