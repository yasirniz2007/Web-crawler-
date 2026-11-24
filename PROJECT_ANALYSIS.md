# Project analysis and revision notes

## Existing structure
The uploaded `app.py` already imports `live_feed`, `report_crawler`, and `universal_market_analyzer`, and already defines all three Streamlit tabs. The package preserves that existing three-tab layout; the third tab did not need to be added from scratch.

## Issue addressed
The Live News currency score previously applied generic positive/negative word sentiment to each currency mentioned in a headline. This can misread a geopolitical headline where a word such as “surges” describes oil or another commodity rather than the currency.

The revised `headline_fx_score()` treats geopolitical risk headlines separately. Risk-off headlines use a cautious heuristic that can support traditional havens (USD, JPY, CHF) and weigh on risk-sensitive currencies (AUD, NZD); risk-on geopolitical headlines use the reverse mapping. Other headlines retain the existing finance lexicon.

## Reliability improvements
- Safe fallback for missing news source labels.
- Handles naive and timezone-aware RSS publication timestamps.
- Clamps future publication timestamps to zero age.
- Displays a warning rather than crashing the Live News tab when news feeds fail.
- Adds explicit `pandas` dependency.

## Validation
All Python modules are syntax-compiled and the three-tab integration is checked. No live API calls or full Streamlit browser session were run, so feed access and end-to-end rendering still need runtime verification.
