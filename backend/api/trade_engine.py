# backend/api/trade_engine.py
from .database import SessionLocal
from . import crud, models
from datetime import datetime
import pandas as pd

def calculate_sma(series, period):
    if len(series) < period:
        return None
    return series[-period:].mean()

def run_sma(strategy_name='SMA_CROSS', lookback=500):
    """
    Query historical close prices per pair, compute SMA10/SMA50, insert trades when crossover detected.
    This is a simple synchronous runner invoked manually or via endpoint.
    """
    session = SessionLocal()
    try:
        # fetch needed data: restrict to last `lookback` rows per pair
        # We'll use a single query ordering by timestamp and then group by pair in pandas
        q = session.query(models.Price.timestamp, models.Price.pair, models.Price.close_price).order_by(models.Price.timestamp.asc())
        df = pd.read_sql(q.statement, session.bind)
        if df.empty:
            print("No price data available")
            return

        # group by pair
        for pair, group in df.groupby('pair'):
            closes = group['close_price'].dropna().astype(float).tolist()
            if len(closes) < 50:
                continue
            import numpy as np
            closes_series = pd.Series(closes)
            sma10 = calculate_sma(closes_series, 10)
            sma50 = calculate_sma(closes_series, 50)
            if sma10 is None or sma50 is None:
                continue

            # current close price
            price = closes[-1]
            trade_type = None
            if sma10 > sma50:
                trade_type = 'BUY'
            elif sma10 < sma50:
                trade_type = 'SELL'

            if trade_type:
                # you should decide volume; use a fixed example volume here
                volume = 100000  # example, adapt as needed or compute dynamic size
                # insert trade via crud (we used insert_trade earlier)
                tr = crud.insert_trade(session, pair, trade_type, price, volume, status="Filled")
                # add strategy metadata: update strategy column
                try:
                    session.query(models.Trade).filter(models.Trade.id==tr.id).update({"strategy": strategy_name})
                    session.commit()
                except Exception:
                    session.rollback()
                print(f"Trade executed: {trade_type} {pair} at {price}")
    finally:
        session.close()
