import os
from flask import Flask, jsonify
from binance.client import Client
import pandas as pd
import numpy as np

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    from dotenv import load_dotenv
    load_dotenv(dotenv_path)

app = Flask(__name__)

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

if not API_KEY or not API_SECRET:
    raise ValueError("API keys not found! Set them in a .env file or environment variables.")

client = Client(API_KEY, API_SECRET)

def get_btc_data():
    try:
        klines = client.get_klines(symbol="BTCUSDT", interval=Client.KLINE_INTERVAL_1MINUTE, limit=500)
        df = pd.DataFrame(klines, columns=['time','open','high','low','close','volume', '_', '_', '_', '_', '_', '_'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        df.set_index('time', inplace=True)
        df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
        return df
    except Exception as e:
        return str(e)

def find_major_support_resistance(df):
    rolling_max = df['high'].rolling(window=50, min_periods=1).max()
    rolling_min = df['low'].rolling(window=50, min_periods=1).min()
    return rolling_min.iloc[-1], rolling_max.iloc[-1]

def calculate_anchored_vwap(df, anchor_points):
    vwap = np.full(len(df), np.nan)
    for anchor in anchor_points:
        if anchor not in df.index:
            continue
        idx = df.index.get_loc(anchor)
        cum_vol = np.cumsum(df['volume'].iloc[idx:])
        cum_vp = np.cumsum(df['close'].iloc[idx:] * df['volume'].iloc[idx:])
        vwap[idx:] = cum_vp / cum_vol
    return vwap.tolist()

@app.route('/')
def home():
    return "BTC Trading Bot is running! Go to /data to see market data."

@app.route('/data')
def data():
    df = get_btc_data()
    if isinstance(df, str):  # Error message case
        return jsonify({"error": df})
    
    support, resistance = find_major_support_resistance(df)
    anchor_points = [df['high'].idxmax(), df['low'].idxmin()]
    vwap_values = calculate_anchored_vwap(df, anchor_points)
    return jsonify({
        "time": df.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
        "open": df['open'].tolist(),
        "high": df['high'].tolist(),
        "low": df['low'].tolist(),
        "close": df['close'].tolist(),
        "volume": df['volume'].tolist(),
        "support": support,
        "resistance": resistance,
        "vwap": vwap_values
    })

if __name__ == '__main__':
    app.run(debug=True)
