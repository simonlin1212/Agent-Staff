#!/bin/bash
# ════════════════════════════════════════════════════════
#  Agent-Staff · 交互配置向导入口
#  用法: bash setup.sh
#  前提:先跑过 `bash install.sh` 装好 zeroclaw + 工具,
#       并在飞书后台建好自建应用(见 docs/飞书接入指南.md)。
# ════════════════════════════════════════════════════════
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "配置前，请确认两个前提都已完成："
echo "  ① 已跑 bash install.sh 装好 zeroclaw + poppler/tesseract"
echo "  ② 已在飞书后台建好【自建应用】(1 个数据应用 + 每部门 1 个 bot),见 docs/飞书接入指南.md"
printf "都完成了吗？(y/N) "
read -r REPLY
case "$REPLY" in
  [Yy]*) ;;
  *) echo "先完成上面两步再来。飞书建应用保姆级步骤 → docs/飞书接入指南.md"; exit 1 ;;
esac

exec python3 "$HERE/agent-os/scripts/setup_wizard.py"
