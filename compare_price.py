import requests
import time
def get_orderbook_binance(symbol, binance_endpoint_depth):
    """
    Retrieves the order book from Binance.
    
    :param symbol: The trading symbol (e.g., "BTCUSDT").
    :param binance_endpoint_depth: Base endpoint URL for Binance order book.
    :return: Parsed JSON order book data or None if an error occurs.
    """
    url = f"{binance_endpoint_depth}?symbol={symbol}"
    headers = {
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
        order_book_data = response.json()
        return order_book_data
    except requests.exceptions.RequestException as e:
        print("Binance request error:", e)
        return None

def get_orderbook_bitkub(symbol, bitkub_endpoint_depth):
    """
    Retrieves the order book from Bitkub.
    
    :param symbol: The trading symbol (e.g., "BTCUSDT").
    :param bitkub_endpoint_depth: Base endpoint URL for Bitkub order book.
    :return: Parsed JSON order book data or None if an error occurs.
    """
    url = f"{bitkub_endpoint_depth}?sym={symbol}&lmt=1000"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        order_book_data = response.json()
        return order_book_data
    except requests.exceptions.RequestException as e:
        print("Bitkub request error:", e)
        return None

def get_orderbook_orbix(symbol, orbix_trade_endpoint_depth):
    """
    Retrieves the order book from Orbix.
    
    :param symbol: The trading symbol (e.g., "BTCUSDT").
    :param orbix_trade_endpoint_depth: Base endpoint URL for Orbix order book.
    :return: Parsed JSON order book data or None if an error occurs.
    """
    url = f"{orbix_trade_endpoint_depth}?symbol={symbol}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        order_book_data = response.json()
        return order_book_data
    except requests.exceptions.RequestException as e:
        print("Orbix request error:", e)
        return None

def get_mid_price(order_book):
    """
    Computes the mid price given an order book.
    Assumes order_book has 'bids' and 'asks' keys with a list of [price, quantity] entries.
    """
    try:
        bids = order_book.get("bids", [])
        asks = order_book.get("asks", [])
        
        if not bids or not asks:
            print("Empty bids or asks.")
            return None
        
        # Assume the first bid is the highest bid and the first ask is the lowest ask.
        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
        mid_price = (best_bid + best_ask) / 2.0
        return mid_price
    except Exception as e:
        print("Error computing mid price:", e)
        return None


def main():
    

    # Replace these endpoint URLs with your actual configuration endpoints.
    binance_endpoint_depth = "https://api.binance.th/api/v1/depth"
    bitkub_endpoint_depth = "https://api.bitkub.com/api/market/depth"
    orbix_trade_endpoint_depth = "https://www.orbixtrade.com/api/v3/depth"
    
    # Retrieve order book data from each exchange.
    binance_orderbook = get_orderbook_binance("BTCTHB", binance_endpoint_depth)
    bitkub_orderbook = get_orderbook_bitkub("THB_BTC", bitkub_endpoint_depth)
    orbix_orderbook = get_orderbook_orbix("BTC_THB", orbix_trade_endpoint_depth)

    # Compute the mid price for each order book.
    binance_mid = get_mid_price(binance_orderbook) if binance_orderbook else None
    bitkub_mid = get_mid_price(bitkub_orderbook) if bitkub_orderbook else None
    orbix_mid = get_mid_price(orbix_orderbook) if orbix_orderbook else None

    # Print the mid prices.
    print("Price (Binance):", binance_mid)
    print("Price (Bitkub) :", bitkub_mid)
    print("Price (Orbix)  :", orbix_mid)


if __name__ == "__main__":
    while True:
        print("--------------------------------")
        print("Start")
        main()
        print("--------------------------------")
        time.sleep(1)