#!/usr/bin/env python3
"""codata MCP (Agent-Staff) · stdlib 零依赖 · stdio JSON-RPC · 部门感知 · 通用版。

用法:feishu_mcp.py --dept <部门名>   (部门名见 dept_registry.json;CEO 用"公司"=合并全部门)

设计:参谋层"只追踪不汇报",数据靠"动嘴汇报→记账"进来。
- get_company_data:读本部门表 → 返回 每表字段 + 记录 + 自动汇总(数值求和/计数/最新)。日期统一转 YYYY-MM-DD。CEO 合并全部门。
- log_record:把你汇报的成绩写进对应表(按字段类型转:日期 YYYY-MM-DD→飞书时间戳、数字→number)。
- list_files / read_file:读本部门存储空间文件。
原则:算数交代码(求和/日期在 Python 算),判断交 LLM。
"""
import sys, os, json, re, subprocess, shutil
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# lark-cli(read_file / list_files 用)是 node CLI,确保子进程 PATH 能找到 node + lark-cli
# (Mac Mini 上 codata 进程默认 PATH 不含 /opt/homebrew/bin → lark-cli 报 "env: node: not found")
if "/opt/homebrew/bin" not in os.environ.get("PATH", ""):
    os.environ["PATH"] = "/opt/homebrew/bin:" + os.environ.get("PATH", "")

PROTOCOL = "2025-06-18"
REG_PATH = os.path.join(HERE, "dept_registry.json")
LARK_CLI = shutil.which("lark-cli") or "/opt/homebrew/bin/lark-cli"  # 在 PATH 找;跨平台(没装则 read_file 会给清晰提示,不崩)
LARK_BASE = os.environ.get("LARK_API_BASE", "https://open.feishu.cn/open-apis")  # 海外 Lark:设环境变量 LARK_API_BASE=https://open.larksuite.com/open-apis
DATE_MS_FLOOR = 1_000_000_000_000  # > 此值的数字视为毫秒时间戳(日期);经营指标远小于此


def _dept_arg():
    for i, a in enumerate(sys.argv):
        if a == "--dept" and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


DEPT = _dept_arg() or "公司"


def _registry():
    return json.load(open(REG_PATH, encoding="utf-8"))


def _stores():
    """返回 [(部门名, FeishuDataStore)]:单部门=1个;公司=全部门合并。"""
    from datastore import FeishuDataStore
    reg = _registry()
    if DEPT in reg and DEPT != "公司":
        info = reg[DEPT]
        return [(DEPT, FeishuDataStore(app_token=info["app_token"], tables=info["tables"]))]
    return [(d, FeishuDataStore(app_token=i["app_token"], tables=i["tables"])) for d, i in reg.items()]


def _ymd(v):
    try:
        return datetime.fromtimestamp(int(v) / 1000).strftime("%Y-%m-%d")
    except Exception:
        return v


def _summarize(rows, num_fields, date_fields):
    """通用汇总:计数 + 各数值字段求和 + 日期毫秒→YYYY-MM-DD。按字段类型精确处理(飞书数字常以字符串回传,这里强转)。算数交代码。"""
    clean = []
    for r in rows:
        c = {}
        for k, v in r.items():
            if k == "_record_id":
                continue
            if k in date_fields and isinstance(v, (int, float)) and v >= DATE_MS_FLOOR:
                c[k] = _ymd(v)
            else:
                c[k] = v
        clean.append(c)
    totals = {}
    for r in rows:
        for k in num_fields:
            v = r.get(k)
            try:
                totals[k] = round(totals.get(k, 0) + float(v), 2)
            except (ValueError, TypeError):
                pass
    return {"记录数": len(clean), "合计": {k: v for k, v in totals.items() if v}, "记录": clean}


def _field_names(store, table_name):
    try:
        tid = store.meta["tables"][table_name]
        r = store._api("GET", f"/bitable/v1/apps/{store.app_token}/tables/{tid}/fields?page_size=100")
        return [(f["field_name"], f.get("type")) for f in (r.get("data") or {}).get("items") or []]
    except Exception as e:
        print(f"[codata] _field_names({table_name}) 失败: {e}", file=sys.stderr)  # 不静默:表被删/权限问题留痕
        return []


def _company_data():
    out = {"today": datetime.now().strftime("%Y-%m-%d"), "部门": DEPT, "数据": {}}
    for dept, store in _stores():
        for tname in store.meta["tables"]:
            try:
                rows = store.list_records(tname)
                ft = _field_names(store, tname)
                num_fields = {n for n, t in ft if t == 2}
                date_fields = {n for n, t in ft if t == 5}
                summ = _summarize(rows, num_fields, date_fields)
                summ["字段"] = [n for n, _ in ft]
                key = tname if DEPT != "公司" else f"{dept}·{tname}"
                out["数据"][key] = summ
            except Exception as e:
                out["数据"][tname] = {"错误": str(e)}
    return json.dumps(out, ensure_ascii=False, default=str)


def _log_record(table, data):
    """把一条汇报写进本部门的某张表。data={字段名:值};按字段类型转换。"""
    if DEPT == "公司":
        info = _registry().get("公司")
    else:
        info = _registry().get(DEPT)
    if not info or table not in info["tables"]:
        return json.dumps({"error": f"{DEPT} 没有表「{table}」,可选:{list(info['tables']) if info else []}"}, ensure_ascii=False)
    from datastore import FeishuDataStore
    store = FeishuDataStore(app_token=info["app_token"], tables=info["tables"])
    ftypes = {n: t for n, t in _field_names(store, table)}
    fields = {}
    for k, v in (data or {}).items():
        if k not in ftypes:
            continue  # 跳过不认识的字段,避免飞书报错
        t = ftypes[k]
        if t == 5:  # 日期
            if isinstance(v, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", v.strip()):
                fields[k] = int(datetime.strptime(v.strip(), "%Y-%m-%d").timestamp() * 1000)
            elif isinstance(v, (int, float)):
                fields[k] = int(v)
        elif t == 2:  # 数字
            try:
                fields[k] = float(v)
            except (ValueError, TypeError):
                pass
        else:
            fields[k] = str(v)
    if not fields:
        return json.dumps({"error": "没有可写字段(字段名要和表一致)", "表字段": list(ftypes)}, ensure_ascii=False)
    try:
        recs = store.create_records(table, [fields])
        rid = recs[0].get("record_id") if recs else None
        return json.dumps({"ok": True, "已记入": table, "字段": fields, "record_id": rid,
                           "附依据提示": "要给这笔附凭证/依据:先 list_files 拿文件 token,再 attach_evidence(table, record_id, file_token, file_name)"},
                          ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def _folder_token():
    info = _registry().get(DEPT)
    return info.get("folder_token") if info else None


def _drive_token():
    """公司应用 tenant token(drive API 用,与 Base 同一套凭证)。"""
    from datastore import FeishuDataStore
    info = _registry().get(DEPT) or next(iter(_registry().values()))
    return FeishuDataStore(app_token=info["app_token"], tables=info.get("tables", {})).token()


def _list_files():
    """递归列本部门飞书存储空间的文件(含子文件夹)。直连 drive API(urllib),不依赖 lark-cli/node。"""
    ft = _folder_token()
    if not ft:
        return json.dumps({"error": f"{DEPT} 无存储文件夹"}, ensure_ascii=False)
    import urllib.request as _u, urllib.parse as _up
    tok = _drive_token()

    def ls(folder, depth=0):
        url = LARK_BASE + "/drive/v1/files?" + _up.urlencode({"folder_token": folder, "page_size": 200})
        try:
            d = json.load(_u.urlopen(_u.Request(url, headers={"Authorization": "Bearer " + tok}), timeout=20))
            items = (d.get("data") or {}).get("files") or []
        except Exception as e:
            return [{"error": str(e)[:120]}]
        out = []
        for f in items:
            e = {"name": f.get("name"), "type": f.get("type"), "file_token": f.get("token")}
            if f.get("type") == "folder" and depth < 3:  # 递归钻子文件夹
                e["内含"] = ls(f.get("token"), depth + 1)
            out.append(e)
        return out
    return json.dumps(ls(ft), ensure_ascii=False)


_READ_CAP = 15000  # 返回给 agent 的正文上限(防上下文爆)
# 系统工具依赖(跨平台:在 PATH 里找,不写死路径;开源部署需装 poppler + tesseract)
_OCR_LANG = os.environ.get("LARK_OCR_LANG", "eng")  # 默认英文。读中文:先装 chi_sim 语言包(brew: tesseract-lang / apt: tesseract-ocr-chi-sim),再设环境变量 LARK_OCR_LANG=eng+chi_sim


def _cap(txt):
    return txt[:_READ_CAP] + (f"\n\n…(已截断,正文共 {len(txt)} 字)" if len(txt) > _READ_CAP else "")


def _ocr_image(path):
    tess = shutil.which("tesseract")
    if not tess:
        return None
    p = subprocess.run([tess, path, "-", "-l", _OCR_LANG], capture_output=True, timeout=120)
    return p.stdout.decode("utf-8", "replace").strip()


def _read_file(file_token):
    """读文件正文(跨平台,工具在 PATH 里找):PDF→pdftotext;扫描PDF/图片→tesseract OCR;飞书原生文档→lark-cli。
    依赖系统工具 poppler(pdftotext/pdftoppm)+ tesseract(OCR),没装则返回安装提示(不崩)。"""
    if not file_token:
        return "缺 file_token(先用 list_files 拿)"
    import urllib.request as _u, tempfile, os as _os
    raw = None
    try:
        req = _u.Request(LARK_BASE + f"/drive/v1/files/{file_token}/download",
                         headers={"Authorization": "Bearer " + _drive_token()})
        raw = _u.urlopen(req, timeout=60).read()
    except Exception:
        raw = None
    if raw is None:  # 下载失败 → 多半是飞书原生文档(docx/wiki)→ lark-cli markdown 兜底
        if not (LARK_CLI and _os.path.exists(LARK_CLI)):
            return "无法读取此文件:既非可下载的 PDF/图片,又没装 lark-cli 解析飞书原生文档(docx/wiki)。装:`npm i -g @larksuite/cli`"
        try:
            p = subprocess.run([LARK_CLI, "markdown", "+fetch", "--file-token", file_token, "--as", "bot", "--format", "pretty"],
                               capture_output=True, timeout=30)
            txt = p.stdout.decode("utf-8", "replace").strip()
            return _cap(txt) if txt else "(读取为空,且非可下载文件)"
        except (FileNotFoundError, OSError, subprocess.SubprocessError) as e:
            return f"无法读取(非可下载文件,lark-cli 解析飞书文档也失败:{type(e).__name__})。"
    head = raw[:8]
    is_img = head[:3] == b"\xff\xd8\xff" or head[:8] == b"\x89PNG\r\n\x1a\n" or head[:4] in (b"GIF8", b"RIFF")
    if head[:4] == b"%PDF":
        pdftotext = shutil.which("pdftotext")
        if not pdftotext:
            return "需装 poppler 才能读 PDF:`brew install poppler`(Mac)/`apt install poppler-utils`(Linux)"
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        try:
            tmp.write(raw); tmp.close()
            txt = subprocess.run([pdftotext, "-layout", tmp.name, "-"], capture_output=True, timeout=90).stdout.decode("utf-8", "replace").strip()
            if txt:
                return _cap(txt)
            # 无文字层 = 扫描 PDF → 转图 + OCR(前 8 页)
            ppm = shutil.which("pdftoppm")
            if not (ppm and shutil.which("tesseract")):
                return "这是扫描版 PDF(无文字层),需 OCR——未装 tesseract/poppler:`brew install tesseract poppler`"
            d = tempfile.mkdtemp()
            try:
                subprocess.run([ppm, "-png", "-r", "150", "-f", "1", "-l", "8", tmp.name, _os.path.join(d, "p")], timeout=120)
                texts = [t for t in (_ocr_image(_os.path.join(d, f)) for f in sorted(_os.listdir(d))) if t]
                full = "\n".join(texts)
                return _cap(full) if full else "扫描 PDF 经 OCR 仍未识别出文字(可能太模糊)。"
            finally:
                shutil.rmtree(d, ignore_errors=True)
        finally:
            _os.unlink(tmp.name)
    if is_img:  # 图片 → OCR
        if not shutil.which("tesseract"):
            return "需装 tesseract 才能 OCR 图片:`brew install tesseract`(Mac)/`apt install tesseract-ocr`(Linux)"
        f = tempfile.NamedTemporaryFile(suffix=".img", delete=False)
        try:
            f.write(raw); f.close()
            txt = _ocr_image(f.name)
            return _cap(txt) if txt else "图片 OCR 未识别出文字(可能无文字/太模糊;中文需装 chi_sim 语言包)。"
        finally:
            _os.unlink(f.name)
    return f"已下载({len(raw)} 字节),但不是 PDF/图片(可能 Office 等),当前只解析 PDF 与图片。"


def _num(r, k):
    try:
        return float(r.get(k) or 0)
    except (ValueError, TypeError):
        return 0.0


def _sum_num_fields(rows, ftypes):
    """把每行里「数字类型(type 2)」字段求和。
    ⚠️飞书数字字段常以字符串回传("3000"),故用 float() 强转,而非 isinstance 严判
    (和 _summarize 一致;否则金额永远汇总不出来)。非数字类型/转不动的静默跳过。"""
    sums = {}
    for r in rows:
        for k, v in r.items():
            if k.startswith("_") or ftypes.get(k) != 2:
                continue
            try:
                sums[k] = round(sums.get(k, 0) + float(v), 2)
            except (ValueError, TypeError):
                pass
    return sums


def _analyze_generic(store, dept):
    """通用部门战报:汇总本部门每张表(记录数 + 数值字段求和)。
    这是开源默认实现——按需把它当模板,给自己的部门写专属 analyze。"""
    out = {"部门": dept}
    for tname in store.meta["tables"]:
        try:
            rows = store.list_records(tname)
            ftypes = {n: t for n, t in _field_names(store, tname)}  # 字段类型:只汇总数字(type 2),跳过日期等
        except Exception as e:
            out[tname] = {"error": str(e)[:80]}
            continue
        sums = _sum_num_fields(rows, ftypes)
        out[tname] = {"记录数": len(rows), **({"数值合计": sums} if sums else {})}
    return out


def _analyze_ceo_generic():
    """通用 CEO 聚合:把每个部门的通用汇总拼一起(CEO 是唯一能看全部门的)。"""
    from datastore import FeishuDataStore
    out = {"战报": "全公司聚合"}
    for dept, info in _registry().items():
        if dept == "公司" or not isinstance(info, dict) or "app_token" not in info:
            continue
        try:
            store = FeishuDataStore(app_token=info["app_token"], tables=info.get("tables", {}))
            out[dept] = _analyze_generic(store, dept)
        except Exception as e:
            out[dept] = {"error": str(e)[:80]}
    return out


def _analyze():
    info = _registry().get(DEPT)
    if not info:
        return _company_data()
    if DEPT == "公司":
        return json.dumps(_analyze_ceo_generic(), ensure_ascii=False, default=str)
    from datastore import FeishuDataStore
    store = FeishuDataStore(app_token=info["app_token"], tables=info["tables"])
    return json.dumps(_analyze_generic(store, DEPT), ensure_ascii=False, default=str)

TOOLS = [
    {"name": "get_company_data",
     "description": (f"读【{DEPT}】经营数据:每张表返回 字段/记录数/数值合计/全部记录(日期已转 YYYY-MM-DD,数字已求和)。"
                     "读数一律用本工具,别自己算日期。先看这里有哪些表和字段,再决定 log_record 怎么写。"),
     "inputSchema": {"type": "object", "properties": {}, "required": []}},
    {"name": "analyze",
     "description": (f"出【{DEPT}】战报:已用代码算好的分组汇总/ROI/排名/总览,数字精确(率值用代码算,不会算错)。"
                     "用户问'表现怎样/战报/哪类好/分析一下'时用它,别自己拿原始记录算。"),
     "inputSchema": {"type": "object", "properties": {}, "required": []}},
    {"name": "log_record",
     "description": (f"把你汇报的成绩记进【{DEPT}】台账(动嘴汇报→记账)。"
                     "参数:table=表名(见 get_company_data),data={字段名:值}。"
                     "日期用 \"YYYY-MM-DD\",数字用数字。字段名必须和表一致(不一致的会被忽略)。"),
     "inputSchema": {"type": "object",
                     "properties": {"table": {"type": "string"}, "data": {"type": "object"}},
                     "required": ["table", "data"]}},
    {"name": "attach_evidence",
     "description": (f"给【{DEPT}】某条记录挂依据/凭证(把部门文件夹里的文件附到记录的附件字段=记账留证、凭证归档)。"
                     "流程:先 list_files 拿文件 file_token+name,再调本工具。参数:table=表名,record_id=记录id(log_record 会返回),"
                     "file_token=文件夹里那个文件的token,file_name=文件名。"),
     "inputSchema": {"type": "object",
                     "properties": {"table": {"type": "string"}, "record_id": {"type": "string"},
                                    "file_token": {"type": "string"}, "file_name": {"type": "string"}},
                     "required": ["table", "record_id", "file_token"]}},
    {"name": "list_files",
     "description": f"列出【{DEPT}】存储空间所有文件(递归含子文件夹):name/type/file_token。",
     "inputSchema": {"type": "object", "properties": {}, "required": []}},
    {"name": "read_file",
     "description": "读一个文件正文(传 list_files 给的 file_token)。支持:PDF(提取文字)、图片/扫描件(OCR)、飞书原生文档(docx/wiki)、文本/Markdown。",
     "inputSchema": {"type": "object", "properties": {"file_token": {"type": "string"}}, "required": ["file_token"]}},
    {"name": "read_audit",
     "description": f"看【{DEPT}】最近的操作日志(谁动了数据的留痕:时间/工具/读还是写/参数)。老板或负责人问「最近谁改了什么/有哪些操作」用它。",
     "inputSchema": {"type": "object", "properties": {"n": {"type": "integer", "description": "看最近几条,默认20"}}, "required": []}},
]


def _send(o):
    sys.stdout.write(json.dumps(o, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _find_attach_field(store, table):
    """找表里的附件类型字段(type 17)。"""
    for n, t in _field_names(store, table):
        if t == 17:
            return n
    return None


def _attach_evidence(table, record_id, file_token, file_name="凭证依据"):
    """把部门文件夹里的一个文件(file_token,来自 list_files)挂到某条记录的附件字段=记账留依据/凭证归档。
    机制:下载 drive 文件 → 作为 bitable 媒体重传 → 追加到记录的附件字段。"""
    info = _registry().get(DEPT)
    if not info or table not in info.get("tables", {}):
        return json.dumps({"error": f"{DEPT} 没有表「{table}」"}, ensure_ascii=False)
    from datastore import FeishuDataStore
    store = FeishuDataStore(app_token=info["app_token"], tables=info["tables"])
    field = _find_attach_field(store, table)
    if not field:
        return json.dumps({"error": f"表「{table}」没有附件字段。先在飞书给它加一个「附件」类型字段(如 凭证依据)。"}, ensure_ascii=False)
    import urllib.request as _u
    tok = _drive_token()
    try:  # 1. 下载文件夹里的文件
        raw = _u.urlopen(_u.Request(LARK_BASE + f"/drive/v1/files/{file_token}/download",
                                    headers={"Authorization": "Bearer " + tok}), timeout=60).read()
    except Exception as e:
        return json.dumps({"error": f"下载文件失败(file_token 对吗): {str(e)[:100]}"}, ensure_ascii=False)
    b = "----ev9x"  # 2. 作为 bitable 媒体上传
    body = b""
    for k, v in [("file_name", file_name), ("parent_type", "bitable_file"), ("parent_node", info["app_token"]), ("size", str(len(raw)))]:
        body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    body += f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{file_name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode() + raw + b"\r\n" + f"--{b}--\r\n".encode()
    try:
        media = json.load(_u.urlopen(_u.Request(LARK_BASE + "/drive/v1/medias/upload_all", data=body,
                          headers={"Authorization": "Bearer " + tok, "Content-Type": f"multipart/form-data; boundary={b}"}), timeout=120)).get("data", {}).get("file_token")
    except Exception as e:
        return json.dumps({"error": f"媒体上传失败: {str(e)[:100]}"}, ensure_ascii=False)
    if not media:
        return json.dumps({"error": "媒体上传未返回 token"}, ensure_ascii=False)
    cur = []  # 3. 取当前附件(追加不覆盖)→ 更新记录
    for rec in store.list_records(table):
        if rec.get("_record_id") == record_id:
            v = rec.get(field)
            if isinstance(v, list):
                cur = [{"file_token": a.get("file_token")} for a in v if isinstance(a, dict) and a.get("file_token")]
            break
    cur.append({"file_token": media})
    try:
        store.update_record(table, record_id, {field: cur})
    except Exception as e:
        return json.dumps({"error": f"写附件字段失败: {str(e)[:120]}"}, ensure_ascii=False)
    return json.dumps({"ok": True, "已挂依据": f"{table} / {record_id}", "附件字段": field, "当前附件数": len(cur)}, ensure_ascii=False)


AUDIT_DIR = os.path.join(HERE, "audit")


def _audit(tool, args, result, ok=True):
    """操作审计:每次工具调用记一行到 audit/<dept>.jsonl。记到部门级(zeroclaw 不传调用者身份,记不到具体人)。审计失败不影响主流程。"""
    try:
        os.makedirs(AUDIT_DIR, exist_ok=True)
        rec = {"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "dept": DEPT, "tool": tool,
               "args": {k: str(v)[:200] for k, v in (args or {}).items()},
               "ok": ok, "result_len": len(result or ""), "result_preview": (result or "")[:120]}
        with open(os.path.join(AUDIT_DIR, f"{DEPT}.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _read_audit(n=20):
    """看本部门最近 n 条操作日志(写操作=log_record,其余=读)。"""
    p = os.path.join(AUDIT_DIR, f"{DEPT}.jsonl")
    if not os.path.exists(p):
        return "(暂无操作日志)"
    lines = open(p, encoding="utf-8").read().strip().split("\n")
    out = []
    for ln in lines[-n:]:
        try:
            r = json.loads(ln)
            kind = "✍️写" if r["tool"] == "log_record" else "👁读"
            out.append(f"{r['ts']} · {kind} · {r['tool']} · {'✓' if r['ok'] else '✗'} · {json.dumps(r['args'], ensure_ascii=False)[:80]}")
        except Exception:
            pass
    return "\n".join(out) if out else "(暂无操作日志)"


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        method, rid = msg.get("method"), msg.get("id")
        if method == "initialize":
            pv = (msg.get("params") or {}).get("protocolVersion") or PROTOCOL
            _send({"jsonrpc": "2.0", "id": rid, "result": {
                "protocolVersion": pv, "capabilities": {"tools": {}},
                "serverInfo": {"name": f"codata-{DEPT}", "version": "3.0.0"}}})
        elif method in ("notifications/initialized", "initialized"):
            continue
        elif method == "ping":
            _send({"jsonrpc": "2.0", "id": rid, "result": {}})
        elif method == "tools/list":
            _send({"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            params = msg.get("params") or {}
            name = params.get("name")
            args = params.get("arguments") or {}
            try:
                if name == "get_company_data":
                    text = _company_data()
                elif name == "analyze":
                    text = _analyze()
                elif name == "log_record":
                    text = _log_record(args.get("table", ""), args.get("data") or {})
                elif name == "attach_evidence":
                    text = _attach_evidence(args.get("table", ""), args.get("record_id", ""), args.get("file_token", ""), args.get("file_name", "凭证依据"))
                elif name == "list_files":
                    text = _list_files()
                elif name == "read_file":
                    text = _read_file(args.get("file_token", ""))
                elif name == "read_audit":
                    text = _read_audit(int(args.get("n", 20)))
                else:
                    text = f"unknown tool: {name}"
                _audit(name, args, text, ok=True)
                _send({"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": text}]}})
            except Exception as e:
                _audit(name, args, str(e), ok=False)
                _send({"jsonrpc": "2.0", "id": rid, "result": {
                    "content": [{"type": "text", "text": f"ERROR: {e}"}], "isError": True}})
        elif rid is not None:
            _send({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"method not found: {method}"}})


if __name__ == "__main__":
    try:
        main()
    except (BrokenPipeError, KeyboardInterrupt):
        pass  # 读取端(zeroclaw)关管道 / Ctrl+C → 静默退出,不吐 traceback
