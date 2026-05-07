import requests
import pandas as pd
import io
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

WEBHOOK_URL = "https://discord.com/api/webhooks/1501936628027883553/NWJsszzTj31gyjzvLzm6mFfkGEkEW47T3Y-NEn2OJWMv9QzkDJNnWBkxSIoWuvHpkkkc"
THRESHOLD_YI = 25000

def send_discord(msg):
    r = requests.post(WEBHOOK_URL, json={"content": msg}, timeout=15, verify=False)
    print("discord status:", r.status_code)
    return r

def get_twse_turnover_yi():
    url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=open_data"
    text = requests.get(url, timeout=20, verify=False).text
    df = pd.read_csv(io.StringIO(text))

    if "成交金額" not in df.columns:
        raise KeyError(f"找不到成交金額欄位，實際欄位: {df.columns.tolist()}")

    df["成交金額"] = pd.to_numeric(
        df["成交金額"].astype(str).str.replace(",", "", regex=False),
        errors="coerce"
    )
    return df["成交金額"].sum() / 100000000

if __name__ == "__main__":
    turnover_yi = get_twse_turnover_yi()
    status = "已突破 2.5 兆" if turnover_yi >= THRESHOLD_YI else "未突破 2.5 兆"
    print(f"今天台股成交值：{turnover_yi:,.0f} 億")
    print("門檻判斷：", turnover_yi >= THRESHOLD_YI)

    send_discord(f"台股今日成交值 {turnover_yi:,.0f} 億，{status}。")