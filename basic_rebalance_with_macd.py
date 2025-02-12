import time
import hmac
import hashlib
import requests
import pandas as pd
import numpy as np
from datetime import datetime

API_KEY = ""
SECRET_KEY = ""
BASE_URL = "https://api.binance.th"

# ---------------------------------------------------
# 1) ฟังก์ชันเชื่อมต่อกับ Binance TH
# ---------------------------------------------------
def get_server_time():
    url = f"{BASE_URL}/api/v1/time"
    resp = requests.get(url)
    data = resp.json()
    return data.get("serverTime", 0)

def sign_params(query_string: str, secret_key: str):
    return hmac.new(
        secret_key.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

def get_account_info():
    """
    ดึงข้อมูลบัญชี เช่น Balances
    Endpoint: GET /api/v1/account
    """
    ts = get_server_time()
    if ts == 0:
        raise Exception("Cannot get server time.")

    query_string = f"timestamp={ts}"
    signature = sign_params(query_string, SECRET_KEY)
    url = f"{BASE_URL}/api/v1/account?{query_string}&signature={signature}"
    headers = {
        "X-MBX-APIKEY": API_KEY,
        "Accept": "application/json"
    }
    resp = requests.get(url, headers=headers)
    return resp.json()

def place_order(symbol, side, order_type, quantity_or_quote):
    """
    ส่งคำสั่งเทรด (Market Order) ไป Binance TH
    Endpoint: POST /api/v1/order
    side: "BUY" หรือ "SELL"
    order_type: "MARKET"
    quantity_or_quote: ถ้า side=BUY => ใช้เป็น 'quoteOrderQty' (THB), side=SELL => 'quantity' (BTC)
    """
    ts = get_server_time()
    if ts == 0:
        raise Exception("Cannot get server time.")

    endpoint = f"{BASE_URL}/api/v1/order"
    params_dict = {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "timestamp": ts
    }

    # BUY => ใส่ THB ใน quoteOrderQty
    # SELL => ใส่ BTC ใน quantity
    if side == "BUY":
        params_dict["quoteOrderQty"] = quantity_or_quote
    else:
        params_dict["quantity"] = quantity_or_quote

    # สร้าง query string
    qs_list = [f"{k}={v}" for k, v in params_dict.items()]
    query_string = "&".join(qs_list)
    signature = sign_params(query_string, SECRET_KEY)
    query_string += f"&signature={signature}"

    headers = {
        "X-MBX-APIKEY": API_KEY,
        "Accept": "application/json"
    }

    url = f"{endpoint}?{query_string}"
    print(f"url: {url}")
    resp = requests.post(url, headers=headers)
    return resp.json()

# ---------------------------------------------------
# 2) ดึง Kline 7 วัน (Daily) BTC/THB
# ---------------------------------------------------
def get_kline_7days_btcthb():
    """
    ดึงข้อมูล Kline ระยะ 1 วัน (1d) ย้อนหลัง 7 วัน ของคู่ BTCTHB
    Endpoint (คล้าย Binance Global): GET /api/v1/klines?symbol=BTCTHB&interval=1d&limit=7
    * ตรวจสอบว่า Binance TH รองรับหรือไม่
    """
    url = f"{BASE_URL}/api/v1/klines?symbol=BTCTHB&interval=1d&limit=7"
    resp = requests.get(url)
    data = resp.json()  # เป็น list ของ list [[openTime, open, high, low, close, ...], ...]
    # สร้าง DataFrame สำหรับคำนวณ MACD
    columns = ["openTime","Open","High","Low","Close","Volume","closeTime","quoteAssetVolume","trades","takerBaseVol","takerQuoteVol","ignore"]
    df = pd.DataFrame(data, columns=columns)
    df["Close"] = df["Close"].astype(float)
    return df

# ---------------------------------------------------
# 3) ฟังก์ชันคำนวณ MACD + สัญญาณ Cross
# ---------------------------------------------------
def compute_macd(df, fast=12, slow=26, signal=9):
    df["ema_fast"] = df["Close"].ewm(span=fast, adjust=False).mean()
    df["ema_slow"] = df["Close"].ewm(span=slow, adjust=False).mean()
    df["MACD"] = df["ema_fast"] - df["ema_slow"]
    df["Signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["Hist"] = df["MACD"] - df["Signal"]
    return df

def get_macd_signal(df):
    """
    ดูการ Cross ของ Histogram
    คืนค่า +1 (Cross ขึ้น), -1 (Cross ลง), 0 (ไม่มี)
    โดยดูจาก 2 แท่งท้ายสุด
    """
    if len(df) < 2:
        return 0
    prev_hist = df["Hist"].iloc[-2]
    curr_hist = df["Hist"].iloc[-1]
    if prev_hist < 0 and curr_hist > 0:
        return +1
    elif prev_hist > 0 and curr_hist < 0:
        return -1
    else:
        return 0

# ---------------------------------------------------
# 4) ฟังก์ชัน Rebalance 50:50
# ---------------------------------------------------
def rebalance_50_50_btcthb():
    account_data = get_account_info()
    balances = account_data.get("balances", [])
    free_btc = 0.0
    free_thb = 0.0
    for b in balances:
        if b["asset"] == "BTC":
            free_btc = float(b["free"])
        elif b["asset"] == "THB":
            free_thb = float(b["free"])

    # ดึงราคาล่าสุด (อาจดึงจาก ticker)
    # หรือจะใช้ close ล่าสุดจาก Kline ก็ได้
    # ตัวอย่าง: GET ticker
    ticker_url = f"{BASE_URL}/api/v1/ticker/price?symbol=BTCTHB"
    r = requests.get(ticker_url)
    ticker_data = r.json()
    btc_price = float(ticker_data.get("price", 0.0))

    total_value_thb = free_thb + (free_btc * btc_price)
    if total_value_thb <= 0:
        print("[Rebalance] No balance to trade.")
        return

    half = 0.5 * total_value_thb
    current_btc_value = free_btc * btc_price
    diff_btc_value = current_btc_value - half

    print(f"[Rebalance] total={total_value_thb:.2f}, free_btc={free_btc}, free_thb={free_thb}, price={btc_price}, diff={diff_btc_value:.2f}")

    if diff_btc_value > 0:
        # ขาย BTC
        btc_to_sell = diff_btc_value / btc_price
        if btc_to_sell > free_btc:
            btc_to_sell = free_btc
        if btc_to_sell > 0.0001:  # ตรวจสอบ min trade
            print(f"SELL BTC => {btc_to_sell:.4f}")
            resp = place_order("BTCTHB", "SELL", "MARKET", round(btc_to_sell, 4))
            print("[Order SELL response]", resp)
        else:
            print("[Rebalance] Not enough BTC to sell or below min threshold.")
    else:
        # diff_btc_value < 0 => ซื้อ BTC
        thb_to_buy = abs(diff_btc_value)
        if thb_to_buy > free_thb:
            thb_to_buy = free_thb
        if thb_to_buy > 300:  # สมมติ minimum 10 THB
            print(f"BUY BTC => {thb_to_buy:.2f} THB")
            resp = place_order("BTCTHB", "BUY", "MARKET", round(thb_to_buy, 2))
            print("[Order BUY response]", resp)
        else:
            print("[Rebalance] Not enough THB to buy or below min threshold.")

def check_and_rebalance_on_start():
    """
    เมื่อเริ่มต้นสคริปต์ ให้เช็คสัดส่วนพอร์ตว่าถึง 50:50 หรือไม่
    ถ้าไม่ -> rebalance ทันที
    """
    account_data = get_account_info()
    balances = account_data.get("balances", [])
    free_btc = 0.0
    free_thb = 0.0
    for b in balances:
        if b["asset"] == "BTC":
            free_btc = float(b["free"])
        elif b["asset"] == "THB":
            free_thb = float(b["free"])

    # ราคาล่าสุด
    ticker_url = f"{BASE_URL}/api/v1/ticker/price?symbol=BTCTHB"
    r = requests.get(ticker_url)
    btc_price = float(r.json().get("price", 0.0))
    print(f"btc_price: {btc_price}")
    total_value_thb = free_thb + (free_btc * btc_price)
    if total_value_thb <= 0:
        print("[Start] No balance.")
        return

    half = 0.5 * total_value_thb
    current_btc_value = free_btc * btc_price

    # ถ้าห่างจาก 50:50 เกิน 1% หรือกำหนด threshold
    ratio_btc = current_btc_value / total_value_thb
    if abs(ratio_btc - 0.5) > 0.01:
        print("[Start] ratio_btc=", ratio_btc, " => rebalance now.")
        rebalance_50_50_btcthb()
    else:
        print("[Start] ratio_btc=", ratio_btc, " => already near 50:50. Skip.")

# ---------------------------------------------------
# 5) Main Loop
# ---------------------------------------------------
def main_loop():
    """
    - เรียก check_and_rebalance_on_start() ทันทีที่เริ่ม
    - จากนั้น วนลูป:
      (a) ดึง Kline 7 วัน
      (b) คำนวณ MACD
      (c) เช็ค cross => ถ้ามีสัญญาณ => rebalance
      (d) sleep 1 นาที
    """
    # (1) Rebalance เมื่อเริ่ม
    check_and_rebalance_on_start()
    print("Start process")
    while True:
        try:
            # (a) ดึง Kline 7 วัน
            df_klines = get_kline_7days_btcthb()
            # (b) คำนวณ MACD
            df_klines = compute_macd(df_klines)
            # (c) ดูสัญญาณ cross
            sig = get_macd_signal(df_klines)
            print(f"sig: {sig}")
            if sig != 0:
                print(f"[MACD Cross] signal = {sig}, => Rebalance!")
                rebalance_50_50_btcthb()
            else:
                print("[MACD Cross] No signal => skip rebalance.")

        except Exception as e:
            print("Error in main_loop:", e)

        # พัก 1 นาที
        time.sleep(60)

if __name__ == "__main__":
    main_loop()
