#!/usr/bin/env python3
"""导出全部飞书 Base(全公司业务数据)到 JSON 备份。

业务数据底座 = 飞书云(已天然备份),这是**额外本地副本**:可跑成 cron 定期导出,
再单向推到第二台设备(只收不删),作为「单点故障」的兜底。

用法:
  python3 export_feishu_backup.py [--out <目录>]
默认输出到 公司AI系统/数据备份/飞书Base备份-YYYY-MM-DD/<部门>.json
"""
import sys
import os
import json
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
AOS = os.path.dirname(HERE)  # agent-os
sys.path.insert(0, AOS)
from datastore import FeishuDataStore  # noqa: E402


def main():
    out = os.path.join(os.path.dirname(AOS), "数据备份")  # 默认:公司AI系统/数据备份
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    date = datetime.now().strftime("%Y-%m-%d")
    outdir = os.path.join(out, f"飞书Base备份-{date}")
    os.makedirs(outdir, exist_ok=True)
    reg = json.load(open(os.path.join(AOS, "dept_registry.json"), encoding="utf-8"))

    total = 0
    for dept, info in reg.items():
        try:
            store = FeishuDataStore(app_token=info["app_token"], tables=info["tables"])
            dump = {"_meta": {"dept": dept, "app_token": info["app_token"], "exported": date}}
            n = 0
            for tname in info["tables"]:
                recs = store.list_records(tname)
                dump[tname] = recs
                n += len(recs)
            with open(os.path.join(outdir, f"{dept}.json"), "w", encoding="utf-8") as f:
                json.dump(dump, f, ensure_ascii=False, indent=2, default=str)
            total += n
            print(f"  ✓ {dept}: {n} 条 / {len(info['tables'])} 表")
        except Exception as e:
            print(f"  ✗ {dept}: {str(e)[:100]}")
    print(f"\n备份完成 → {outdir}({total} 条记录)")


if __name__ == "__main__":
    main()
