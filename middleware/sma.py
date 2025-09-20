import collections
from datetime import datetime

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
        
        # Sliding windows for SMA and high/low tracking
        self.price_window_short = collections.deque(maxlen=short_window)
        self.price_window_long = collections.deque(maxlen=long_window)
        self.price_window_high_low = collections.deque(maxlen=high_low_window)
        
        self.position = None  # 'LONG', 'SHORT', or None
        self.cumulative_volume = 0
        self.trade_log = []
        self.prev_diff = None
        self.purchase_price = None  # store the price at which current position was opened
    
    def add_price(self, price: float):
        """Add new price tick to SMA and high/low windows."""
        self.price_window_short.append(price)
        self.price_window_long.append(price)
        self.price_window_high_low.append(price)
    
    def calculate_sma(self, price_deque):
        """Calculate SMA for given deque."""
        if len(price_deque) == 0:
            return None
        return sum(price_deque) / len(price_deque)
    
    def generate_signal(self):
        """Generate BUY/SELL signals based on SMA crossover."""
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
        """Execute trades respecting volume limits and track position."""
        if signal is None:
            return
        
        if self.cumulative_volume >= self.trade_volume_limit:
            print("[INFO] Max trade volume reached. Halting trades.")
            return
        
        if signal == 'BUY' and self.position != 'LONG':
            self.purchase_price = self.price_window_short[-1]
            self._log_trade('BUY')
            self.position = 'LONG'
            self.cumulative_volume += self.trade_size
            print(f"[TRADE] BUY executed at {self.purchase_price} for volume {self.trade_size}")
        
        elif signal == 'SELL' and self.position == 'LONG':
            self._log_trade('SELL')
            # Calculate profit/loss on closing
            sell_price = self.price_window_short[-1]
            pnl = sell_price - self.purchase_price if self.purchase_price else None
            print(f"[TRADE] SELL executed at {sell_price} for volume {self.trade_size}, PnL: {pnl}")
            self.position = 'SHORT'
            self.cumulative_volume += self.trade_size
            self.purchase_price = None  # position closed
        
        else:
            print(f"[INFO] No trade executed for signal: {signal}")
    
    def _log_trade(self, trade_type):
        """Log trade with timestamp."""
        trade_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': trade_type,
            'volume': self.trade_size,
            'position': self.position
        }
        self.trade_log.append(trade_record)
        print(f"[LOG] Trade recorded: {trade_record}")
    
    def process_tick(self, price):
        """Main entry point: process new price tick, run logic."""
        self.add_price(price)
        signal = self.generate_signal()
        self.execute_trade(signal)
    
    def get_high_low(self):
        """Return highest and lowest price within the high_low window."""
        if not self.price_window_high_low:
            return None, None
        return max(self.price_window_high_low), min(self.price_window_high_low)
    
    def get_average_trade_volume(self):
        """Calculate average trade volume over all logged trades."""
        if not self.trade_log:
            return 0
        total_volume = sum(trade['volume'] for trade in self.trade_log)
        return total_volume / len(self.trade_log)
    
    def get_current_price(self):
        """Return the latest price received."""
        if not self.price_window_short:
            return None
        return self.price_window_short[-1]
    
    def get_purchase_price(self):
        """Return the purchase price of the current position."""
        return self.purchase_price
    
    def get_profit_loss(self):
        """Compute live profit/loss for open long position."""
        current_price = self.get_current_price()
        if self.position == 'LONG' and self.purchase_price is not None and current_price is not None:
            return current_price - self.purchase_price
        return None

# Example usage (assuming cleaned data available)
if __name__ == "__main__":
    import pandas as pd
    
    df = pd.read_csv('fx_dataset.csv')  # Replace with your dataset file
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.sort_values('timestamp', inplace=True)
    
    model = SMA_TradingModel()
    
    for index, row in df.iterrows():
        model.process_tick(row['close'])
        high, low = model.get_high_low()
        avg_volume = model.get_average_trade_volume()
        current_price = model.get_current_price()
        purchase_price = model.get_purchase_price()
        pnl = model.get_profit_loss()
        
        print(f"Tick {index}: Current Price: {current_price}, High: {high}, Low: {low}, "
              f"Avg Volume: {avg_volume}, Purchase Price: {purchase_price}, P/L: {pnl}")
    
    print("\nFinal Trade Log:")
    for trade in model.trade_log:
        print(trade)
