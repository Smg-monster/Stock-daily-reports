import os
import io
import requests
import pandas as pd
from datetime import datetime

THRESHOLD_YI = 25000
TWSE_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data"
LAST_VALUE_FILE = "last_turnover.txt"

def send_discord(turnover_yi, gap, exceeded):
    # 改從環境變數讀取，或是直接填入 (如果你不放 GitHub)
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("警告: 找不到 Webhook URL，跳過發送")
        return

    color = 15548997 if exceeded else 5763719
    status = "🔥 已突破 2.5 兆！" if exceeded else "☁️ 未突破 2.5 兆"

    embed = {
        "title": "📊 台股即時成交值監報",
        "description": f"更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "color": color,
        "fields": [
            {"name": "當前總成交值", "value": f"**{turnover_yi:,.0f} 億**", "inline": True},
            {"name": "目標門檻", "value": "25,000 億", "inline": True},
            {"name": "距離目標", "value": "🏁 已達標" if exceeded else f"還差 {gap:,.0f} 億", "inline": True},
            {"name": "市場狀態", "value": f"**{status}**", "inline": False},
        ],
        "footer": {"text": "數據來源：TWSE 臺灣證券交易所"}
    }

    try:
        r = requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"Discord 發送失敗: {e}")

def get_twse_turnover_yi():
    # 增加 User-Agent 偽裝成瀏覽器，減少被證交所封鎖機率
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(TWSE_URL, headers=headers, timeout=25)
    r.raise_for_status()

    df = pd.read_csv(io.StringIO(r.text))
    df.columns = [c.strip() for c in df.columns] # 清除欄位空白

    # 自動匹配欄位
    possible_cols = ["成交金額", "TradeValue", "成交值"]
    value_col = next((c for c in possible_cols if c in df.columns), None)

    if not value_col:
        raise RuntimeError(f"找不到成交金額欄位。現有欄位: {df.columns.tolist()}")

    # 處理數值中的逗號並轉為數字
    df[value_col] = pd.to_numeric(
        df[value_col].astype(str).str.replace(",", "", regex=False),
        errors="coerce"
    ).fillna(0)

    return df[value_col].sum() / 100000000

# ... (read_last_value 和 save_last_value 保持不變) ...

if __name__ == "__main__":
    try:
        # 額外優化：如果是週末則不跑 (選擇性加入)
        if datetime.now().weekday() >= 5:
             print("今日為週末，非交易日。")
             # exit() # 如果你想在週末停止可開啟這行

        turnover_yi = get_twse_turnover_yi()
        last_value = read_last_value()

        print(f"本次成交值：{turnover_yi:,.2f} 億")

        # 使用 round(1) 避免極小誤差導致重複發送
        if last_value is not None and round(turnover_yi, 1) == round(last_value, 1):
            print("數據無變動，略過發送。")
        else:
            gap = THRESHOLD_YI - turnover_yi
            exceeded = turnover_yi >= THRESHOLD_YI
            send_discord(turnover_yi, gap, exceeded)
            save_last_value(turnover_yi)
            print("✅ 數據更新並已發送 Discord。")

    except Exception as e:
        print(f"❌ 流程失敗: {e}")
