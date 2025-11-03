# Professional Forward Factor Scanner

A Python-based Forward Factor options scanner that uses the same timeframes as professional trading platforms.

## What it does

Scans options chains to find Forward Factor opportunities using professional timeframes:
- **30/60 DTE**: 15-45 DTE vs 40-80 DTE  
- **30/90 DTE**: 15-45 DTE vs 65-115 DTE
- **60/90 DTE**: 40-80 DTE vs 65-115 DTE

The Forward Factor formula: `FF = (σ₁ - σ₂) / σ₂`
- Positive FF: Front month IV elevated (potential bearish signal)
- Negative FF: Front month IV depressed (potential bullish signal)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure Schwab API credentials in your environment or `.env` file

## Usage

### Quick scan (recommended):
```bash
python professional_scanner.py
```

### Custom analysis:
```python
from forward_factor_strategy_fixed import ForwardFactorStrategy

strategy = ForwardFactorStrategy()
opportunity = strategy.analyzer.scan_ticker_for_opportunities("SPY", strategy.scanner)

if opportunity and opportunity.is_valid_opportunity:
    summary = strategy.analyzer.get_opportunity_summary(opportunity)
    print(f"Forward Factor: {summary['forward_factor_pct']:+.1f}%")
```

## Core Files

- `professional_scanner.py` - Main scanner script
- `forward_factor_strategy_fixed.py` - Strategy orchestrator  
- `options_scanner.py` - Schwab API integration with professional timeframes
- `iv_calculator.py` - Black-Scholes implied volatility calculations
- `iv_ff_analyzer.py` - Forward Factor analysis engine
- `liquidity_filter.py` - Filters for liquid options
- `midcap_filter.py` - Midcap stock filter
- `ff_config_default.json` - Configuration settings

## Professional Timeframe Logic

The scanner automatically selects the best available timeframe combination:
1. Tries 30/60 DTE with ±15/±20 day buffers
2. Falls back to 30/90 DTE with ±15/±25 day buffers  
3. Finally tries 60/90 DTE with ±20/±25 day buffers
4. Uses fallback logic if no professional timeframes available

This matches how professional scanners like those found in trading platforms work.

## Example Output

```
=== Professional Forward Factor Scanner ===
Timeframes: 30/60, 30/90, 60/90 DTE

Scanning SPY...
  ✅ SPY: +12.3% Forward Factor (bullish)
     Timeframe: 33/62 DTE
     Confidence: 85.2

Scanning QQQ...
  ✅ QQQ: -8.1% Forward Factor (bearish)  
     Timeframe: 59/89 DTE
     Confidence: 92.1

=== TOP OPPORTUNITIES ===
1. SPY: +12.3% (bullish) - 33/62 DTE
2. QQQ: -8.1% (bearish) - 59/89 DTE
```