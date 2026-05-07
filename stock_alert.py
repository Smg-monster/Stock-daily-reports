import os
import io
import requests
import pandas as pd

THRESHOLD_YI = 25000
TWSE_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data"

def send_discord(turnover_yi, gap, exceeded):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("找不到 DISCORD_WEBHOOK_URL")

    color = 15548997 if exceeded else 5763719  # 紅色 / 綠色
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
        return r
    except requests.exceptions.Timeout:
        raise RuntimeError("Discord 發送超時")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Discord 發送失敗: {e}")
