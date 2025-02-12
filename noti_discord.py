import requests
import time
from datetime import datetime, timedelta

def fetch_klines(symbol, interval, startTime=None, endTime=None, limit=1000):
    # Construct the URL with the provided parameters.
    url = (f"https://api.binance.th/api/v1/klines"
           f"?symbol={symbol}&interval={interval}&limit={limit}"
           f"&startTime={startTime}&endTime={endTime}")
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Error fetching data: {response.text}")
    return response.json()

def send_discord_notification(message, webhook_url):
    data = {"content": message}
    response = requests.post(webhook_url, json=data)
    if response.status_code != 204:
        print(f"Failed to send Discord notification: {response.text}")

if __name__ == "__main__":
    symbol = "BTCTHB"         # Set your trading pair
    interval = "15m"          # Candle interval (e.g., "1m", "15m", "1h", etc.)
    discord_webhook_url = "https://discord.com/api/webhooks/xxxxxxxxx"  # Replace with your Discord webhook URL

    # Define the starting date (January 1, 2024) and get today's date.
    start_date = datetime(2025, 1, 1)
    today = datetime.now()
    
    # We'll accumulate all fetched candles in this list.
    history = []
    # This variable stores the previous difference (MA20 - MA50) for crossover detection.
    last_diff = None

    current_date = start_date
    while current_date < today:
        # Define the start and end of the day in epoch milliseconds.
        start_time_ms = int(current_date.timestamp() * 1000)
        next_date = current_date + timedelta(days=1)
        end_time_ms = int(next_date.timestamp() * 1000)
        
        try:
            print(f"Fetching data for {current_date.strftime('%Y-%m-%d')}")
            day_data = fetch_klines(symbol, interval, startTime=start_time_ms, endTime=end_time_ms, limit=1000)
            if day_data:
                for candle in day_data:
                    # Append the new candle to history.
                    history.append(candle)
                    
                    # Clear history: keep only candles within the last 30 days of the current candle.
                    thirty_days_ms = 30 * 24 * 3600 * 1000
                    threshold = candle[0] - thirty_days_ms
                    history = [h for h in history if h[0] >= threshold]
                    
                    # Ensure we have enough data points to compute MA20 and MA50.
                    if len(history) >= 50:
                        # Extract the closing prices from the last 20 and 50 candles.
                        close_prices_20 = [float(c[4]) for c in history[-20:]]
                        close_prices_50 = [float(c[4]) for c in history[-50:]]
                        ma20 = sum(close_prices_20) / 20
                        ma50 = sum(close_prices_50) / 50
                        diff = ma20 - ma50
                        
                        # Check for a crossover if we have a previous diff.
                        if last_diff is not None and diff * last_diff < 0:
                            candle_time = datetime.fromtimestamp(candle[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                            if diff > 0:
                                message = (f"========= \n========= \nBullish crossover detected on {candle_time}: "
                                           f"\nMA20 ({ma20:.2f}) crossed above MA50 ({ma50:.2f}).")
                            else:
                                message = (f"========= \n========= \nBearish crossover detected on {candle_time}: "
                                           f"\nMA20 ({ma20:.2f}) crossed below MA50 ({ma50:.2f}).")
                            print(message)
                            send_discord_notification(message, discord_webhook_url)
                        last_diff = diff
                print(f"Processed {len(day_data)} candles for {current_date.strftime('%Y-%m-%d')}\n\n")
            else:
                print(f"No data returned for {current_date.strftime('%Y-%m-%d')}")
        except Exception as e:
            print(f"Error on {current_date.strftime('%Y-%m-%d')}: {e}")
        
        # Pause briefly to avoid hitting rate limits.
        time.sleep(1)
        # Move to the next day.
        current_date = next_date

    print("Data processing completed.")
