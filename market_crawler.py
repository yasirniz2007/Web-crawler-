#!/usr/bin/env python3
"""
Financial market data crawler.

Collects: stock/ETF/index quotes, crypto prices, and news headlines.
Polite by design: robots.txt check, rate limiting, retries, custom User-Agent.

Install:  pip install requests
Run:      python market_crawler.py --symbols AAPL MSFT ^GSPC --crypto bitcoin ethereum
"""
import argparse
import csv
import json
import time
import urllib.robotparser as robotparser
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

USER_AGENT = "MarketCrawler/1.0 (educational; contact: you@example.com)"
DELAY_SECONDS = 1.5  # pause between requests


class PoliteSession:
    """requests wrapper with robots.txt checks, rate limiting and retries."""

    def __init__(self, delay=DELAY_SECONDS, respect_robots=True):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": USER_AGENT})
        self.delay = delay
        self.respect_robots = respect_robots
        self._robots = {}
        self._last = 0.0

    def _allowed(self, url):
        if not self.respect_robots:
            return True
        host = "{0.scheme}://{0.netloc}".format(urlparse(url))
        if host not in self._robots:
            rp = robotparser.RobotFileParser()
            try:
                rp.set_url(host + "/robots.txt")
                rp.read()
            except Exception:
                rp = None  # robots.txt unreachable -> allow
            self._robots[host] = rp
        rp = self._robots[host]
        return True if rp is None else rp.can_fetch(USER_AGENT, url)

    def get(self, url, retries=3, **kw):
        if not self._allowed(url):
            print(f"[skip] robots.txt disallows {url}")
            return None
        for attempt in range(1, retries + 1):
            wait = self.delay - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            try:
                r = self.s.get(url, timeout=15, **kw)
                self._last = time.time()
                if r.status_code == 429:  # rate limited -> back off
                    time.sleep(5 * attempt)
                    continue
                r.raise_for_status()
                return r
            except requests.RequestException as e:
                print(f"[retry {attempt}/{retries}] {url}: {e}")
                time.sleep(2 * attempt)
        return None


def fetch_quote(http, symbol):
    """Price, change, volume and 5-day history via Yahoo Finance chart API."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    r = http.get(url, params={"range": "5d", "interval": "1d"})
    if not r:
        return None
    try:
        res = r.json()["chart"]["result"][0]
        m = res["meta"]
        price, prev = m.get("regularMarketPrice"), m.get("chartPreviousClose")
        closes = res["indicators"]["quote"][0].get("close", [])
        return {
            "symbol": symbol,
            "name": m.get("longName") or m.get("shortName"),
            "currency": m.get("currency"),
            "price": price,
            "prev_close": prev,
            "change_pct": round((price - prev) / prev * 100, 2) if price and prev else None,
            "day_high": m.get("regularMarketDayHigh"),
            "day_low": m.get("regularMarketDayLow"),
            "volume": m.get("regularMarketVolume"),
            "exchange": m.get("fullExchangeName"),
            "last_5_closes": [round(c, 2) for c in closes if c is not None],
        }
    except (KeyError, IndexError, TypeError, ValueError) as e:
        print(f"[parse error] {symbol}: {e}")
        return None


def fetch_crypto(http, ids, vs="usd"):
    """Prices, 24h change, market cap and volume via CoinGecko public API."""
    r = http.get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={
            "ids": ",".join(ids),
            "vs_currencies": vs,
            "include_24hr_change": "true",
            "include_market_cap": "true",
            "include_24hr_vol": "true",
        },
    )
    if not r:
        return []
    return [
        {
            "id": cid,
            "price": d.get(vs),
            "change_24h_pct": round(d.get(f"{vs}_24h_change") or 0, 2),
            "market_cap": d.get(f"{vs}_market_cap"),
            "volume_24h": d.get(f"{vs}_24h_vol"),
        }
        for cid, d in r.json().items()
    ]


def fetch_news(http, symbol, limit=5):
    """Latest headlines from Yahoo Finance RSS."""
    r = http.get(
        "https://feeds.finance.yahoo.com/rss/2.0/headline",
        params={"s": symbol, "region": "US", "lang": "en-US"},
    )
    if not r:
        return []
    try:
        root = ET.fromstring(r.content)
    except ET.ParseError:
        return []
    return [
        {
            "symbol": symbol,
            "title": (i.findtext("title") or "").strip(),
            "link": i.findtext("link"),
            "published": i.findtext("pubDate"),
        }
        for i in root.iter("item")
    ][:limit]


def save(data, prefix="market_data"):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    with open(f"{prefix}_{stamp}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    if data["quotes"]:
        with open(f"{prefix}_quotes_{stamp}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=[k for k in data["quotes"][0] if k != "last_5_closes"])
            w.writeheader()
            for q in data["quotes"]:
                w.writerow({k: v for k, v in q.items() if k != "last_5_closes"})
    print(f"Saved {prefix}_{stamp}.json (+ CSV)")


def main():
    p = argparse.ArgumentParser(description="Financial market crawler")
    p.add_argument("--symbols", nargs="*", default=["AAPL", "MSFT", "^GSPC"])
    p.add_argument("--crypto", nargs="*", default=["bitcoin", "ethereum"])
    p.add_argument("--news", type=int, default=3, help="headlines per symbol (0 = off)")
    p.add_argument("--no-robots", action="store_true", help="skip robots.txt check (APIs only)")
    a = p.parse_args()

    http = PoliteSession(respect_robots=not a.no_robots)
    data = {"timestamp": datetime.now(timezone.utc).isoformat(), "quotes": [], "crypto": [], "news": []}

    for sym in a.symbols:
        q = fetch_quote(http, sym)
        if q:
            data["quotes"].append(q)
            print(f"{sym:8} {q['price']}  ({q['change_pct']}%)")
        if a.news:
            data["news"] += fetch_news(http, sym, a.news)

    if a.crypto:
        data["crypto"] = fetch_crypto(http, a.crypto)
        for c in data["crypto"]:
            print(f"{c['id']:10} ${c['price']}  ({c['change_24h_pct']}% 24h)")

    save(data)


if __name__ == "__main__":
    main()
