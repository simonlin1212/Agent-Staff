<p align="center"><a href="README.md">简体中文</a> | <b>English</b></p>

<div align="center">

# Agent-Staff · Agentify Your Whole Company

**You're the CEO. Staff your company with AI.** Mirror your real **org chart**: put an AI agent in every department (Business / Finance / HR / Admin / Ops / Compliance…), with a **chief-of-staff** agent on top that aggregates across them and helps you run the business. They live in your Feishu/Lark, work in parallel, and handle the whole operation of running a company — bookkeeping, cross-department reports, proactive alerts, and management decisions.

*把你的公司,整个 Agent 化。*

[English (current)](README_en.md) · **[简体中文](README.md)**

![license](https://img.shields.io/badge/license-MIT-green) ![python](https://img.shields.io/badge/python-3.9+-blue) ![feishu](https://img.shields.io/badge/data-Feishu%20Bitable-1E88E5) ![architecture](https://img.shields.io/badge/org%20chart-one%20agent%20per%20dept-orange) ![dogfood](https://img.shields.io/badge/dogfood-used%20daily%20by%20author-success) ![models](https://img.shields.io/badge/models-Claude%20·%20DeepSeek%20·%20Minimax-blue)

</div>

---

> **Other AI tools give you one assistant. Agent-Staff gives you a whole company — staffed, department by department.**

## What this is

Agent-Staff isn't "a few agents that help with some ops work." It turns your **entire company org chart into agents**:

**For each real department in your company, you embed an AI agent — and a chief-of-staff agent sits on top and runs the business across all of them.** You (the human CEO) stay on top making the calls. Underneath is an always-on team of AI staff, each owning its department, working in parallel — all living inside **Feishu/Lark**, with Feishu Bitable as the shared data store:

```
                       You = CEO (human · makes the calls)
                                │
                  ┌─────────────┴─────────────┐
                  │   Chief-of-Staff · agent    │   cross-dept rollup · P&L · decisions
                  └─────────────┬─────────────┘
                                │  runs each department below (one AI agent each · in parallel)
   ┌────────────────────────────┴────────────────────────────┐
   │  Revenue     📱 Media    🛒 E-commerce    💼 Business       │
   │  Functions   💰 Finance  👥 HR   🗂 Admin   📊 Ops   🛡 Compliance │
   └────────────────────────────┬────────────────────────────┘
                                │
     Feishu Bitable = per-dept data store + shared files + chat shell (you @ it)
```

This isn't automating a handful of tasks. It's giving your company an AI operating layer: your org structure, copied in; an agent on watch in each department; a chief-of-staff that closes the books across departments and sees the whole business clearly. You and your team keep doing the core work. **Everything it takes to run the company — the revenue lines (media, e-commerce, business) and the functions (finance, HR, admin, ops, compliance) — this AI staff runs it, watches it, and reports back to you.**

> 🐕 **Dogfood** — the author's own company runs on it every day, on real data. Not a toy.
> 🧩 **Built around your company** — a generic framework; set up departments to match your real org chart. No industry lock-in.

## Department roster (build it to match your company)

One department = one agent = one Feishu Bitable + **its own file space** + a persona + **its own access wall**. The open-source build ships a **complete 9-department company** (below), running out of the box:

| Department agent | What it owns |
|---|---|
| 🏛 **Chief-of-Staff** | Rolls up a cross-department report; computes the **P&L / bottom line** (net take across businesses, net profit); flags anomalies and supports decisions. **Only it sees across departments** (each dept agent sees only its own — isolated by structure) |
| 📱 **Media** · revenue | Per-platform content / views / follower-growth / monetization ledger; log an entry from one line in chat; content reports |
| 🛒 **E-commerce** · revenue | Store orders / GMV / refunds / net-profit ledger |
| 💼 **Business** · revenue | Clients / contracts / collections; log signings and payments by voice; business reports |
| 💰 **Finance** · function | P&L, net profit, operating expenses; attach invoices / contracts as evidence, auditable |
| 👥 **HR** · function | Roster, payroll, attendance; also the **identity backbone** for access control (who may talk to which department) |
| 🗂 **Admin** · function | Contract / license expiry reminders (cron nudges you to renew), external records |
| 📊 **Ops** · function | Day-to-day metric monitoring; runs analysis on a schedule, pushes anomalies to the group |
| 🛡 **Compliance** · function | Policy / red-line checks, audit trail of every action |

> **All 9 departments are built in and runnable**: one `provision.py` creates every Feishu table, `seed_demo_data.py` fills generic sample data, and `@` gives you content immediately. **Delete the ones you don't need, or add more from the same template** (edit `dept_registry` + `config`) — the framework puts no cap on department count. Cut it to your real org chart.

## The department wall: who can ask, who can see — locked on two axes

The isolation a real company needs is **built in** — not a software filter bolted on afterward, but separation by structure:

- **Who can talk to which department agent** — locked by a Feishu identity allowlist (DMs and groups). Someone in the Finance group can't reach the HR agent; when an employee leaves, `offboard.py` revokes their access across every department in one command.
- **Departments can't see each other** — each department agent reads only its own Base (**structural isolation, not a software filter**). Business can't see Finance; Finance can't see HR payroll. **Only the chief-of-staff aggregates across departments.**
- **Each department has its own file space** — a dedicated Feishu storage space per department; the agent only reaches its own department's files (contracts / invoices / reports), reading PDFs, OCR scans, and native Feishu docs. Files are isolated too.

## It lives inside Feishu = it embeds in your workflow

Agent-Staff **isn't a separate system** — it lives **inside Feishu**: the data is Feishu Bitable, the entry point is @-ing in a Feishu group. So it shares the same foundation as the Feishu suite your company already runs — attendance, approvals, finance, docs, calendar.

The AI staff and your human team work in the **same Feishu**, so data and processes connect naturally: attendance / approval / reimbursement data can flow into a department's Base, the AI's reports move through your work groups, and access is tied to Feishu identity. **Real "agentifying your company" isn't making your staff learn a new tool — it's folding AI into the workflow you already run.**

## What it looks like (running in real Feishu, not a mockup)

**① A department agent produces a P&L** — @ Finance in the department group; it reads its ledger and computes the statement (revenue − expenses = net profit), then explains the bottom line in a few lines:

![Finance P&L](docs/images/demo-2-finance-record.png)

**② @ the chief-of-staff and in seconds it aggregates a cross-department report — and you can drill in** (real screen recording below). It first returns a company-wide report (per-department headlines + the books + "things to watch"); ask it to "break out business and collections" and it returns line-by-line detail plus cross-analysis (real vs. paper receivables):

![CEO business report](docs/images/demo-1-ceo-report.gif)

> Both are real recordings/screenshots on **generic sample data** (not mockups). Your business data stays in your own Feishu — it never touches a third party.

## What it does for you (deliverables, not chat)

| Capability | Detail |
|---|---|
| 🏢 **Org chart, agentified** | Build departments to match a real company; one agent per department, each owning its area, all in parallel; **chief-of-staff aggregates the business across departments in real time** |
| 🗣️ **Voice bookkeeping** | Say a result in the group → it's logged into the right department's Feishu Bitable ledger (returns a record_id); **works out of the box** |
| 📊 **Cross-department reports** | One Feishu Bitable per department as the base; read data + `analyze` for a rolled-up report, drill down to detail. **Want to pull external data (quotes / stars / traffic)? Write one `analyze` function** |
| 💰 **P&L / bottom line** | Chief-of-staff turns per-business take, operating expenses, and headcount cost into net profit (math in code, only real numbers reported) |
| 📁 **Reads files** | Reads files in a department's storage: PDF text extraction, image / scan OCR, native Feishu docs |
| 🧾 **Evidence / audit trail** | Attach evidence (invoice / contract / screenshot) to a record, traceable; every tool call is logged |
| ⏰ **Proactive alerts** | cron runs analysis on a schedule and pushes anomalies to the group — **you don't have to keep watching or asking** |
| 🔒 **Per-person access** | Who may talk to which department agent is locked by a Feishu identity allowlist (both DMs and groups); `onboard.py` / `offboard.py` set / clear it in one shot |
| 💾 **Your data, yours** | Everything lives in your own Feishu Bitable; export all department data to JSON in one command |
| 🧠 **Model-agnostic** | Subscription or API key; Claude (tested) / DeepSeek / Minimax / Qwen / GLM / Ollama (should work); Feishu in China, Lark overseas |

## What it is NOT

- **Not a chatbot** — it's an AI staff built to your org chart, with a division of labor, running in parallel, producing real deliverables (bookkeeping / reports / P&L / alerts).
- **Not a toy you keep prompting** — always on, and proactive on a schedule; it watches, computes, and reports even when you say nothing.
- **Not yet another web dashboard** — it lives in the Feishu your team already uses. Zero learning curve for staff.
- **It doesn't do your core production** (writing code / making content / building product is you and your team) — it takes over **everything it takes to run the company**, swapping manual operations for AI.

## The one rule (core architecture)

> **Core production is yours. Running the company is Agent-Staff's.**

- **You and your team = core production**: write code / make content / talk to customers / ship product. Unchanged, not a single line.
- **Agent-Staff = your company's AI operating staff**: revenue (Media / E-commerce / Business) + functions (Finance / HR / Admin / Ops / Compliance), each with an agent on watch, chief-of-staff on top — **from bookkeeping to P&L, from alerts to decision support, it runs the whole thing**.
- **The bridge = Feishu Bitable + spoken reporting**: you say a result → the department agent logs it → the chief-of-staff aggregates a cross-department report.

```
┌──────────────────────────────────────────────────────┐
│  You and your team = core production                  │  ← unchanged, not one line
│  code · content · customers · product                 │
└──────────────────────────────────────────────────────┘
                      │ results (just say them)
                      ▼
┌──────────────────────────────────────────────────────┐
│  Agent-Staff = your company's AI operating staff       │  ← it runs the company
│  🏛 Chief-of-Staff + Revenue(Media·Ecom·Biz)          │
│                    + Functions(Fin·HR·Admin·Ops·Cmpl)  │
│  one agent per dept · parallel · chief aggregates all  │
└──────────────────────────────────────────────────────┘
                      │ write / read
                      ▼
┌──────────────────────────────────────────────────────┐
│  Feishu Bitable = data store + shared files + chat     │
└──────────────────────────────────────────────────────┘
```

Hard constraint: **the system adapts to your company's org chart and workflow — you never change your workflow for the system.**

## What you can build (example scenarios)

The framework is generic — the department agents above plus Feishu Bitable compose into all kinds of business setups. The author's own company runs these on it (business implementations, stripped out before open-sourcing, but proof the framework holds up):

- **P&L statement** — per-business revenue auto-rolled up − operating expenses − headcount cost → net profit (chief-of-staff closes the books)
- **Contract / license expiry reminders** — Admin runs a cron sweep and nudges you to renew before anything lapses
- **Market / quote monitoring** — Ops writes an `analyze` that pulls an external API (stock price / competitor / site traffic) and pushes to the group on a schedule
- **Evidence archive** — invoices / contracts attached to the right record, traceable
- **Staff roster + payroll** — HR owns the identity backbone; headcount cost feeds the P&L

> To add a department, copy `_analyze_generic` in `agent-os/feishu_mcp.py` as a template, write one `analyze`, and add a row to `dept_registry`.

## Tech stack / design principles

- **Multi-department, always-on, parallel** — one agent per department, up 24/7, @-able in groups, chief aggregates across departments in real time, with cron alerts + heartbeat built in (`install.sh` sets up the underlying runtime for you).
- **Bring your own model (not locked to Claude)** — native support for **Claude (subscription/API) / DeepSeek / Minimax / Qwen / GLM / OpenRouter / local Ollama** and others (OpenAI-compatible). Change one line of `model_provider` in `config.toml` and drop in your key.
  > ⚠️ **The author tested Claude.** DeepSeek/Minimax and friends go through the standard OpenAI-compatible interface — should work, but not individually tested. Feedback welcome.
- **Data store = Feishu Bitable.** The data-access layer is abstracted (`DataStore`), leaving a path to swap the backend. Overseas runs on Lark (same API, one env var).
- **Math in code, judgment to the AI** — sums / tax / FX / dates are computed in Python; the AI only narrates. **It reports only the real numbers a tool returned — never numbers from memory.**
- **codata MCP** (`agent-os/feishu_mcp.py`) — a pure-stdlib, zero-dependency stdio MCP that gives each department agent tools for read data / log entry / report / read files / attach evidence / view audit.

## Quickstart

> `install.sh` sets up every dependency (the agent runtime + PDF/OCR tools) in one go — you don't install them one by one.

### Easiest: three commands (recommended)

```bash
bash install.sh     # installs the runtime + poppler + tesseract (and checks Rust / Python)
bash setup.sh       # wizard: paste credentials → auto-create tables → pick a model → generate config.toml
bash 启动.sh        # runs it; @ in Feishu and go
```

> The one manual step: **create the self-built apps in the Feishu admin console** (one bot per department + one data app). The wizard tells you where to paste the credentials. Step-by-step → [`docs/飞书接入指南.md`](docs/飞书接入指南.md).

### Or fully manual (if you want control of each step)

```bash
# 0. Install the runtime (engine): build from source with channel-lark (brew install protobuf first); see the deploy guide
brew install poppler tesseract                                  # 1. PDF/OCR (Linux: apt install poppler-utils tesseract-ocr)
cp agent-os/.feishu凭证.example agent-os/.feishu凭证.local       # 2. data app_id/secret
python3 agent-os/scripts/provision.py                           # 3. create department Bitables
cp agent-home/config.example.toml agent-home/config.toml        # 4. fill bot credentials + model (see comments)
bash 启动.sh                                                    # 5. start
```

> See [`docs/部署指南.md`](docs/部署指南.md) (with 8 gotchas). *Docs are currently in Chinese — English docs welcome via PR.*

## Feishu / Lark (China and overseas)

The data store is Feishu (China version, data in Beijing). **Overseas, use [Lark](https://www.larksuite.com/)** — the international edition of Feishu (also ByteDance), with an **almost identical API**, data in Singapore.

**Same codebase; overseas changes only two things** (see the last section of the [Feishu access guide](docs/飞书接入指南.md)):
1. Create the app at [open.larksuite.com](https://open.larksuite.com); `lark-cli` is the same tool — add `--brand lark` (nothing extra to install).
2. Set `export LARK_API_BASE=https://open.larksuite.com/open-apis` (defaults to Feishu).

## System dependencies

| Tool | Purpose | Install |
|---|---|---|
| **runtime** | keeps agents alive / group @ / cron alerts | `install.sh` sets it up (built on the open-source [zeroclaw](https://github.com/zeroclaw-labs/zeroclaw) engine) |
| **poppler** | PDF parsing (`pdftotext` / `pdftoppm`) | `brew install poppler` / `apt install poppler-utils` |
| **tesseract** | image / scan OCR | `brew install tesseract` / `apt install tesseract-ocr`; **for Chinese**, install the `chi_sim` pack and set `export LARK_OCR_LANG=eng+chi_sim` |
| **Python 3.9+** | codata (pure stdlib, no pip deps) | ships with the OS |
| **lark-cli** (optional) | only to read native Feishu docs (docx/wiki); not needed for PDF/image/listing files | `npm install -g @larksuite/cli` (official) |

> Tools are found on PATH with an install hint if missing — cross-platform (macOS / Linux), no hardcoded paths.
> **How to create the Feishu apps (required, manual) → [`docs/飞书接入指南.md`](docs/飞书接入指南.md)**

## Docs

| Doc | Content |
|---|---|
| [架构.md](docs/架构.md) | Three-layer architecture (brain / abacus / store) + data flow + department roster |
| [部署指南.md](docs/部署指南.md) | Deploy steps + **8 gotchas** (single Feishu long-connection / daemon carries cron / no Chinese TOML keys / sandbox…) |
| [飞书接入指南.md](docs/飞书接入指南.md) | Step-by-step to create Feishu apps + lark-cli + overseas Lark |

> Docs are currently in Chinese. English translations are welcome — open a PR.

## Dependencies & credits

Agent-Staff is **built on top of** these projects (dependency + credit, **not a reskin/rename**). Thanks to:

- **[zeroclaw](https://github.com/zeroclaw-labs/zeroclaw)** (MIT + Apache 2.0) — the underlying agent runtime engine, by ZeroClaw Labs. Agent-Staff depends on it, doesn't modify it, doesn't reskin it (`install.sh` installs it).
- **Feishu / [Lark](https://www.larksuite.com/)** (ByteDance) — data store (Bitable) + chat shell.
- **poppler / tesseract** — PDF parsing / OCR.

## Status

Early · the author's own dogfood (used daily, real data). Issues / PRs welcome.

---

## Support

If this tool saved you time, a coffee is appreciated ☕

<p align="center">
  <a href="https://buymeacoffee.com/simonlin1212"><img src="./assets/bmc-qr.png" width="180" alt="Buy Me a Coffee"></a>
</p>

---

## License

[MIT](LICENSE) · the zeroclaw dependency is MIT + Apache 2.0 (see its repo).
