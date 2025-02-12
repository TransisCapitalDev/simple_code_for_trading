import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------
# 1) ดาวน์โหลดข้อมูลราคา BTC-USD จาก yfinance
# ---------------------------------------------------
df = yf.download('BTC-USD', start='2022-01-01', end='2025-01-01')

# รีเซ็ต index -> ทำให้ df.index เป็นตัวเลข 0..N-1
df.reset_index(inplace=True)

# ---------------------------------------------------
# 2) ฟังก์ชันคำนวณ MACD
# ---------------------------------------------------
def compute_macd(data, fastperiod=12, slowperiod=26, signalperiod=9):
    data['EMA_fast'] = data['Close'].ewm(span=fastperiod, adjust=False).mean()
    data['EMA_slow'] = data['Close'].ewm(span=slowperiod, adjust=False).mean()
    
    data['MACD'] = data['EMA_fast'] - data['EMA_slow']
    data['Signal'] = data['MACD'].ewm(span=signalperiod, adjust=False).mean()
    data['Hist'] = data['MACD'] - data['Signal']
    
    return data

# ---------------------------------------------------
# 3) ฟังก์ชันสร้างสัญญาณ MACD จาก Histogram Cross
# ---------------------------------------------------
def generate_macd_signal(data):
    signals = []
    hist_list = data['Hist'].values
    
    for i in range(1, len(hist_list)):
        prev_hist = hist_list[i-1]
        curr_hist = hist_list[i]
        
        if prev_hist < 0 and curr_hist > 0:
            signals.append(+1)  # ข้ามจากลบเป็นบวก (Buy)
        elif prev_hist > 0 and curr_hist < 0:
            signals.append(-1)  # ข้ามจากบวกเป็นลบ (Sell)
        else:
            signals.append(0)
    
    # แถวแรกยังไม่รู้ให้ 0
    signals.insert(0, 0)
    return signals

# คำนวณ MACD และสร้างคอลัมน์สัญญาณ
df = compute_macd(df)
df['Signal_MACD'] = generate_macd_signal(df)

# ---------------------------------------------------
# 4) ตั้งค่าพอร์ตเริ่มต้น
# ---------------------------------------------------
initial_usdt = 10000.0
initial_btc  = 0.0

current_usdt = initial_usdt
current_btc  = initial_btc

portfolio_values = []
usdt_history = []
# ---------------------------------------------------
# 5) Backtest Loop ด้วย iloc[i]
# ---------------------------------------------------
for i in range(len(df)):
    price_btc   = df.iloc[i]['Close']       # ได้ float
    signal_macd = df.iloc[i]['Signal_MACD'].iloc[0] # ได้ int/float (สเกลาร์)
    
    # คำนวณมูลค่าพอร์ต (USDT)
    total_value = current_usdt + current_btc * price_btc
    
    # ถ้ามีสัญญาณ (±1) -> Rebalance 50:50
    if signal_macd != 0:
        target_value_each = 0.5 * total_value
        current_btc_value = current_btc * price_btc
        diff_btc_value = current_btc_value - target_value_each
        
        # Debug print (ถ้าต้องการดูค่าใน console)
        
        print(f"current_btc_value: {current_btc_value}, target_value_each: {target_value_each}, diff_btc_value: {diff_btc_value}")
        if diff_btc_value.iloc[0]  > 0:
            # BTC เกิน => ขายส่วนต่าง
            btc_to_sell = diff_btc_value.iloc[0] / price_btc
            current_btc -= btc_to_sell
            current_usdt += diff_btc_value.iloc[0]
        else:
            # BTC ขาด => ซื้อ
            buy_in_value = abs(diff_btc_value.iloc[0])
            if current_usdt >= buy_in_value:
                btc_to_buy = buy_in_value / price_btc
                current_btc += btc_to_buy
                current_usdt -= buy_in_value
            else:
                # ถ้า USDT ไม่พอ ก็ใส่หมด
                btc_to_buy = current_usdt / price_btc
                current_btc += btc_to_buy
                current_usdt = 0.0
    
    # เก็บมูลค่าพอร์ตในแต่ละวัน
    portfolio_values.append(current_usdt + current_btc * price_btc)
    usdt_history.append(current_usdt)

# ---------------------------------------------------
# 6) Plot มูลค่าพอร์ต + ราคา BTC
# ---------------------------------------------------
dates = df['Date']

# -- สร้าง Subplot สองส่วนในหนึ่ง Figure --
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

# (A) Plot Portfolio Value และ ราคา BTC บนกราฟบน (ax1) แบบ 2 แกน (ซ้าย-ขวา)
ax1.set_title('Portfolio Value vs. BTC Price')

# 1) แกนซ้าย = Portfolio Value (USDT)
color_port = 'tab:blue'
ax1.set_ylabel('Portfolio Value (USDT)', color=color_port)
ax1.plot(dates, portfolio_values, color=color_port, label='Portfolio Value')
ax1.tick_params(axis='y', labelcolor=color_port)

# 2) แกนขวา = BTC Price
ax1b = ax1.twinx()
color_btc = 'tab:orange'
ax1b.set_ylabel('BTC Price (USD)', color=color_btc)
ax1b.plot(dates, df['Close'], color=color_btc, label='BTC Price', alpha=0.7)
ax1b.tick_params(axis='y', labelcolor=color_btc)

# (B) Plot Cashflow (ปริมาณ USDT ที่ถือ) บนกราฟล่าง (ax2)
ax2.set_title('Cashflow (USDT Holdings Over Time)')
ax2.plot(dates, usdt_history, color='green', label='USDT Holdings')
ax2.set_xlabel('Date')
ax2.set_ylabel('USDT Amount')
ax2.grid(True)
ax2.legend()

plt.tight_layout()
plt.show()