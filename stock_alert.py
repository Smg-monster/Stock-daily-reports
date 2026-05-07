import os
import io
import requests
import pandas as pd

THRESHOLD_YI = 25000
TWSE_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data"

def send_discord(msg):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("找不到 DISCORD_WEBHOOK_URL")

    try:
        r = requests.post(
            webhook_url,
            json={"content": msg},
            timeout=10
        )
        r.raise_for_status()
        print("discord status:", r.status_code)
        return r
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

    if "成交金額" not in df.columns:
        raise KeyError(f"找不到成交金額欄位，實際欄位: {df.columns.tolist()}")

    df["成交金額"] = pd.to_numeric(
        df["成交金額"].astype(str).str.replace(",", "", regex=False),
        errors="coerce"
    )

    return df["成交金額"].sum() / 100000000

def main():
    try:
        turnover_yi = get_twse_turnover_yi()
        gap = THRESHOLD_YI - turnover_yi
        status = "已突破 2.5 兆" if turnover_yi >= THRESHOLD_YI else f"距離門檻還差 {gap:,.0f} 億"

        print(f"今天台股成交值：{turnover_yi:,.0f} 億")
        print("門檻判斷：", turnover_yi >= THRESHOLD_YI)

        send_discord(f"台股今日成交值 {turnover_yi:,.0f} 億，{status}。")

    except Exception as e:
        print(f"整體流程失敗: {e}")
        raise

if __name__ == "__main__":
    main()
