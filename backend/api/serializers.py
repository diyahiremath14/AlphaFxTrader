# backend/api/serializers.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FXRateIn(BaseModel):
    pair: str
    price: float

class FXRateOut(FXRateIn):
    ts: datetime

class SMAOut(BaseModel):
    pair: str
    sma_short: Optional[float]
    sma_long: Optional[float]
    latest_price: float

class TradeIn(BaseModel):
    pair: str
    action: str  # BUY/SELL
    volume: float

class TradeOut(TradeIn):
    id: int
    price: float
    status: str
    ts: datetime
