# backend/api/crud.py
from sqlalchemy.orm import Session
from . import models
from sqlalchemy import func
from datetime import datetime

def insert_price(db: Session, pair: str, price: float):
    obj = models.FXRate(pair=pair.upper(), price=price)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def get_latest_price(db: Session, pair: str):
    return db.query(models.FXRate).filter(models.FXRate.pair==pair.upper()).order_by(models.FXRate.ts.desc()).first()

def get_prices_since(db: Session, pair: str, since_ts):
    return db.query(models.FXRate).filter(models.FXRate.pair==pair.upper(), models.FXRate.ts>=since_ts).order_by(models.FXRate.ts.asc()).all()

def insert_trade(db: Session, pair: str, action: str, price: float, volume: float, status="Filled"):
    tr = models.Trade(pair=pair.upper(), action=action.upper(), price=price, volume=volume, status=status)
    db.add(tr)
    db.commit()
    db.refresh(tr)
    return tr

def get_trade_history(db: Session, limit:int=100):
    return db.query(models.Trade).order_by(models.Trade.ts.desc()).limit(limit).all()

def get_total_traded_volume_today(db: Session):
    today = datetime.utcnow().date()
    start = datetime(today.year, today.month, today.day)
    total = db.query(func.coalesce(func.sum(models.Trade.volume),0)).filter(models.Trade.ts>=start).scalar()
    return float(total or 0.0)
