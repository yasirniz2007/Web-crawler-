# Market Crawler

A Streamlit dashboard with three tabs:

1. **Market Crawler** — prices, news sentiment, momentum, volatility and rough probability estimates for stocks, indices, crypto, commodities and FX.
2. **Report Crawler** — SEC EDGAR filing retrieval and key-figure extraction for US-listed companies.
3. **Live News & Calendar** — public RSS / Google News headlines, economic calendar, risk mood, currency headline tone and spider animation.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Files

- `app.py` — main Streamlit app and market spider animation
- `live_feed.py` — live news and economic calendar tab
- `report_crawler.py` — SEC filing crawler and report animation
- `universal_market_analyzer.py` — shared market, FX and probability logic
- `market_crawler.py` — standalone quote/news crawler
- `requirements.txt` — dependencies

## Notes

- Public feeds and third-party data endpoints can change, be rate limited, or become unavailable.
- The free economic calendar feed does not provide actual release values; the embedded TradingView calendar is included for that view.
- SEC EDGAR requests require a real contact email in the SEC User-Agent; enter it in the Report Crawler tab.
- Sentiment and probability outputs are experimental heuristics, not validated trading signals or investment advice. Verify data independently.
