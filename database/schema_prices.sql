-- Create database if not exists
CREATE DATABASE IF NOT EXISTS alphafxdb;
USE alphafxdb;

-- Create the trades table first to avoid error
CREATE TABLE IF NOT EXISTS trades (
  id INT AUTO_INCREMENT PRIMARY KEY,
  pair VARCHAR(10) NOT NULL,
  action VARCHAR(4) NOT NULL, -- 'BUY' or 'SELL'
  price DECIMAL(18,6) NOT NULL,
  volume DECIMAL(18,6) NOT NULL,
  status VARCHAR(20) NOT NULL,
  ts TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Add strategy column to trades table
ALTER TABLE trades 
ADD COLUMN strategy VARCHAR(50) NULL;

-- Create prices table
CREATE TABLE IF NOT EXISTS prices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    base_currency VARCHAR(10),
    exchange_rate DECIMAL(18,6),
    pair VARCHAR(20) NOT NULL,
    open_price DECIMAL(18,6),
    high_price DECIMAL(18,6),
    low_price DECIMAL(18,6),
    close_price DECIMAL(18,6),
    volume_ticks BIGINT,
    current_price DECIMAL(18,6),
    buy_sell VARCHAR(10),
    return_val DECIMAL(18,6),
    log_return DECIMAL(18,6),
    sma10 DECIMAL(18,6),
    sma50 DECIMAL(18,6),
    ema20 DECIMAL(18,6),
    atr14 DECIMAL(18,6),
    rsi14 DECIMAL(18,6),
    bband_upper DECIMAL(18,6),
    bband_lower DECIMAL(18,6),
    volatility20 DECIMAL(18,6),
    INDEX idx_pair_ts (pair, timestamp)
);

-- Create fx_rates table
CREATE TABLE IF NOT EXISTS fx_rates (
  id INT AUTO_INCREMENT PRIMARY KEY,
  pair VARCHAR(10) NOT NULL,
  price DECIMAL(18,6) NOT NULL,
  ts TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create index on fx_rates table
CREATE INDEX idx_fx_rates_pair_ts ON fx_rates(pair, ts);

-- Create index on trades table
CREATE INDEX idx_trades_ts ON trades(ts);
