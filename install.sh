#!/bin/bash
# ════════════════════════════════════════════════════════
#  Agent-Staff · 一键装引擎 + 工具
#  用法: bash install.sh   →  装好后跑 bash setup.sh
#  关键依赖装不上会明确报错退出(不会装一半让你后面一脸懵)。
# ════════════════════════════════════════════════════════
set -uo pipefail

# zeroclaw pin 到已验证的 commit(v0.8.2);它没发 tag,pin commit 最稳,避免 main 漂移 break。
# 想升级:改这里,自测通过再提交。
ZEROCLAW_REPO="https://github.com/zeroclaw-labs/zeroclaw"
ZEROCLAW_REV="be5f17c"

OS="$(uname -s)"
have() { command -v "$1" >/dev/null 2>&1; }
say()  { printf "\n\033[1m%s\033[0m\n" "$1"; }
ok()   { printf "  \xE2\x9C\x93 %s\n" "$1"; }
warn() { printf "  [!] %s\n" "$1"; }
die()  { printf "\n[X] %s\n" "$1" >&2; exit 1; }

pkg() {  # $1=brew包 $2=apt包  → 返回安装退出码
  if [ "$OS" = "Darwin" ]; then brew install "$1"
  elif have apt-get; then sudo apt-get install -y "$2"
  else warn "未知系统,请手动装 $1 / $2"; return 1; fi
}

say "Agent-Staff 安装 —— 系统: $OS"
[ "$OS" = "Darwin" ] && ! have brew && die "请先装 Homebrew: https://brew.sh"

# ① PDF / OCR —— 非核心(没装只是读不了 PDF/OCR,核心记账/汇总照常)→ 失败 warn 不退出
say "① PDF / OCR(poppler + tesseract)· 文件读取功能用"
have pdftotext && ok "poppler 已装" || { echo "  装 poppler…"; pkg poppler poppler-utils && ok poppler || warn "poppler 没装上(只影响读 PDF)"; }
have tesseract && ok "tesseract 已装" || { echo "  装 tesseract…"; pkg tesseract tesseract-ocr && ok tesseract || warn "tesseract 没装上(只影响 OCR)"; }

# ② Python —— 核心(codata 必需)→ 缺则退出
say "② Python 3.9+ · codata 必需"
have python3 && ok "python3: $(python3 --version 2>&1)" || die "没装 python3(codata 必需)。请先装 Python 3.9+ 再重跑。"

# ③ Rust / cargo —— 编 zeroclaw 必需 → 失败退出
say "③ Rust / cargo · 编 zeroclaw 必需"
if have cargo; then ok "cargo 已装"; else
  echo "  装 Rust(rustup)…"
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y || die "Rust 安装失败(查网络;国内可换 rsproxy 镜像)。"
  # shellcheck disable=SC1091
  . "$HOME/.cargo/env" 2>/dev/null || true
  have cargo || die "Rust 装了但当前 shell 找不到 cargo。请重开终端(或 source ~/.cargo/env)后重跑本脚本。"
  ok "Rust"
fi

# ④ protobuf —— 编 zeroclaw 飞书渠道必需
say "④ protobuf · zeroclaw channel-lark 编译必需"
have protoc && ok "protoc 已装" || { echo "  装 protobuf…"; pkg protobuf protobuf-compiler && ok protobuf || warn "protobuf 没装上 → 下一步 zeroclaw 编译可能失败"; }

# ⑤ zeroclaw —— 核心运行时,失败即退出(别装一半)
say "⑤ zeroclaw(运行时引擎)· pin @ $ZEROCLAW_REV"
if have zeroclaw; then
  ok "zeroclaw 已装: $(zeroclaw --version 2>&1 | head -1)"
else
  echo "  从源码编 zeroclaw(带飞书渠道,约 5-15 分钟,请耐心)…"
  if cargo install --git "$ZEROCLAW_REPO" --rev "$ZEROCLAW_REV" --features channel-lark --locked; then
    ok "zeroclaw"
  else
    die "zeroclaw 编译失败。常见原因:protobuf 没装 / 网络(国内换 crates 镜像)/ Rust 太旧(rustup update)。
   手动装见 $ZEROCLAW_REPO(务必带 --features channel-lark)。"
  fi
fi

# ⑥ lark-cli —— 可选(读飞书原生文档时用)
say "⑥ lark-cli(可选 · 读飞书 docx/wiki 时用)"
have lark-cli && ok "lark-cli 已装" || warn "可选,需要时: npm install -g @larksuite/cli"

say "完成 ✅  下一步:"
echo "  bash setup.sh        # 交互配置:填凭证 → 建表 → 选模型 → 生成 config → 启动"
echo "  国内装得慢就换镜像(brew/cargo/pip/npm 国内源,见 README 系统依赖)"
