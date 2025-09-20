import requests
import pandas as pd
import time
import random
import mysql.connector
from datetime import datetime

# ---------------- PARAMETERS ----------------
BASE_CURRENCY = "USD"
TARGET_CURRENCY = "EUR"
WINDOW_SMA = 5
WINDOW_RSI = 14
WINDOW_BB = 5
BB_K = 2
FETCH_INTERVAL = 5   # seconds between API calls
MAX_HISTORY = 100    # max rows to keep in DataFrame

# Initialize empty DataFrame
df = pd.DataFrame(columns=['Rate', 'SMA', 'RSI', 'BB_SMA', 'BB_STD', 'BB_upper', 'BB_lower', 'Signal'])

# ---------------- DB CONNECTION ----------------
import pymysql

db = pymysql.connect(
    host="localhost",
    user="root",
    password="moonChar",
    database="forexdb"

)
cursor = db.cursor()

cursor = db.cursor()

# Create table if not exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS forex_signals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    rate FLOAT NOT NULL,
    sma FLOAT,
    rsi FLOAT,
    bb_sma FLOAT,
    bb_std FLOAT,
    bb_upper FLOAT,
    bb_lower FLOAT,
    trade_signal VARCHAR(10)
)
""")

# ---------------- HELPER FUNCTIONS ----------------
def get_latest_rate(base="USD", target="EUR"):
    """Fetch latest exchange rate from the API and add small random fluctuation."""
    url = f"https://api.exchangerate-api.com/v4/latest/{base}"
    try:
        response = requests.get(url)
        data = response.json()
        rate = data['rates'][target]
        # Add small fluctuation to simulate market
        rate += random.uniform(-0.002, 0.002)
        return round(rate, 5)
    except Exception as e:
        print("Error fetching rate:", e)
        return round(0.85 + random.uniform(-0.002, 0.002), 5)

def compute_RSI(series, window=14):
    """Compute Relative Strength Index."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=window, min_periods=1).mean()
    avg_loss = loss.rolling(window=window, min_periods=1).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def generate_signal(row):
    """Generate simple trading signal based on SMA and RSI."""
    if pd.isna(row['SMA']) or pd.isna(row['RSI']):
        return "HOLD"
    if row['Rate'] > row['SMA'] and row['RSI'] < 70:
        return "BUY"
    elif row['Rate'] < row['SMA'] and row['RSI'] > 30:
        return "SELL"
    else:
        return "HOLD"

def save_to_db(row):
    """Save row into MySQL database."""
    sql = """
    INSERT INTO forex_signals 
    (timestamp, rate, sma, rsi, bb_sma, bb_std, bb_upper, bb_lower, trade_signal)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        float(row['Rate']),
        None if pd.isna(row['SMA']) else float(row['SMA']),
        None if pd.isna(row['RSI']) else float(row['RSI']),
        None if pd.isna(row['BB_SMA']) else float(row['BB_SMA']),
        None if pd.isna(row['BB_STD']) else float(row['BB_STD']),
        None if pd.isna(row['BB_upper']) else float(row['BB_upper']),
        None if pd.isna(row['BB_lower']) else float(row['BB_lower']),
        row['Signal']
    )
    cursor.execute(sql, values)
    db.commit()

# ---------------- MAIN LOOP ----------------
print("Starting live exchange rate monitoring...")

try:
    while True:
        # Step 1: Get latest rate
        latest_rate = get_latest_rate(BASE_CURRENCY, TARGET_CURRENCY)

        # Step 2: Append to DataFrame
        df = pd.concat([df, pd.DataFrame({'Rate': [latest_rate]})], ignore_index=True)

        # Keep only last MAX_HISTORY rows
        if len(df) > MAX_HISTORY:
            df = df.iloc[-MAX_HISTORY:]

        # Step 3: Calculate SMA
        df['SMA'] = df['Rate'].rolling(window=WINDOW_SMA).mean()

        # Step 4: Calculate RSI
        df['RSI'] = compute_RSI(df['Rate'], WINDOW_RSI)

        # Step 5: Calculate Bollinger Bands
        df['BB_SMA'] = df['Rate'].rolling(window=WINDOW_BB).mean()
        df['BB_STD'] = df['Rate'].rolling(window=WINDOW_BB).std()
        df['BB_upper'] = df['BB_SMA'] + BB_K * df['BB_STD']
        df['BB_lower'] = df['BB_SMA'] - BB_K * df['BB_STD']

        # Step 6: Generate trading signal
        df['Signal'] = df.apply(generate_signal, axis=1)

        # Step 7: Get latest row
        latest_row = df.tail(1).iloc[0]
        print(latest_row)

        # Step 8: Save to DB
        save_to_db(latest_row)

        # Wait for next fetch
        time.sleep(FETCH_INTERVAL)

except KeyboardInterrupt:
    print("Stopping live monitoring.")
    cursor.close()
    db.close()
