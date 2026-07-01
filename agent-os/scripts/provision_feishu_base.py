#!/usr/bin/env python3
"""
飞书 Base 建表脚本(infra-as-code,幂等)。
读 ../.feishu凭证.local,按《飞书Base建表清单》在 Base 里建齐所有表。
- 已存在的表跳过(按表名),只补缺。
- 删掉飞书自动生成的空默认表「数据表」。
- 表元数据写入 ../feishu_base_meta.json。
换公司 = 改凭证(指向新 Base)+ 跑一遍。
字段类型: 1文本 2数字 3单选 4多选 5日期 11人员 15超链接 17附件 20公式 1001创建时间 1002最后更新时间
说明:项目↔回款↔部门↔成员 的「关联」与「未回款=合同额-已回款」公式,飞书 API 侧脆弱,
     本系统改在 engine 层用 Python 按名字 join + 计算(更稳),故这里不建 link/formula 字段。
"""
import json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CRED = os.path.join(HERE, "..", ".feishu凭证.local")
META_OUT = os.path.join(HERE, "..", "feishu_base_meta.json")
BASE = os.environ.get("LARK_API_BASE", "https://open.feishu.cn/open-apis")  # 海外 Lark:设环境变量 LARK_API_BASE=https://open.larksuite.com/open-apis


def load_creds():
    d = {}
    with open(CRED, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip()
    return d


def api(method, path, token, body=None):
    req = urllib.request.Request(BASE + path,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 method=method)
    req.add_header("Content-Type", "application/json; charset=utf-8")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def get_token(c):
    r = api("POST", "/auth/v3/tenant_access_token/internal", None,
            {"app_id": c["FEISHU_APP_ID"], "app_secret": c["FEISHU_APP_SECRET"]})
    if r.get("code") != 0:
        sys.exit("拿 token 失败: " + json.dumps(r, ensure_ascii=False))
    return r["tenant_access_token"]


def sel(*names):
    return {"options": [{"name": n} for n in names]}


def date_prop():
    return {"date_formatter": "yyyy/MM/dd", "auto_fill": False}


TABLES = [
    ("组织·成员", [
        {"field_name": "姓名", "type": 1},
        {"field_name": "部门", "type": 3, "property": sel("销售", "交付", "培训", "财务", "行政")},
        {"field_name": "角色", "type": 3, "property": sel("老板", "部门负责人", "成员")},
        {"field_name": "飞书OpenID", "type": 1},
        {"field_name": "在职状态", "type": 3, "property": sel("在职", "离职")},
    ]),
    ("部门", [
        {"field_name": "部门名", "type": 1},
        {"field_name": "负责人", "type": 1},
        {"field_name": "绑定Agent", "type": 3, "property": sel("CEO参谋长", "销售", "交付", "培训", "财务")},
        {"field_name": "月度目标", "type": 1},
    ]),
    ("项目落地进展", [
        {"field_name": "项目名", "type": 1},
        {"field_name": "所属部门", "type": 3, "property": sel("销售", "交付", "培训", "财务")},
        {"field_name": "负责人", "type": 1},
        {"field_name": "状态", "type": 3, "property": sel("未启动", "进行中", "风险", "已交付", "暂停")},
        {"field_name": "落地进度(%)", "type": 2},
        {"field_name": "当前里程碑", "type": 1},
        {"field_name": "里程碑截止", "type": 5, "property": date_prop()},
        {"field_name": "交付物链接", "type": 15},
        {"field_name": "风险卡点", "type": 1},
        {"field_name": "更新时间", "type": 1002},
    ]),
    ("回款进展", [
        {"field_name": "客户", "type": 1},
        {"field_name": "关联项目", "type": 1},
        {"field_name": "合同额", "type": 2},
        {"field_name": "已开票", "type": 2},
        {"field_name": "已回款", "type": 2},
        {"field_name": "未回款", "type": 2},
        {"field_name": "账期到期日", "type": 5, "property": date_prop()},
        {"field_name": "状态", "type": 3, "property": sel("未开票", "已开票待回", "部分回款", "已结清", "逾期")},
        {"field_name": "负责人", "type": 1},
        {"field_name": "更新时间", "type": 1002},
    ]),
    ("培训进展", [
        {"field_name": "培训项目", "type": 1},
        {"field_name": "对象部门", "type": 3, "property": sel("销售", "交付", "培训", "财务", "全员")},
        {"field_name": "参与人", "type": 1},
        {"field_name": "状态", "type": 3, "property": sel("未开始", "进行中", "已完成")},
        {"field_name": "完成率(%)", "type": 2},
        {"field_name": "培训材料链接", "type": 15},
        {"field_name": "更新时间", "type": 1002},
    ]),
    ("月度计划·目标", [
        {"field_name": "标题", "type": 1},
        {"field_name": "月份", "type": 1},
        {"field_name": "部门", "type": 3, "property": sel("销售", "交付", "培训", "财务", "全员")},
        {"field_name": "目标", "type": 1},
        {"field_name": "关键结果", "type": 1},
        {"field_name": "进度(%)", "type": 2},
        {"field_name": "负责人", "type": 1},
        {"field_name": "状态", "type": 3, "property": sel("进行中", "达成", "未达成", "顺延")},
    ]),
    ("业务·周报", [
        {"field_name": "标题", "type": 1},
        {"field_name": "部门", "type": 3, "property": sel("销售", "交付", "培训", "财务")},
        {"field_name": "周", "type": 5, "property": date_prop()},
        {"field_name": "进展亮点", "type": 1},
        {"field_name": "卡点", "type": 1},
        {"field_name": "下周计划", "type": 1},
    ]),
    ("财务概览", [
        {"field_name": "月份", "type": 1},
        {"field_name": "收入", "type": 2},
        {"field_name": "支出", "type": 2},
        {"field_name": "利润", "type": 2},
        {"field_name": "现金余额", "type": 2},
        {"field_name": "关键指标备注", "type": 1},
    ]),
    ("Agent任务台账", [
        {"field_name": "任务", "type": 1},
        {"field_name": "Agent", "type": 3, "property": sel("CEO参谋长", "销售", "交付", "培训", "财务")},
        {"field_name": "触发方式", "type": 3, "property": sel("心跳", "定时", "对话")},
        {"field_name": "产出链接", "type": 15},
        {"field_name": "时间", "type": 1001},
    ]),
    # —— 让 agent 成为"有记忆有规则的专职 agent"的两张表 ——
    ("Agent配置", [
        {"field_name": "Agent", "type": 1},
        {"field_name": "角色", "type": 1},
        {"field_name": "职责", "type": 1},
        {"field_name": "规则", "type": 1},
        {"field_name": "心跳任务", "type": 1},
        {"field_name": "是否启用", "type": 3, "property": sel("启用", "停用")},
    ]),
    ("Agent记忆", [
        {"field_name": "内容", "type": 1},
        {"field_name": "Agent", "type": 3, "property": sel("CEO参谋长", "销售", "交付", "培训", "财务")},
        {"field_name": "类型", "type": 3, "property": sel("长期事实", "观察", "决定", "已提醒")},
        {"field_name": "关联对象", "type": 1},
        {"field_name": "日期", "type": 1001},
    ]),
]


def list_tables(app, token):
    r = api("GET", f"/bitable/v1/apps/{app}/tables?page_size=100", token)
    return {t["name"]: t["table_id"] for t in r.get("data", {}).get("items", [])}


def main():
    c = load_creds()
    app = c.get("FEISHU_BASE_APP_TOKEN")
    if not app:
        sys.exit("缺 FEISHU_BASE_APP_TOKEN")
    token = get_token(c)
    print(f"Base: {app}\n")

    existing = list_tables(app, token)

    # 删掉飞书自动生成的空默认表
    if "数据表" in existing:
        api("DELETE", f"/bitable/v1/apps/{app}/tables/{existing['数据表']}", token)
        print("🗑  删除默认空表「数据表」")
        del existing["数据表"]

    meta = {"app_token": app, "tables": dict(existing)}
    for name, fields in TABLES:
        if name in existing:
            meta["tables"][name] = existing[name]
            print(f"·  {name}  已存在,跳过  ({existing[name]})")
            continue
        body = {"table": {"name": name, "default_view_name": "总表", "fields": fields}}
        r = api("POST", f"/bitable/v1/apps/{app}/tables", token, body)
        if r.get("code") == 0:
            tid = r["data"]["table_id"]
            meta["tables"][name] = tid
            print(f"✓  {name}  ->  {tid}  ({len(fields)} 字段)")
        else:
            print(f"✗  {name}: code={r.get('code')} msg={r.get('msg')}")

    with open(META_OUT, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"\n表元数据已写入 {os.path.relpath(META_OUT, HERE)} ({len(meta['tables'])} 张表)")


if __name__ == "__main__":
    main()
