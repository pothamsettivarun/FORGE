from __future__ import annotations

import argparse
import logging
import os
import time
from dataclasses import dataclass, field

import yaml

from forge_bot.data.binance import BinanceFeed
from forge_bot.data.polymarket import PolymarketData
from forge_bot.execution.paper import PaperExecutor
from forge_bot.risk.simple import can_trade, within_daily_drawdown
from forge_bot.runtime.files import append_jsonl, ensure_dir, session_id, write_json
from forge_bot.signal.edge import fair_probability_from_signal, has_tradeable_edge
from forge_bot.signal.momentum import build_momentum_signal


FORGE_BUILD = "patch3"


@dataclass
class Stats:
    markets_seen: int = 0
    entries: int = 0
    skips: int = 0
    resolutions: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    current_slug: str | None = None
    skip_reasons: dict = field(default_factory=dict)


class ForgeBot:
    def __init__(self, cfg: dict, base_dir: str, sid: str):
        self.cfg = cfg
        self.base_dir = base_dir
        self.sid = sid
        self.feed = BinanceFeed(symbol=cfg["market"]["symbol"])
        self.poly = PolymarketData()
        self.exec = PaperExecutor()
        self.stats = Stats()
        self.position = None
        self.logs_dir = ensure_dir(os.path.join(base_dir, "logs"))
        self.trades_dir = ensure_dir(os.path.join(base_dir, "trades"))
        self.summary_dir = ensure_dir(os.path.join(base_dir, "summary"))
        self.trade_file = os.path.join(self.trades_dir, f"trades-{sid}.jsonl")
        self.summary_file = os.path.join(self.summary_dir, f"summary-{sid}.json")
        self.latest_summary = os.path.join(self.summary_dir, "latest-summary.json")
        self.halt_logged = False

    def inc_skip(self, reason: str):
        self.stats.skips += 1
        self.stats.skip_reasons[reason] = self.stats.skip_reasons.get(reason, 0) + 1

    def persist_summary(self):
        payload = {
            "session_id": self.sid,
            "markets_seen": self.stats.markets_seen,
            "entries": self.stats.entries,
            "skips": self.stats.skips,
            "resolutions": self.stats.resolutions,
            "wins": self.stats.wins,
            "losses": self.stats.losses,
            "win_rate": round(self.stats.wins / self.stats.resolutions, 4) if self.stats.resolutions else None,
            "total_pnl": round(self.stats.total_pnl, 4),
            "current_slug": self.stats.current_slug,
            "skip_reasons": self.stats.skip_reasons,
        }
        write_json(self.summary_file, payload)
        write_json(self.latest_summary, payload)

    def resolve_if_due(self):
        if not self.position:
            return
        if time.time() < self.position["window_start"] + 300:
            return
        final_spot = self.feed.klines(limit=1)[-1]["close"]
        won = (final_spot > self.position["open_spot"] and self.position["side"] == "yes") or (
            final_spot < self.position["open_spot"] and self.position["side"] == "no"
        )
        pnl_per_share = (1 - self.position["entry_price"]) if won else (-self.position["entry_price"])
        pnl = pnl_per_share * self.position["shares"]
        self.stats.resolutions += 1
        self.stats.total_pnl += pnl
        if won:
            self.stats.wins += 1
        else:
            self.stats.losses += 1
        append_jsonl(self.trade_file, {
            "action": "CLOSE",
            "slug": self.position["slug"],
            "side": self.position["side"],
            "entry_price": self.position["entry_price"],
            "shares": round(self.position["shares"], 4),
            "open_spot": self.position["open_spot"],
            "final_spot": final_spot,
            "won": won,
            "pnl": round(pnl, 4),
            "ts": int(time.time()),
        })
        logging.info("RESOLUTION | slug=%s side=%s won=%s pnl=%.2f", self.position["slug"], self.position["side"], won, pnl)
        self.position = None
        self.persist_summary()

    def cycle(self):
        self.resolve_if_due()

        slug = self.poly.current_btc_5m_slug()
        if slug != self.stats.current_slug:
            self.stats.markets_seen += 1
            self.stats.current_slug = slug
            logging.info("MARKET | slug=%s", slug)
            self.persist_summary()

        market = self.poly.market_by_slug(slug)
        if not market:
            self.inc_skip("no_market")
            logging.info("SKIP | reason=no_market slug=%s", slug)
            return
        yes_id, no_id = self.poly.extract_token_ids(market)
        if not yes_id or not no_id:
            self.inc_skip("no_token_ids")
            logging.info("SKIP | reason=no_token_ids slug=%s", slug)
            return

        rows = self.feed.klines(limit=30)
        closes = [r["close"] for r in rows]
        signal = build_momentum_signal(closes)

        if signal.get("side") not in ("yes", "no"):
            self.inc_skip(signal.get("reason", "no_side"))
            logging.info("SCAN | slug=%s signal=%s decision=SKIP", slug, signal)
            return

        if float(signal.get("confidence", 0.0) or 0.0) < self.cfg["signal"]["min_confidence"]:
            self.inc_skip("low_confidence")
            logging.info("SCAN | slug=%s signal=%s decision=SKIP reason=low_confidence", slug, signal)
            return

        token_id = yes_id if signal["side"] == "yes" else no_id
        market_price = self.poly.midpoint(token_id)
        if market_price is None:
            self.inc_skip("no_midpoint")
            logging.info("SCAN | slug=%s signal=%s decision=SKIP reason=no_midpoint", slug, signal)
            return

        fair_prob, fair_reason = fair_probability_from_signal(signal)
        if fair_prob is None:
            self.inc_skip(fair_reason)
            logging.info("SCAN | slug=%s signal=%s decision=SKIP reason=%s", slug, signal, fair_reason)
            return

        ok_edge, edge = has_tradeable_edge(signal["side"], market_price, fair_prob, self.cfg["execution"]["edge_threshold"])
        if not ok_edge:
            self.inc_skip("edge_below_threshold")
            logging.info("SCAN | slug=%s side=%s market=%.3f fair=%.3f edge=%.3f decision=SKIP reason=edge_below_threshold", slug, signal['side'], market_price, fair_prob, edge)
            return

        risk_ok, risk_reason = can_trade(0.0 if not self.position else self.position["notional_usd"], self.cfg["execution"]["position_size_usd"], self.cfg["risk"]["max_gross_exposure_usd"])
        if not risk_ok:
            self.inc_skip(risk_reason)
            logging.info("SCAN | slug=%s decision=SKIP reason=%s", slug, risk_reason)
            return

        dd_ok, dd_reason = within_daily_drawdown(self.stats.total_pnl, self.cfg["risk"]["max_daily_drawdown_usd"])
        if not dd_ok:
            self.inc_skip(dd_reason)
            if not self.halt_logged:
                logging.info("SCAN | slug=%s decision=SKIP reason=%s", slug, dd_reason)
                self.halt_logged = True
            return
        else:
            self.halt_logged = False

        if self.position and self.position["slug"] == slug:
            self.inc_skip("position_already_open")
            logging.info("SCAN | slug=%s decision=SKIP reason=position_already_open", slug)
            return

        order = self.exec.place(signal["side"], market_price, self.cfg["execution"]["position_size_usd"], slug=slug)
        self.position = {
            "slug": slug,
            "window_start": int(time.time() // 300) * 300,
            "side": order.side,
            "entry_price": order.price,
            "shares": order.shares,
            "notional_usd": order.notional_usd,
            "open_spot": closes[-1],
        }
        self.stats.entries += 1
        implied_prob = market_price if order.side == "yes" else (1.0 - market_price)
        append_jsonl(self.trade_file, {
            "action": "OPEN",
            "slug": slug,
            "side": order.side,
            "entry_price": order.price,
            "shares": round(order.shares, 4),
            "notional_usd": order.notional_usd,
            "signal": signal,
            "implied_prob": round(implied_prob, 4),
            "fair_prob": fair_prob,
            "edge": round(edge, 4),
            "ts": int(time.time()),
        })
        logging.info("SCAN | slug=%s side=%s market=%.3f implied=%.3f fair=%.3f edge=%.3f decision=ENTER", slug, order.side, market_price, implied_prob, fair_prob, edge)
        self.persist_summary()

    def run(self):
        logging.info("FORGE STARTING | session=%s", self.sid)
        self.persist_summary()
        while True:
            try:
                self.cycle()
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logging.exception("Loop error: %s", e)
            time.sleep(self.cfg["execution"]["scan_interval_sec"])


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
    logging.info("SESSION | id=%s log=%s build=%s", sid, log_file, FORGE_BUILD)
    logging.info(
        "CONFIG | edge_threshold=%.3f min_conf=%.2f low_block=%.2f high_block=%.2f max_yes=%.2f max_no=%.2f dd=%.2f",
        cfg["execution"]["edge_threshold"],
        cfg["signal"]["min_confidence"],
        cfg["execution"]["extreme_price_block_low"],
        cfg["execution"]["extreme_price_block_high"],
        cfg["execution"]["max_entry_price_yes"],
        cfg["execution"]["max_entry_price_no"],
        cfg["risk"]["max_daily_drawdown_usd"],
    )
    ForgeBot(cfg, base_dir, sid).run()


if __name__ == "__main__":
    main()

    cfg = load_config(args.config)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ensure_dir(os.path.join(base_dir, "logs"))
    ensure_dir(os.path.join(base_dir, "trades"))
    ensure_dir(os.path.join(base_dir, "summary"))
    sid = session_id()
    log_file = setup_logging(base_dir, sid, cfg["logging"]["level"])
    logging.info("SESSION | id=%s log=%s", sid, log_file)
    ForgeBot(cfg, base_dir, sid).run()


if __name__ == "__main__":
    main()
