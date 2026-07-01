#!/usr/bin/env python3
"""
L1 数据层 · DataStore 抽象 + 飞书适配器(读 + 写 + 发消息)。
架构铁律:上层 agent 只通过 DataStore 读写/发消息,不直接碰飞书 API。
将来切 Baserow/Teable = 新写一个适配器实现同样接口,上层不动。
"""
import json, os, sys, time, urllib.request, urllib.parse, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.environ.get("LARK_API_BASE", "https://open.feishu.cn/open-apis")  # 海外 Lark:设环境变量 LARK_API_BASE=https://open.larksuite.com/open-apis


def _flatten(v):
    """飞书富文本/链接/人员字段可能返回数组或对象,拍平成易读值。"""
    if isinstance(v, list):
        out = []
        for it in v:
            if isinstance(it, dict):
                out.append(it.get("text") or it.get("name") or it.get("en_name") or "")
            else:
                out.append(str(it))
        return "".join(out) if all(isinstance(x, str) for x in out) else out
    if isinstance(v, dict):
        return v.get("text") or v.get("link") or v
    return v


class DataStore:
    """统一接口(上层只认这些方法)。具体实现见各适配器。"""
    def list_records(self, table_name): raise NotImplementedError
    def snapshot(self): raise NotImplementedError
    def create_records(self, table_name, rows): raise NotImplementedError
    def update_record(self, table_name, record_id, fields): raise NotImplementedError
    def send_message(self, target, text, id_type="open_id"): raise NotImplementedError


class FeishuDataStore(DataStore):
    def __init__(self, cred_path=None, meta_path=None, app_token=None, tables=None):
        self.creds = self._load(cred_path or os.path.join(HERE, ".feishu凭证.local"))
        if app_token and tables is not None:
            # 指定某个部门 Base(app_token + 表名→table_id)
            self.meta = {"app_token": app_token, "tables": tables}
        else:
            self.meta = json.load(open(meta_path or os.path.join(HERE, "feishu_base_meta.json"), encoding="utf-8"))
        self.app_token = self.meta["app_token"]
        self._tok = None
        self._tok_exp = 0

    @staticmethod
    def _load(path):
        d = {}
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    d[k.strip()] = v.strip()
        return d

    def _api(self, method, path, body=None, auth=True):
        req = urllib.request.Request(BASE + path,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     method=method)
        req.add_header("Content-Type", "application/json; charset=utf-8")
        if auth:
            req.add_header("Authorization", "Bearer " + self.token())
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            try:
                return json.loads(raw)  # 飞书错误体是 JSON(含 code/msg)→ 上层 caller 查 code 抛错
            except ValueError:          # 非 JSON(网关 500 / HTML)→ 不崩,给结构化错误 + 留痕
                print(f"[datastore] {method} {path} HTTP {e.code}: {raw[:200]}", file=sys.stderr)
                return {"code": e.code, "msg": raw[:200]}
        except urllib.error.URLError as e:   # 网络层失败(连不上 / DNS / 超时)
            print(f"[datastore] {method} {path} 网络失败: {e.reason}", file=sys.stderr)
            return {"code": -1, "msg": f"网络失败: {e.reason}"}

    def token(self):
        if self._tok and time.time() < self._tok_exp - 60:
            return self._tok
        r = self._api("POST", "/auth/v3/tenant_access_token/internal",
                      {"app_id": self.creds["FEISHU_APP_ID"], "app_secret": self.creds["FEISHU_APP_SECRET"]},
                      auth=False)
        self._tok = r["tenant_access_token"]
        self._tok_exp = time.time() + r.get("expire", 7200)
        return self._tok

    def _tid(self, table_name):
        tid = self.meta["tables"].get(table_name)
        if not tid:
            raise KeyError(f"未知表: {table_name}")
        return tid

    # ---- 读 ----
    def list_records(self, table_name, page_size=500):
        tid = self._tid(table_name)
        rows, page_token = [], None
        while True:
            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token
            r = self._api("GET", f"/bitable/v1/apps/{self.app_token}/tables/{tid}/records?{urllib.parse.urlencode(params)}")
            if r.get("code") != 0:
                raise RuntimeError(f"读 {table_name} 失败: {r.get('code')} {r.get('msg')}")
            data = r.get("data") or {}
            for item in data.get("items") or []:
                f = {k: _flatten(v) for k, v in item.get("fields", {}).items()}
                f["_record_id"] = item.get("record_id")
                rows.append(f)
            if data.get("has_more") and data.get("page_token"):
                page_token = data["page_token"]
            else:
                return rows

    def snapshot(self):
        return {name: self.list_records(name) for name in self.meta["tables"]}

    # ---- 写 ----
    def create_records(self, table_name, rows):
        body = {"records": [{"fields": r} for r in rows]}
        r = self._api("POST", f"/bitable/v1/apps/{self.app_token}/tables/{self._tid(table_name)}/records/batch_create", body)
        if r.get("code") != 0:
            raise RuntimeError(f"写 {table_name} 失败: {r.get('code')} {r.get('msg')}")
        return r["data"]["records"]

    def update_record(self, table_name, record_id, fields):
        body = {"fields": fields}
        r = self._api("PUT", f"/bitable/v1/apps/{self.app_token}/tables/{self._tid(table_name)}/records/{record_id}", body)
        if r.get("code") != 0:
            raise RuntimeError(f"更新 {table_name} 失败: {r.get('code')} {r.get('msg')}")
        return r["data"]["record"]

    def delete_records(self, table_name, record_ids):
        if not record_ids:
            return None
        return self._api("POST", f"/bitable/v1/apps/{self.app_token}/tables/{self._tid(table_name)}/records/batch_delete",
                         {"records": record_ids})

    def clear_table(self, table_name):
        ids = [x["_record_id"] for x in self.list_records(table_name) if x.get("_record_id")]
        self.delete_records(table_name, ids)
        return len(ids)

    def log_task(self, agent, task, trigger="心跳", link=""):
        """往 Agent任务台账 记一笔(审计)。台账表不存在则静默跳过。"""
        if "Agent任务台账" not in self.meta["tables"]:
            return
        fields = {"任务": task, "Agent": agent, "触发方式": trigger}
        if link:
            fields["产出链接"] = {"text": "查看", "link": link}
        try:
            self.create_records("Agent任务台账", [fields])
        except Exception:
            pass

    # ---- 发消息(飞书 im,需应用开 im 发消息权限) ----
    def send_message(self, target, text, id_type="open_id"):
        body = {"receive_id": target, "msg_type": "text",
                "content": json.dumps({"text": text}, ensure_ascii=False)}
        r = self._api("POST", f"/im/v1/messages?receive_id_type={id_type}", body)
        return r  # 调用方看 code:0 是否成功;无权限会返回明确错误

    def member_open_id(self, name):
        """从 组织·成员 表查某人的飞书OpenID(填了才查得到)。"""
        for m in self.list_records("组织·成员"):
            if m.get("姓名") == name and m.get("飞书OpenID"):
                return m["飞书OpenID"]
        return None


def get_store():
    return FeishuDataStore()


if __name__ == "__main__":
    ds = get_store()
    print(json.dumps(ds.snapshot(), ensure_ascii=False, indent=2))
