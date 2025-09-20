import collections
from datetime import datetime
import yfinance as yf
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import threading
import time

# -------- SMA Trading Model --------
class SMA_TradingModel:
    def __init__(self,
                 short_window=5,
                 long_window=15,
                 trade_volume_limit=10_000_000,
                 trade_size=100_000,
                 high_low_window=60):
        self.short_window = short_window
        self.long_window = long_window
        self.trade_volume_limit = trade_volume_limit
        self.trade_size = trade_size
        self.high_low_window = high_low_window
        
        self.price_window_short = collections.deque(maxlen=short_window)
        self.price_window_long = collections.deque(maxlen=long_window)
        self.price_window_high_low = collections.deque(maxlen=high_low_window)
        
        self.position = None
        self.cumulative_volume = 0
        self.trade_log = []
        self.prev_diff = None
        self.purchase_price = None
    
    def add_price(self, price: float):
        self.price_window_short.append(price)
        self.price_window_long.append(price)
        self.price_window_high_low.append(price)
    
    def calculate_sma(self, price_deque):
        if len(price_deque) == 0:
            return None
        return sum(price_deque) / len(price_deque)
    
    def generate_signal(self):
        sma_short = self.calculate_sma(self.price_window_short)
        sma_long = self.calculate_sma(self.price_window_long)
        
        if sma_short is None or sma_long is None:
            return None
        
        current_diff = sma_short - sma_long
        signal = None
        
        if self.prev_diff is not None:
            if self.prev_diff < 0 and current_diff > 0:
                signal = 'BUY'
            elif self.prev_diff > 0 and current_diff < 0:
                signal = 'SELL'
        
        self.prev_diff = current_diff
        return signal
    
    def execute_trade(self, signal):
        if signal is None:
            return
        
        if self.cumulative_volume >= self.trade_volume_limit:
            print("[INFO] Trade volume limit reached. No further trades.")
            return
        
        if signal == 'BUY' and self.position != 'LONG':
            self.purchase_price = self.price_window_short[-1]
            self._log_trade('BUY')
            self.position = 'LONG'
            self.cumulative_volume += self.trade_size
            print(f"[TRADE] BUY executed at {self.purchase_price} for volume {self.trade_size}")
        
        elif signal == 'SELL' and self.position == 'LONG':
            sell_price = self.price_window_short[-1]
            pnl = sell_price - self.purchase_price if self.purchase_price else None
            self._log_trade('SELL')
            self.position = 'SHORT'
            self.cumulative_volume += self.trade_size
            self.purchase_price = None
            print(f"[TRADE] SELL executed at {sell_price} for volume {self.trade_size}, PnL: {pnl}")
        else:
            print(f"[INFO] No trade executed for signal: {signal}")
    
    def _log_trade(self, trade_type):
        trade_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': trade_type,
            'volume': self.trade_size,
            'position': self.position
        }
        self.trade_log.append(trade_record)
        print(f"[LOG] Trade recorded: {trade_record}")
    
    def process_tick(self, price):
        self.add_price(price)
        signal = self.generate_signal()
        self.execute_trade(signal)
    
    def get_high_low(self):
        if not self.price_window_high_low:
            return None, None
        return max(self.price_window_high_low), min(self.price_window_high_low)
    
    def get_average_trade_volume(self):
        if not self.trade_log:
            return 0
        total_volume = sum(trade['volume'] for trade in self.trade_log)
        return total_volume / len(self.trade_log)
    
    def get_current_price(self):
        if not self.price_window_short:
            return None
        return self.price_window_short[-1]
    
    def get_purchase_price(self):
        return self.purchase_price
    
    def get_profit_loss(self):
        current_price = self.get_current_price()
        if self.position == 'LONG' and self.purchase_price is not None and current_price is not None:
            return current_price - self.purchase_price
        return None

# ---------- FastAPI App and Models ----------

app = FastAPI()
sma_model = SMA_TradingModel()

class PriceTick(BaseModel):
    price: float

# Endpoint to submit new price tick manually (optional)
@app.post("/price_tick/")
async def submit_price_tick(tick: PriceTick):
    sma_model.process_tick(tick.price)
    return {"message": "Price tick processed"}

# Endpoint to get current model stats
@app.get("/status/")
async def get_status():
    high, low = sma_model.get_high_low()
    avg_volume = sma_model.get_average_trade_volume()
    current_price = sma_model.get_current_price()
    purchase_price = sma_model.get_purchase_price()
    profit_loss = sma_model.get_profit_loss()
    return {
        "current_price": current_price,
        "high": high,
        "low": low,
        "average_trade_volume": avg_volume,
        "purchase_price": purchase_price,
        "profit_loss": profit_loss,
        "position": sma_model.position,
        "trade_log": sma_model.trade_log[-10:]  # Last 10 trades
    }

# Background thread to fetch live prices from Yahoo Finance for a symbol
def live_price_feed(symbol="EURUSD=X", interval="1m", delay=60):
    """
    Fetches latest price every 'delay' seconds and feeds to SMA model.
    symbol: ticker symbol supported by yfinance
    interval: data interval
    delay: seconds between fetches
    """
    while True:
        data = yf.download(tickers=symbol, period="1d", interval=interval, progress=False)
        if not data.empty:
            last_price = data['Close'].iloc[-1]
            print(f"[YFinance] Latest {symbol} price: {last_price}")
            sma_model.process_tick(last_price)
        else:
            print("[YFinance] No data fetched")
        time.sleep(delay)

# Start background fetch thread on app startup
@app.on_event("startup")
def start_background_tasks():
    thread = threading.Thread(target=live_price_feed, args=("EURUSD=X", "1m", 60), daemon=True)
    thread.start()

# Run the FastAPI app with:
# uvicorn this_file_name:app --reload

