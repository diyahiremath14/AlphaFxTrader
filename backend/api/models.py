# backend/api/models.py
from sqlalchemy import Column, Integer, String, Numeric, TIMESTAMP, func
from .database import Base

class FXRate(Base):
    __tablename__ = "fx_rates"
    id = Column(Integer, primary_key=True, index=True)
    pair = Column(String(10), nullable=False, index=True)
    price = Column(Numeric, nullable=False)
    ts = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    pair = Column(String(10), nullable=False)
    action = Column(String(4), nullable=False)  # BUY / SELL
    price = Column(Numeric, nullable=False)
    volume = Column(Numeric, nullable=False)
    status = Column(String(20), nullable=False)
    ts = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
