from __future__ import annotations

import argparse
import logging
import os
import time
import yaml

from forge_bot.data.binance import BinanceFeed
from forge_bot.execution.paper import PaperExecutor
from forge_bot.runtime.files import ensure_dir, session_id
from forge_bot.signal.momentum import build_momentum_signal


def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_logging(base_dir: str, sid: str, level: str):
    log_dir = ensure_dir(os.path.join(base_dir, "logs"))
    log_file = os.path.join(log_dir, f"forge-{sid}.log")
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_file)],
    )
    return log_file


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.example.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ensure_dir(os.path.join(base_dir, "logs"))
    ensure_dir(os.path.join(base_dir, "trades"))
    ensure_dir(os.path.join(base_dir, "summary"))

    sid = session_id()
    log_file = setup_logging(base_dir, sid, cfg["logging"]["level"])
    logging.info("FORGE STARTING | session=%s log=%s", sid, log_file)

    feed = BinanceFeed(symbol=cfg["market"]["symbol"])
    executor = PaperExecutor()
    _ = executor

    while True:
        try:
            rows = feed.klines(limit=30)
            closes = [r["close"] for r in rows]
            signal = build_momentum_signal(closes)
            logging.info("SCAN | signal=%s", signal)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            logging.exception("Loop error: %s", e)
        time.sleep(cfg["execution"]["scan_interval_sec"])


if __name__ == "__main__":
    main()
