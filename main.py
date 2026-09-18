import hashlib
import json
import os
import time
import requests
from datetime import datetime
USER_ID = os.getenv("AFDIAN_USER_ID")
TOKEN = os.getenv("AFDIAN_TOKEN")
ORDER_API = "https://ifdian.net/api/open/query-order"
SPONSOR_API = "https://ifdian.net/api/open/query-sponsor"

def sign(params: str, ts: int) -> str:
    raw = f"{TOKEN}params{params}ts{ts}user_id{USER_ID}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()
def post(api: str, params: dict):
    body = {
        "user_id": USER_ID,
        "params": json.dumps(params, ensure_ascii=False),
        "ts": int(time.time()),
        "sign": sign(json.dumps(params, ensure_ascii=False), int(time.time())),
    }
    r = requests.post(api, json=body, timeout=15)
    r.raise_for_status()
    data = r.json()
    if data.get("ec") != 200:
        raise RuntimeError(f"爱发电返回错误: {data}")
    return data["data"]
def trade_no_to_ts(no: str) -> int:
    try:
        return int(datetime.strptime(no[:14], "%Y%m%d%H%M%S").timestamp())
    except Exception:
        return 0
def this_month_user_ids():
    now = datetime.now()
    month_start_ts = int(datetime(now.year, now.month, 1).timestamp())
    ids, page = {}, 1
    while True:
        data = post(ORDER_API, {"page": page})
        orders = data.get("list", [])
        if not orders:
            break

        stop = False
        for o in orders:
            ts = o.get("create_time") or trade_no_to_ts(o.get("out_trade_no", ""))
            if ts and ts < month_start_ts:
                stop = True
                break
            if o.get("status") != 2:
                continue
            ids[o["user_id"]] = ts

        if stop:
            break
        if page >= data.get("total_page", 1):
            break
        page += 1

    return ids
def nicknames(user_ids: dict):
    nick_map, p = {}, 1
    while True:
        d = post(SPONSOR_API, {"page": p})
        lst = d.get("list", [])
        if not lst:
            break
        for s in lst:
            nick_map[s["user_id"]] = s.get("user", {}).get("name") or s["user_id"]
        if p >= d.get("total_page", 1):
            break
        p += 1

    return [nick_map.get(uid, uid) for uid in user_ids]
if __name__ == "__main__":
    uids = this_month_user_ids()
    names = nicknames(uids)
    os.makedirs('output/', exist_ok=True)
    with open("output/output.json", "w", encoding="utf-8") as f:
        json.dump(names, f, ensure_ascii=False)