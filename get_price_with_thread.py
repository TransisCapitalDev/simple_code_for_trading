import threading
import requests
import time

BASE_URL = "https://api.binance.th"
symbols = ["BTCTHB", "ETHTHB", "BNBTHB"]

# A shared dictionary to store symbol -> price
prices = {}

def fetch_price(symbol):
    """Fetch the latest price for a given symbol from Binance TH and store in `prices` dict."""
    url = f"{BASE_URL}/api/v1/ticker/price?symbol={symbol}"
    response = requests.get(url).json()
    price = float(response["price"])
    prices[symbol] = price

def main():
    while True:
        threads = []

        # Create and start a thread for each symbol
        for symbol in symbols:
            thread = threading.Thread(target=fetch_price, args=(symbol,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to finish
        for thread in threads:
            thread.join()

        # Now we can safely print the results after all have completed
        print("All responses received:")
        for symbol in symbols:
            print(f"{symbol}: {prices[symbol]}")
        print("================================================\n")
        time.sleep(30)

if __name__ == "__main__":
    main()
