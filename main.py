import ccxt
import time
import requests
import numpy as np
from datetime import datetime

# --- CONFIG ---
TELEGRAM_TOKEN = '8051044850:AAGF9ID1IvQqXfxESBVKxgEZ_9LpbA-zoiY'
CHAT_ID = '607429363'
CHECK_INTERVAL = 3600  # 1 hour in seconds
SIDEWAYS_TIMEFRAME = '15m'
PUMP_TIMEFRAME = '5m'
EXCHANGE = ccxt.binance()

# --- TOOLS ---
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=payload)

def get_ohlcv(symbol, timeframe, limit=100):
    try:
        data = EXCHANGE.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        return np.array(data)
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

def is_sideways(data):
    closes = data[:, 4]
    upper = np.max(closes[-20:])
    lower = np.min(closes[-20:])
    range_pct = (upper - lower) / lower * 100
    return range_pct < 1.5  # Sideways jika range < 1.5%

def detect_pump(data):
    closes = data[:, 4]
    volumes = data[:, 5]
    avg_vol = np.mean(volumes[-20:])
    vol_now = volumes[-1]
    rsi = compute_rsi(closes)

    if closes[-1] > closes[-2] and rsi[-1] > 65 and vol_now > 1.8 * avg_vol:
        return True
    return False

def compute_rsi(closes, period=14):
    deltas = np.diff(closes)
    seed = deltas[:period]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi = [100. - 100. / (1. + rs)]
    
    for delta in deltas[period:]:
        up_val = max(delta, 0)
        down_val = -min(delta, 0)
        up = (up * (period - 1) + up_val) / period
        down = (down * (period - 1) + down_val) / period
        rs = up / down if down != 0 else 0
        rsi.append(100. - 100. / (1. + rs))

    return rsi

# --- MAIN LOOP ---
sideways_watchlist = []

while True:
    try:
        print(f"[ {datetime.now()} ] Mulai screening...")
        symbols = [m['symbol'] for m in EXCHANGE.load_markets().values() if 
                   m['quote'] == 'USDT' and m['spot'] and not m['symbol'].endswith('UP/USDT')]

        sideways_watchlist.clear()
        for symbol in symbols:
            ohlcv = get_ohlcv(symbol, SIDEWAYS_TIMEFRAME)
            if ohlcv is not None and is_sideways(ohlcv):
                sideways_watchlist.append(symbol)
                print(f"{symbol} terdeteksi sideways")

        for symbol in sideways_watchlist:
            pump_data = get_ohlcv(symbol, PUMP_TIMEFRAME)
            if pump_data is not None and detect_pump(pump_data):
                send_telegram(f"🚀 {symbol} menunjukan potensi pump!")

        print("Selesai 1 loop. Tidur 1 jam...")
        time.sleep(CHECK_INTERVAL)

    except Exception as e:
        print(f"ERROR: {e}")
        send_telegram(f"❌ Bot error: {e}")
        time.sleep(60)
