"""codata(feishu_mcp)纯计算逻辑的单元测试——财务系统的可信度地基。
都是不碰飞书 API 的纯函数。跑:python3 -m unittest discover tests  (或 pytest)。
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "agent-os"))
sys.path.insert(0, os.path.join(ROOT, "agent-os", "scripts"))

import feishu_mcp as m            # noqa: E402
import provision_feishu_base as p  # noqa: E402


class TestYmd(unittest.TestCase):
    def test_ms_timestamp_to_date_format(self):
        out = m._ymd(1609459200000)  # ~2021-01-01,毫秒
        self.assertRegex(out, r"^\d{4}-\d{2}-\d{2}$")

    def test_non_numeric_passthrough(self):
        self.assertEqual(m._ymd("abc"), "abc")
        self.assertEqual(m._ymd(None), None)


class TestSummarize(unittest.TestCase):
    def test_counts_and_sums_number_fields(self):
        rows = [{"金额": 100, "客户": "A", "_record_id": "r1"},
                {"金额": 50, "客户": "B", "_record_id": "r2"}]
        out = m._summarize(rows, num_fields={"金额"}, date_fields=set())
        self.assertEqual(out["记录数"], 2)
        self.assertEqual(out["合计"]["金额"], 150)

    def test_string_numbers_coerced(self):
        # 飞书有时把数字以字符串回传,必须强转后求和
        rows = [{"金额": "100"}, {"金额": "50.5"}]
        out = m._summarize(rows, num_fields={"金额"}, date_fields=set())
        self.assertEqual(out["合计"]["金额"], 150.5)

    def test_non_number_field_not_summed(self):
        rows = [{"金额": 100, "备注": "x"}]
        out = m._summarize(rows, num_fields={"金额"}, date_fields=set())
        self.assertNotIn("备注", out["合计"])

    def test_zero_totals_omitted(self):
        rows = [{"客户": "A"}]
        out = m._summarize(rows, num_fields=set(), date_fields=set())
        self.assertEqual(out["合计"], {})

    def test_date_field_converted_in_records(self):
        rows = [{"日期": 1609459200000}]
        out = m._summarize(rows, num_fields=set(), date_fields={"日期"})
        self.assertRegex(out["记录"][0]["日期"], r"^\d{4}-\d{2}-\d{2}$")

    def test_record_id_stripped(self):
        rows = [{"金额": 1, "_record_id": "rec_x"}]
        out = m._summarize(rows, num_fields={"金额"}, date_fields=set())
        self.assertNotIn("_record_id", out["记录"][0])

    def test_bad_number_ignored_not_crash(self):
        rows = [{"金额": "not_a_number"}, {"金额": 10}]
        out = m._summarize(rows, num_fields={"金额"}, date_fields=set())
        self.assertEqual(out["合计"]["金额"], 10)  # 坏值跳过,不崩


class TestSumNumFields(unittest.TestCase):
    """通用战报的金额汇总——CEO/部门战报靠它出数字。"""

    def test_sums_number_type_fields(self):
        rows = [{"金额": 3000}, {"金额": 1500}, {"金额": 800}]
        ftypes = {"金额": 2, "客户": 1}
        self.assertEqual(m._sum_num_fields(rows, ftypes), {"金额": 5300.0})

    def test_string_numbers_coerced(self):
        # 回归:飞书数字常以字符串回传,严格 isinstance 判断会漏掉 → 金额永远汇总不出来
        rows = [{"金额": "3000"}, {"金额": "1500"}, {"金额": "800"}]
        ftypes = {"金额": 2}
        self.assertEqual(m._sum_num_fields(rows, ftypes), {"金额": 5300.0})

    def test_only_type2_fields_summed(self):
        rows = [{"金额": 100, "客户": "A"}]  # 客户是文本(type 1),不该被汇总
        ftypes = {"金额": 2, "客户": 1}
        out = m._sum_num_fields(rows, ftypes)
        self.assertIn("金额", out)
        self.assertNotIn("客户", out)

    def test_underscore_keys_skipped(self):
        rows = [{"金额": 100, "_record_id": "r1"}]
        ftypes = {"金额": 2, "_record_id": 2}
        self.assertEqual(m._sum_num_fields(rows, ftypes), {"金额": 100.0})

    def test_bad_value_ignored_not_crash(self):
        rows = [{"金额": "n/a"}, {"金额": 10}]
        ftypes = {"金额": 2}
        self.assertEqual(m._sum_num_fields(rows, ftypes), {"金额": 10.0})  # 坏值跳过,不崩

    def test_empty_when_no_number_fields(self):
        self.assertEqual(m._sum_num_fields([{"客户": "A"}], {"客户": 1}), {})


class TestCap(unittest.TestCase):
    def test_short_unchanged(self):
        self.assertEqual(m._cap("hello"), "hello")

    def test_long_truncated_with_note(self):
        out = m._cap("x" * 20000)
        self.assertLess(len(out), 20000)
        self.assertIn("已截断", out)


class TestProvisionHelpers(unittest.TestCase):
    def test_sel_builds_options(self):
        self.assertEqual(p.sel("a", "b"), {"options": [{"name": "a"}, {"name": "b"}]})

    def test_date_prop_is_dict(self):
        self.assertIsInstance(p.date_prop(), dict)


if __name__ == "__main__":
    unittest.main()
