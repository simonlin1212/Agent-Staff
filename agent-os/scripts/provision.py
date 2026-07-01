#!/usr/bin/env python3
"""Agent-Staff · 建部门:按 DEPARTMENTS 建各部门飞书 Base + 表 + 存储文件夹,产出 dept_registry.json。

参谋层只追踪不干活,表结构 = 精简的经营台账(动嘴汇报 → 参谋记账 进来)。
用你的飞书自建应用建(需 bitable + drive 权限)。复用 provision_feishu_base 的 api/token/字段助手。
字段类型:1 文本 / 2 数字 / 3 单选 / 5 日期 / 17 附件 / 1002 最后更新时间。

默认建 9 个部门(一套完整公司组织架构:CEO 参谋长 + 营收[自媒体/电商/业务] + 职能[财务/人力/行政/运营/合规])。
删不需要的、或加你自己的部门 = 改 TABLES + DEPARTMENTS,照葫芦画瓢。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from provision_feishu_base import load_creds, api, get_token, sel, date_prop  # noqa: E402

REG_OUT = os.path.join(HERE, "..", "dept_registry.json")

# ---- 表结构(每部门追踪什么)----
TABLES = {
    # ── 公司(CEO 全局)──
    "月度目标": [
        {"field_name": "部门", "type": 1},
        {"field_name": "月份", "type": 1},
        {"field_name": "目标", "type": 1},
        {"field_name": "进度(%)", "type": 2},
        {"field_name": "状态", "type": 3, "property": sel("进行中", "达成", "未达成", "顺延")},
    ],
    "经营备注": [
        {"field_name": "日期", "type": 5, "property": date_prop()},
        {"field_name": "内容", "type": 1},
        {"field_name": "类型", "type": 3, "property": sel("决定", "风险", "观察", "目标")},
    ],
    "财务台账": [
        {"field_name": "日期", "type": 5, "property": date_prop()},
        {"field_name": "月份", "type": 1},
        {"field_name": "来源", "type": 1},
        {"field_name": "项目", "type": 1},
        {"field_name": "金额", "type": 2},
        {"field_name": "币种", "type": 3, "property": sel("RMB", "USD")},
    ],
    # ── 自媒体运营部(营收)──
    "内容台账": [
        {"field_name": "日期", "type": 5, "property": date_prop()},
        {"field_name": "平台", "type": 1},
        {"field_name": "作品", "type": 1},
        {"field_name": "播放量", "type": 2},
        {"field_name": "新增粉丝", "type": 2},
        {"field_name": "变现", "type": 2},
        {"field_name": "备注", "type": 1},
    ],
    # ── 电商部(营收)──
    "订单台账": [
        {"field_name": "日期", "type": 5, "property": date_prop()},
        {"field_name": "店铺", "type": 1},
        {"field_name": "订单数", "type": 2},
        {"field_name": "GMV", "type": 2},
        {"field_name": "退款", "type": 2},
        {"field_name": "净利润", "type": 2},
        {"field_name": "备注", "type": 1},
    ],
    # ── 业务部(营收)──
    "业务台账": [
        {"field_name": "日期", "type": 5, "property": date_prop()},
        {"field_name": "客户", "type": 1},
        {"field_name": "项目", "type": 1},
        {"field_name": "合同额", "type": 2},
        {"field_name": "已回款", "type": 2},
        {"field_name": "状态", "type": 3, "property": sel("洽谈", "签约", "回款", "流失")},
        {"field_name": "备注", "type": 1},
    ],
    # ── 财务部(职能)──
    "运营支出明细": [
        {"field_name": "日期", "type": 5, "property": date_prop()},
        {"field_name": "类别", "type": 3, "property": sel("人工", "办公", "场地", "软件", "营销", "差旅", "其他")},
        {"field_name": "项目", "type": 1},
        {"field_name": "金额", "type": 2},
        {"field_name": "币种", "type": 3, "property": sel("RMB", "USD")},
        {"field_name": "说明", "type": 1},
        {"field_name": "凭证依据", "type": 17},  # 附件字段:用 attach_evidence 挂发票/凭证
    ],
    "固定支出清单": [
        {"field_name": "类别", "type": 3, "property": sel("订阅", "租金", "其他")},
        {"field_name": "项目", "type": 1},
        {"field_name": "月额", "type": 2},
        {"field_name": "币种", "type": 3, "property": sel("RMB", "USD")},
        {"field_name": "说明", "type": 1},
    ],
    # ── 人力部(职能)──
    "员工花名册": [
        {"field_name": "姓名", "type": 1},
        {"field_name": "飞书OpenID", "type": 1},   # 身份地基:权限白名单按它锁
        {"field_name": "部门", "type": 1},
        {"field_name": "职级", "type": 3, "property": sel("员工", "主管", "总监", "HR", "CEO")},
        {"field_name": "月薪", "type": 2},
        {"field_name": "状态", "type": 3, "property": sel("在职", "离职")},
        {"field_name": "入职日期", "type": 5, "property": date_prop()},
    ],
    # ── 行政部(职能)──
    "合同档案": [
        {"field_name": "名称", "type": 1},
        {"field_name": "对方", "type": 1},
        {"field_name": "类型", "type": 3, "property": sel("供应商", "客户", "租赁", "其他")},
        {"field_name": "金额", "type": 2},
        {"field_name": "到期日", "type": 5, "property": date_prop()},   # 到期提醒:行政 cron 巡检
        {"field_name": "状态", "type": 3, "property": sel("生效中", "即将到期", "已过期")},
    ],
    # ── 运营部(职能)──
    "运营指标": [
        {"field_name": "日期", "type": 5, "property": date_prop()},
        {"field_name": "指标", "type": 1},
        {"field_name": "数值", "type": 2},
        {"field_name": "环比(%)", "type": 2},
        {"field_name": "备注", "type": 1},
    ],
    # ── 合规部(职能)──
    "合规检查": [
        {"field_name": "日期", "type": 5, "property": date_prop()},
        {"field_name": "检查项", "type": 1},
        {"field_name": "结果", "type": 3, "property": sel("通过", "待整改", "风险")},
        {"field_name": "负责人", "type": 1},
        {"field_name": "备注", "type": 1},
    ],
}

# 部门 -> (Base 显示名, [表名])。一套完整公司组织架构;删/加部门照这个改。
DEPARTMENTS = {
    "公司":        ("AgentStaff-公司", ["月度目标", "经营备注", "财务台账"]),  # CEO 参谋长(全局)
    "自媒体运营部": ("AgentStaff-自媒体", ["内容台账"]),   # 营收
    "电商部":      ("AgentStaff-电商", ["订单台账"]),      # 营收
    "业务部":      ("AgentStaff-业务", ["业务台账"]),      # 营收
    "财务部":      ("AgentStaff-财务", ["运营支出明细", "固定支出清单"]),  # 职能
    "人力部":      ("AgentStaff-人力", ["员工花名册"]),    # 职能
    "行政部":      ("AgentStaff-行政", ["合同档案"]),      # 职能
    "运营部":      ("AgentStaff-运营", ["运营指标"]),      # 职能
    "合规部":      ("AgentStaff-合规", ["合规检查"]),      # 职能
}


def create_base(token, name):
    r = api("POST", "/bitable/v1/apps", token, {"name": name})
    if r.get("code") != 0:
        raise RuntimeError(f"建 Base {name} 失败: {r.get('code')} {r.get('msg')}")
    return r["data"]["app"]["app_token"], r["data"]["app"]["url"]


def create_table(token, app_token, name):
    fields = TABLES[name]
    body = {"table": {"name": name, "default_view_name": "总表", "fields": fields}}
    r = api("POST", f"/bitable/v1/apps/{app_token}/tables", token, body)
    return r["data"]["table_id"] if r.get("code") == 0 else f"ERR:{r.get('msg')}"


def create_folder(token, name):
    r = api("POST", "/drive/v1/files/create_folder", token, {"name": name, "folder_token": ""})
    return r["data"]["token"] if r.get("code") == 0 else f"ERR:{r.get('msg')}"


def main():
    c = load_creds()
    token = get_token(c)
    reg = {}
    for dept, (base_name, tnames) in DEPARTMENTS.items():
        app_token, url = create_base(token, base_name)
        tables = {tn: create_table(token, app_token, tn) for tn in tnames}
        folder = create_folder(token, f"AgentStaff-{dept}-文件")
        reg[dept] = {"base_name": base_name, "app_token": app_token, "url": url,
                     "tables": tables, "folder_token": folder}
        print(f"✓ {dept}: {app_token} | 表 {list(tables.keys())} | 文件夹 {folder}")
    with open(REG_OUT, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
    print(f"\n✅ dept_registry.json 已生成({len(reg)} 部门)")


if __name__ == "__main__":
    main()
