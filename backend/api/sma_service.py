# backend/api/sma_service.py
import pandas as pd
from datetime import datetime, timedelta
from .crud import get_prices_since

def compute_sma(db, pair, short_window=5, long_window=15, lookback_minutes=60):
    since = datetime.utcnow() - timedelta(minutes=lookback_minutes)
    rows = get_prices_since(db, pair, since)
    if not rows:
        return None
    df = pd.DataFrame([{"ts": r.ts, "price": float(r.price)} for r in rows])
    df = df.set_index("ts").sort_index()
    df['sma_short'] = df['price'].rolling(window=short_window, min_periods=1).mean()
    df['sma_long'] = df['price'].rolling(window=long_window, min_periods=1).mean()
    latest = df.iloc[-1]
    return {
        "pair": pair.upper(),
        "sma_short": float(latest['sma_short']),
        "sma_long": float(latest['sma_long']),
        "latest_price": float(latest['price'])
    }
