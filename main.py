import time
import requests
import pandas as pd
from ta.trend import EMAIndicator, ADXIndicator
from ta.volatility import AverageTrueRange
from telegram import Bot
from flask import Flask

# === TELEGRAM SETUP ===
bot_token = '7963033521:AAHSq4KWwS3Yg9ppA0AtwNUvNpYlrVGHYak'
chat_id = '8132192522'
bot = Bot(token=bot_token)

# === BALANCE & CONFIG ===
balance = 500.0
RISK_PER_TRADE = 10
REWARD_PER_TRADE = 10
symbols = ['XRP-USDT', 'LINK-USDT', 'ADA-USDT', 'DOGE-USDT', 'BNB-USDT', 'LTC-USDT', 'DOT-USDT']
active_trades = {}

# === FLASK WEB SERVER ===
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot is running!"

# === CANDLES FETCH ===
def fetch_kucoin_candles(symbol):
    url = f'https://api.kucoin.com/api/v1/market/candles?type=5min&symbol={symbol}'
    try:
        res = requests.get(url)
        data = res.json()['data']
        data.reverse()
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'close', 'high', 'low', 'volume', 'turnover'])
        df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)
        df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='ms')
        return df
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

# === STRATEGY CHECK ===
def check_signals(df):
    ema = EMAIndicator(df['close'], window=20).ema_indicator()
    atr = AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()
    adx = ADXIndicator(df['high'], df['low'], df['close'], window=14).adx()

    signals = {}
    c = df['close'].iloc[-1]
    prev_c = df['close'].iloc[-2]
    ema_now = ema.iloc[-1]
    ema_prev = ema.iloc[-2]
    atr_now = atr.iloc[-1]
    adx_now = adx.iloc[-1]

    if adx_now > 20:
        if c < ema_now and prev_c > ema_prev:
            signals['short'] = {'entry': c, 'sl': c + atr_now, 'tp': c - atr_now, 'atr': atr_now}
    return signals

# === MAIN LOOP ===
def run_bot():
    global balance
    while True:
        print(f"🔄 Monitoring... Balance: ${balance:.2f}")
        for symbol in symbols:
            df = fetch_kucoin_candles(symbol)
            if df is None:
                continue

            if symbol in active_trades:
                trade = active_trades[symbol]
                price = df['close'].iloc[-1]
                if trade['direction'] == 'short':
                    if price <= trade['tp']:
                        balance += REWARD_PER_TRADE
                        bot.send_message(chat_id=chat_id, text=f"✅ TP HIT (SHORT) {symbol} @ {price}\\nBalance: ${balance:.2f}")
                        del active_trades[symbol]
                    elif price >= trade['sl']:
                        balance -= RISK_PER_TRADE
                        bot.send_message(chat_id=chat_id, text=f"❌ SL HIT (SHORT) {symbol} @ {price}\\nBalance: ${balance:.2f}")
                        del active_trades[symbol]
                continue

            signals = check_signals(df)
            if 'short' in signals:
                s = signals['short']
                active_trades[symbol] = {**s, 'direction': 'short'}
                bot.send_message(chat_id=chat_id, text=f"📉 SHORT SIGNAL: {symbol}\\nEntry: {s['entry']}\\nTP: {s['tp']}\\nSL: {s['sl']}")

        time.sleep(1)

# === RUN SERVER AND BOT ===
import threading
threading.Thread(target=run_bot).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
