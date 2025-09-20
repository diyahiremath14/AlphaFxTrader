# backend/api/load_prices.py
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from .database import SessionLocal, engine, Base
from . import models
from dotenv import load_dotenv
import re

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

CSV_DEFAULT = os.path.join(os.path.dirname(__file__), '..', 'fx_prices.csv')

# Ensure tables exist
Base.metadata.create_all(bind=engine)


def detect_and_drop_leading_index(df):
    """
    If the first column looks like a row index (values are integers, header not 'Date'),
    drop it. Also handle cases like '6 06-01-90' (row number + date) by splitting.
    """
    first_col = df.columns[0]
    # case A: header is unnamed (e.g., 'Unnamed: 0') and values integers -> drop
    if re.match(r'Unnamed', str(first_col), re.I):
        try:
            if pd.to_numeric(df[first_col], errors='coerce').notna().all():
                return df.drop(columns=[first_col])
        except Exception:
            pass

    # case B: first cell contains something like '6 06-01-90' (rownum + date)
    # try to split first column by whitespace if it contains a space and second token looks like date
    sample = str(df.iloc[0, 0])
    if ' ' in sample:
        left, right = sample.split(' ', 1)
        # if left is integer and right looks like a date token
        if left.isdigit():
            # move right into 'Date' column (or merge into second column)
            # replace the first column values with the right part
            df.iloc[:, 0] = df.iloc[:, 0].apply(lambda v: str(v).split(' ', 1)[1] if ' ' in str(v) else v)
            return df

    return df


def _parse_timestamp_col(series):
    # try parsing with dayfirst=True (dd-mm-yy), then fall back to default parsing
    parsed = pd.to_datetime(series, dayfirst=True, errors='coerce')
    # if too many NaT, try without dayfirst
    if parsed.isna().sum() > len(parsed) * 0.5:
        parsed = pd.to_datetime(series, dayfirst=False, errors='coerce')
    return parsed


def _clean_numeric_str(s):
    """Remove commas and percent signs, return float or None. If percent, return fraction (divide by 100)."""
    if s is None:
        return None
    if pd.isna(s):
        return None
    if isinstance(s, (int, float, np.integer, np.floating)):
        return float(s)
    s = str(s).strip()
    if s == '':
        return None
    # percent?
    if s.endswith('%'):
        try:
            return float(s.strip().replace('%', '').replace(',', '')) / 100.0
        except:
            return None
    # remove commas
    s2 = s.replace(',', '')
    # sometimes values like '467%' may be present without percent — but we handle above
    try:
        return float(s2)
    except:
        return None


def _to_native(val):
    """Convert pandas/numpy types to Python native and coerce NaN -> None."""
    if val is None:
        return None
    if isinstance(val, pd.Timestamp):
        return val.to_pydatetime()
    if pd.isna(val):
        return None
    if isinstance(val, (np.generic,)):
        try:
            return val.item()
        except:
            return None
    if isinstance(val, (int, float, str, bool, datetime)):
        return val
    try:
        return str(val)
    except:
        return None


def parse_and_load(csv_path=CSV_DEFAULT, chunk_size=5000, preview=False):
    print("Loading CSV:", csv_path)
    total = 0
    first_chunk = True

    for chunk_idx, chunk in enumerate(pd.read_csv(csv_path, chunksize=chunk_size, dtype=None, low_memory=False)):
        # normalize headers
        chunk.columns = [c.strip() for c in chunk.columns]

        # Detect and fix leading index or combined index+date
        chunk = detect_and_drop_leading_index(chunk)

        # if preview requested, show headers and a few rows and exit
        if preview and first_chunk:
            print("Columns detected:", list(chunk.columns)[:30])
            print(chunk.head(10))
            return

        # rename columns to our model fields (only if they exist)
        mapping = {
            'Date': 'timestamp',
            'Base Currency': 'base_currency',
            'Exchange rate': 'exchange_rate',   # treat as string code
            'Currency pair': 'pair',
            'Open': 'open_price',
            'High': 'high_price',
            'Low': 'low_price',
            'Close': 'close_price',
            'Volume_Ticks': 'volume_ticks',
            'Current Price': 'current_price',
            'Buy/Sell': 'buy_sell',
            'Return': 'return_val',
            'LogReturn': 'log_return',
            'SMA10': 'sma10',
            'SMA50': 'sma50',
            'EMA20': 'ema20',
            'ATR14': 'atr14',
            'RSI14': 'rsi14',
            'BBand_Upper': 'bband_upper',
            'BBand_Lower': 'bband_lower',
            'Volatility20': 'volatility20'
        }
        # Only rename columns that exist in chunk
        present_map = {k: v for k, v in mapping.items() if k in chunk.columns}
        chunk = chunk.rename(columns=present_map)

        # parse timestamp robustly if present
        if 'timestamp' in chunk.columns:
            chunk['timestamp'] = _parse_timestamp_col(chunk['timestamp'])
            # drop rows without a valid timestamp
            chunk = chunk[chunk['timestamp'].notnull()]

        # Build mappings, cleaning numeric & percent fields explicitly
        mappings = []
        for _, row in chunk.iterrows():
            # Clean / convert values
            exchange_rate_val = row.get('exchange_rate')
            if pd.isna(exchange_rate_val):
                exchange_rate_val = None
            else:
                exchange_rate_val = str(exchange_rate_val).strip()

            mp = {
                'timestamp': _to_native(row.get('timestamp')),
                'base_currency': _to_native(row.get('base_currency')),
                'exchange_rate': exchange_rate_val,
                'pair': _to_native(row.get('pair')),
                'open_price': _clean_numeric_str(row.get('open_price')),
                'high_price': _clean_numeric_str(row.get('high_price')),
                'low_price': _clean_numeric_str(row.get('low_price')),
                'close_price': _clean_numeric_str(row.get('close_price')),
                'volume_ticks': None if pd.isna(row.get('volume_ticks')) or str(row.get('volume_ticks')).strip() == '' else int(float(str(row.get('volume_ticks')).replace(',', ''))),
                'current_price': _clean_numeric_str(row.get('current_price')),
                'buy_sell': None if pd.isna(row.get('buy_sell')) else str(row.get('buy_sell')).strip(),
                'return_val': _clean_numeric_str(row.get('return_val')),
                'log_return': _clean_numeric_str(row.get('log_return')),
                'sma10': _clean_numeric_str(row.get('sma10')),
                'sma50': _clean_numeric_str(row.get('sma50')),
                'ema20': _clean_numeric_str(row.get('ema20')),
                'atr14': _clean_numeric_str(row.get('atr14')),
                'rsi14': _clean_numeric_str(row.get('rsi14')),
                'bband_upper': _clean_numeric_str(row.get('bband_upper')),
                'bband_lower': _clean_numeric_str(row.get('bband_lower')),
                # treat volatility percent -> fraction (e.g. '467%' -> 4.67)
                'volatility20': _clean_numeric_str(row.get('volatility20')),
            }
            mappings.append(mp)

        if not mappings:
            continue

        session = SessionLocal()
        try:
            session.bulk_insert_mappings(models.Price, mappings)
            session.commit()
            total += len(mappings)
            print(f"[chunk {chunk_idx}] Inserted {len(mappings)} rows (total {total})")
        except SQLAlchemyError as e:
            session.rollback()
            print("[chunk {}] Error inserting chunk: {}".format(chunk_idx, str(e)))
        finally:
            session.close()

        first_chunk = False

    print("Finished loading. Total rows inserted:", total)


if __name__ == "__main__":
    # allow a 'preview' mode if called with --preview
    args = sys.argv[1:]
    preview = False
    path = CSV_DEFAULT
    if args:
        for a in args:
            if a == "--preview":
                preview = True
            else:
                path = a
    parse_and_load(path, preview=preview)
