# backend/simulator.py
import time, random, requests, os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
URL = os.getenv("SIMULATOR_TARGET", "http://localhost:8000/internal/ingest_price")

PAIRS = ["EURUSD", "GBPUSD", "USDJPY"]

def random_walk(last, scale=0.0002):
    return last * (1 + random.uniform(-scale, scale))

def run():
    last = {"EURUSD":1.0800, "GBPUSD":1.2600, "USDJPY":150.0}
    while True:
        for p in PAIRS:
            last[p] = random_walk(last[p])
            payload = {"pair": p, "price": round(last[p], 6)}
            try:
                requests.post(URL, json=payload, timeout=2)
            except Exception as e:
                print("post fail:", e)
        time.sleep(1)

if __name__ == "__main__":
    run()
