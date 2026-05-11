import os
import requests
import pandas as pd

THRESHOLD_YI = 25000
TWSE_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
STATE_FILE = "last_turnover.txt"

def send_discord(turnover_yi, gap, exceeded, previous_yi=None):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("找不到 DISCORD_WEBHOOK_URL")

    color = 15548997 if exceeded else 5763719
    status = "已突破 2.5 兆" if exceeded else "未突破 2.5 兆"

    if previous_yi is None:
        change_text = "首次記錄"
    else:
        diff = turnover_yi - previous_yi
        if diff > 0:
            change_text = f"增加 {diff:,.0f} 億"
        elif diff < 0:
            change_text = f"減少 {abs(diff):,.0f} 億"
        else:
            change_text = "無變動"

    embed = {
        "title": "台股收盤成交值通知",
        "color": color,
        "fields": [
            {"name": "目前成交值", "value": f"{turnover_yi:,.0f} 億", "inline": True},
            {"name": "門檻", "value": "25,000 億", "inline": True},
            {"name": "差額", "value": "已突破" if exceeded else f"還差 {gap:,.0f} 億", "inline": True},
            {"name": "狀態", "value": status, "inline": False},
            {"name": "和上次相比", "value": change_text, "inline": False},
        ]
    }

    payload = {"embeds": [embed]}
    r = requests.post(webhook_url, json=payload, timeout=10)
    r.raise_for_status()

def get_twse_turnover_yi():
    r = requests.get(TWSE_URL, timeout=20)
    r.raise_for_status()

    data = r.json()
    if not data:
        raise RuntimeError("TWSE 沒有回傳資料")

    df = pd.DataFrame(data)

    if "成交金額" not in df.columns:
        raise RuntimeError(f"找不到成交金額欄位，實際欄位: {df.columns.tolist()}")

    df["成交金額"] = pd.to_numeric(
        df["成交金額"].astype(str).str.replace(",", "", regex=False),
        errors="coerce"
    )

    turnover_yi = df["成交金額"].sum() / 100000000

    if turnover_yi <= 100:
        raise RuntimeError(f"成交值異常過低：{turnover_yi:.2f} 億，可能資料尚未更新")

    return turnover_yi

def read_last_turnover():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return float(content) if content else None
    except Exception:
        return None

def write_last_turnover(turnover_yi):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(str(turnover_yi))

if __name__ == "__main__":
    turnover_yi = get_twse_turnover_yi()
    previous_yi = read_last_turnover()

    print(f"目前成交值：{turnover_yi:,.2f} 億")
    print(f"上次成交值：{previous_yi if previous_yi is not None else 'None'}")

    if previous_yi is None or turnover_yi != previous_yi:
        gap = THRESHOLD_YI - turnover_yi
        exceeded = turnover_yi >= THRESHOLD_YI
        send_discord(turnover_yi, gap, exceeded, previous_yi)

    write_last_turnover(turnover_yi)