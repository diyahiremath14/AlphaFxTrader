# backend/api/models.py
from sqlalchemy import Column, Integer, String, Numeric, TIMESTAMP, func, BigInteger
from .database import Base

class FXRate(Base):
    __tablename__ = "fx_rates"
    id = Column(Integer, primary_key=True, index=True)
    pair = Column(String(10), nullable=False, index=True)
    price = Column(Numeric, nullable=False)
    ts = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

class Price(Base):
    __tablename__ = "prices"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    base_currency = Column(String(10), nullable=True)
    # <- make exchange_rate a string (currency code), not numeric
    exchange_rate = Column(String(20), nullable=True)
    pair = Column(String(20), nullable=False, index=True)
    open_price = Column(Numeric(18,6), nullable=True)
    high_price = Column(Numeric(18,6), nullable=True)
    low_price = Column(Numeric(18,6), nullable=True)
    close_price = Column(Numeric(18,6), nullable=True)
    volume_ticks = Column(BigInteger, nullable=True)
    current_price = Column(Numeric(18,6), nullable=True)
    buy_sell = Column(String(10), nullable=True)
    return_val = Column(Numeric(18,6), nullable=True)
    log_return = Column(Numeric(18,6), nullable=True)
    sma10 = Column(Numeric(18,6), nullable=True)
    sma50 = Column(Numeric(18,6), nullable=True)
    ema20 = Column(Numeric(18,6), nullable=True)
    atr14 = Column(Numeric(18,6), nullable=True)
    rsi14 = Column(Numeric(18,6), nullable=True)
    bband_upper = Column(Numeric(18,6), nullable=True)
    bband_lower = Column(Numeric(18,6), nullable=True)
    volatility20 = Column(Numeric(18,6), nullable=True)
class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    pair = Column(String(10), nullable=False)
    action = Column(String(16), nullable=False)  # BUY / SELL
    price = Column(Numeric, nullable=False)
    volume = Column(Numeric, nullable=False)
    status = Column(String(20), nullable=False)
    ts = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    strategy = Column(String(50), nullable=True)
