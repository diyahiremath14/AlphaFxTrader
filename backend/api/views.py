# backend/api/views.py
import os
import asyncio
from fastapi import FastAPI, Depends, HTTPException, WebSocket
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from .database import SessionLocal, engine, Base
from . import models, crud, sma_service, broadcast, serializers

# load env from backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# create tables if not present
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AlphaFxTrader API")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# internal ingest endpoint used by simulator or adapter
@app.post("/internal/ingest_price", status_code=201)
async def ingest_price(payload: serializers.FXRateIn, db: Session = Depends(get_db)):
    obj = crud.insert_price(db, payload.pair, payload.price)
    msg = {"type":"price_update", "pair": obj.pair, "price": float(obj.price), "ts": str(obj.ts)}
    # fire-and-forget broadcast
    asyncio.create_task(broadcast.manager.broadcast_json(msg))
    return {"ok": True, "inserted_id": obj.id}

@app.get("/prices")
def get_prices(pair: str = "EURUSD", db: Session = Depends(get_db)):
    latest = crud.get_latest_price(db, pair)
    if not latest:
        raise HTTPException(status_code=404, detail="No price found")
    return {"pair": latest.pair, "price": float(latest.price), "ts": str(latest.ts)}

@app.get("/sma", response_model=serializers.SMAOut)
def get_sma(pair: str = "EURUSD", short_window:int=5, long_window:int=15, db: Session = Depends(get_db)):
    out = sma_service.compute_sma(db, pair, short_window=short_window, long_window=long_window, lookback_minutes=60)
    if out is None:
        raise HTTPException(status_code=404, detail="Not enough data")
    return out

@app.post("/trade", response_model=serializers.TradeOut)
def execute_trade(payload: serializers.TradeIn, db: Session = Depends(get_db)):
    max_vol = float(os.getenv("MAX_DAILY_VOLUME", "10000000"))
    total_today = crud.get_total_traded_volume_today(db)
    if total_today + payload.volume > max_vol:
        raise HTTPException(status_code=403, detail="Daily trading volume limit reached")

    latest = crud.get_latest_price(db, payload.pair)
    if not latest:
        raise HTTPException(status_code=404, detail="No price available to execute trade")
    price = float(latest.price)
    tr = crud.insert_trade(db, payload.pair, payload.action, price, payload.volume, status="Filled")
    # broadcast trade
    msg = {"type":"trade", "id": tr.id, "pair": tr.pair, "action": tr.action, "price": float(tr.price), "volume": float(tr.volume), "ts": str(tr.ts)}
    asyncio.create_task(broadcast.manager.broadcast_json(msg))
    return tr

@app.get("/history")
def get_history(limit:int = 100, db: Session = Depends(get_db)):
    rows = crud.get_trade_history(db, limit)
    return [{"id": r.id, "pair": r.pair, "action": r.action, "price": float(r.price), "volume": float(r.volume), "status": r.status, "ts": str(r.ts)} for r in rows]

# WebSocket endpoint for live feed (prices + trades)
@app.websocket("/ws/prices")
async def ws_prices(websocket: WebSocket):
    await broadcast.manager.connect(websocket)
    try:
        while True:
            # we expect the client to send pings; if not, this will block until client sends something
            await websocket.receive_text()
    except Exception:
        broadcast.manager.disconnect(websocket)
