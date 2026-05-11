import os
import io
import requests
import pandas as pd

THRESHOLD_YI = 25000
TWSE_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data"
LAST_VALUE_FILE = "last_turnover.txt"

def send_discord(turnover_yi, gap, exceeded):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("找不到 DISCORD_WEBHOOK_URL")

    color = 15548997 if exceeded else 5763719
    status = "已突破 2.5 兆" if exceeded else "未突破 2.5 兆"

    embed = {
        "title": "台股日報",
        "color": color,
        "fields": [
            {"name": "成交值", "value": f"{turnover_yi:,.0f} 億", "inline": True},
            {"name": "門檻", "value": "25,000 億", "inline": True},
            {"name": "差額", "value": "已突破" if exceeded else f"還差 {gap:,.0f} 億", "inline": True},
            {"name": "狀態", "value": status, "inline": False},
        ]
    }

    payload = {"embeds": [embed]}

    try:
        r = requests.post(webhook_url, json=payload, timeout=10)
        r.raise_for_status()
        print("discord status:", r.status_code)
    except requests.exceptions.Timeout:
        raise RuntimeError("Discord 發送超時")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Discord 發送失敗: {e}")

def get_twse_turnover_yi():
    try:
        r = requests.get(TWSE_URL, timeout=20)
        r.raise_for_status()
    except requests.exceptions.Timeout:
        raise RuntimeError("TWSE 抓取超時")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"TWSE 抓取失敗: {e}")

    try:
        df = pd.read_csv(io.StringIO(r.text))
    except Exception as e:
        raise RuntimeError(f"CSV 解析失敗: {e}")

    value_col = None
    if "成交金額" in df.columns:
        value_col = "成交金額"
    elif "TradeValue" in df.columns:
        value_col = "TradeValue"
    else:
        raise RuntimeError(f"找不到成交金額欄位，實際欄位: {df.columns.tolist()}")

    df[value_col] = pd.to_numeric(
        df[value_col].astype(str).str.replace(",", "", regex=False),
        errors="coerce"
    )

    return df[value_col].sum() / 100000000

def read_last_value():
    if not os.path.exists(LAST_VALUE_FILE):
        return None
    try:
        with open(LAST_VALUE_FILE, "r", encoding="utf-8") as f:
            return float(f.read().strip())
    except Exception:
        return None

def save_last_value(value):
    with open(LAST_VALUE_FILE, "w", encoding="utf-8") as f:
        f.write(str(value))

if __name__ == "__main__":
    try:
        turnover_yi = get_twse_turnover_yi()
        last_value = read_last_value()

        print(f"本次成交值：{turnover_yi:,.0f} 億")
        print(f"上次成交值：{last_value}")

        if last_value is not None and round(turnover_yi, 2) == round(last_value, 2):
            print("成交值沒有變動，不發送 Discord。")
        else:
            gap = THRESHOLD_YI - turnover_yi
            exceeded = turnover_yi >= THRESHOLD_YI
            send_discord(turnover_yi, gap, exceeded)
            save_last_value(turnover_yi)
            print("成交值有變動，已發送 Discord 並更新 last_turnover.txt。")

    except Exception as e:
        print(f"整體流程失敗: {e}")
        raise
