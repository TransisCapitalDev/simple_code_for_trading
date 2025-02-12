import requests
import csv
import time
import os
from datetime import datetime, timedelta

def fetch_klines(symbol, interval, startTime=None, endTime=None, limit=1000):
    # Construct the URL with the provided parameters.
    url = f"https://api.binance.th/api/v1/klines?symbol={symbol}&interval={interval}&limit={limit}&startTime={startTime}&endTime={endTime}"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Error fetching data: {response.text}")
    return response.json()

def initialize_csv(filename):
    header = [
        "Open Time", "Open", "High", "Low", "Close", "Volume", 
        "Close Time", "Quote Asset Volume", "Number of Trades", 
        "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore"
    ]
    # Create the CSV file and write the header if it doesn't exist.
    if not os.path.exists(filename):
        with open(filename, "w", newline="") as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(header)

def append_to_csv(data, filename):
    with open(filename, "a", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerows(data)

if __name__ == "__main__":
    symbol = "BTCTHB"    # Set your trading pair
    interval = "15m"     # Candle interval (e.g., "1m", "15m", "1h", etc.)
    csv_filename = "klines.csv"
    initialize_csv(csv_filename)

    # Define the starting date (January 1, 2024) and get today's date.
    start_date = datetime(2024, 1, 1)
    today = datetime.now()  # This returns the current date and time.
    
    # Loop day-by-day; note that this will fetch full day data up until yesterday if today's data is incomplete.
    current_date = start_date
    while current_date < today:
        # Define the start and end of the day in epoch milliseconds.
        start_time_ms = int(current_date.timestamp() * 1000)
        next_date = current_date + timedelta(days=1)
        end_time_ms = int(next_date.timestamp() * 1000)
        
        try:
            print(f"Fetching data for {current_date.strftime('%Y-%m-%d')}")
            data = fetch_klines(symbol, interval, startTime=start_time_ms, endTime=end_time_ms, limit=1000)
            if data:
                append_to_csv(data, csv_filename)
                print(f"Appended {len(data)} candles for {current_date.strftime('%Y-%m-%d')}")
            else:
                print(f"No data returned for {current_date.strftime('%Y-%m-%d')}")
        except Exception as e:
            print(f"Error on {current_date.strftime('%Y-%m-%d')}: {e}")
        
        # Pause briefly to avoid hitting rate limits.
        time.sleep(1)
        # Move to the next day.
        current_date = next_date

    print("Data fetching completed.")
