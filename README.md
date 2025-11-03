# Forward Factor Scanner

A Python-based Forward Factor options scanner that calculates proper variance-weighted Forward Factor using Black-Scholes implied volatility calculations via py_vollib.

## What it does

Scans options chains to find Forward Factor opportunities using different timeframes:
- **30/60 DTE**: ~30 DTE vs ~60 DTE (with ±15/±20 day buffers)
- **30/90 DTE**: ~30 DTE vs ~90 DTE (with ±15/±25 day buffers)  
- **60/90 DTE**: ~60 DTE vs ~90 DTE (with ±20/±25 day buffers)

## Forward Factor Calculation

Uses the **proper variance-weighted formula** (not the naive ratio):

1. Convert IV to variance: `V₁ = σ₁²`, `V₂ = σ₂²`
2. Calculate time fractions: `T₁ = DTE₁/365`, `T₂ = DTE₂/365`
3. Forward variance: `Vf = (V₂×T₂ - V₁×T₁) / (T₂ - T₁)`
4. Forward volatility: `σf = √Vf`
5. **Forward Factor: `FF = (σ₁ - σf) / σf`**

**Signal Threshold:** FF > 20% indicates a significant volatility term structure opportunity.

## IV Calculation Method

### Option Selection for IV Calculation:
For each expiration date (e.g., 25 DTE, 74 DTE), the system:

1. **Delta-based filtering**: Selects options with delta between **35-50** (closest to ATM)
2. **Includes both calls and puts** that meet the delta criteria
3. **Applies liquidity filters**: Basic volume/OI and bid-ask spread checks
4. **Calculates Black-Scholes IV** for each selected option using py_vollib
5. **Averages all qualifying IVs** to get the final chain IV

### Example:
For SNOW 25 DTE chain:
- Finds ~6-10 options (calls + puts) with 35-50 delta
- Calculates individual IV for each using Black-Scholes
- **Displayed IV (55.9%)** = Average of all qualifying option IVs

This approach provides a **robust ATM IV estimate** independent of any single strike, representing the overall implied volatility of the most liquid near-the-money options.

## Setup

1. Install dependencies:
```bash
pip install schwab-py requests py_vollib rich pandas numpy
```

2. Configure Schwab API credentials in `global_.py`:
```python
# Set path to your classified_info.py file containing:
# SCHWAB_API_KEY = "your_client_id"
# SCHWAB_SECRET = "your_client_secret" 
# REDIRECT_URI = "https://127.0.0.1"
```

## Usage

### FF scanner (main):
```bash
python forward_factor_strategy_fixed.py --config ff_config_relaxed.json
```

### Scan specific tickers:
```bash
python forward_factor_strategy_fixed.py --config ff_config_relaxed.json --tickers "AAPL,TSLA,NVDA"
```

### Single ticker analysis:
```bash
python forward_factor_strategy_fixed.py --config ff_config_relaxed.json --tickers "SNOW"
```

## Core Files

- `forward_factor_strategy_fixed.py` - **Main scanner script**
- `iv_ff_analyzer.py` - Forward Factor calculation engine with proper variance-weighted formula
- `options_scanner.py` - Schwab API integration and timeframe selection
- `iv_calculator.py` - py_vollib Black-Scholes implied volatility calculations
- `liquidity_filter.py` - Delta-focused liquidity filtering (35-50 delta ATM options)
- `schwab_api_utils.py` - Schwab API authentication and utilities
- `global_.py` - Credentials management
- `ff_config_relaxed.json` - **Recommended configuration** (relaxed liquidity filters)
- `ff_config_default.json` - Default configuration

## Configuration

Key settings in `ff_config_relaxed.json`:

```json
{
  "forward_factor": {
    "signal_threshold": 20.0  // FF > 20% = signal
  },
  "liquidity": {
    "min_volume": 0,           // Very relaxed
    "min_open_interest": 1,    // for smaller caps
    "min_days_to_expiration": 7,
    "max_days_to_expiration": 120
  }
}
```

## Example Output

```
╭──────────────────────────────────────────────────────────────╮
│               Forward Factor Scanner                         │
╰──────────────────────────────────────────────────────────────╯

🏷️  Timeframe: 30/60
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Ticker ┃ Price    ┃ Front Vol (DTE) ┃ Back Vol (DTE) ┃ Forward Factor  ┃ FF Threshold ┃ Pass/Fail ┃ Option Volume ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│  SNOW  │ $277.69  │   55.9% (32)    │   54.7% (46)   │      2.3%       │    20.0%     │  ✗ FAIL   │              66 │
└────────┴──────────┴─────────────────┴────────────────┴─────────────────┴──────────────┴───────────┴─────────────────┘

🏷️  Timeframe: 30/90  
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Ticker ┃ Price    ┃ Front Vol (DTE) ┃ Back Vol (DTE) ┃ Forward Factor  ┃ FF Threshold ┃ Pass/Fail ┃ Option Volume ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│  SNOW  │ $277.69  │   55.9% (32)    │   50.2% (74)   │     11.5%       │    20.0%     │  ✗ FAIL   │              66 │
└────────┴──────────┴─────────────────┴────────────────┴─────────────────┴──────────────┴───────────┴─────────────────┘

📝 Summary: No Forward Factor opportunities found that meet >20% threshold criteria.
```

## Key Features

- ✅ **Mathematically correct Forward Factor** using variance-weighted calculation
- ✅ **Rich table formatting** with color-coded results  
- ✅ **Delta-focused liquidity filtering** (35-50 delta ATM options)
- ✅ **py_vollib Black-Scholes IV calculations** (not broker-provided IV)
- ✅ **DTE information display** for broker benchmark comparison
- ✅ **Option volume data** for liquidity assessment
- ✅ **Simplified configuration** (only FF threshold matters)
- ✅ **Timeframe selection** with intelligent fallbacks

## Liquidity Strategy

Uses **delta-focused filtering** instead of strike-based:
- Targets options with 35-50 delta (closest to ATM)
- Automatically finds liquid ATM options regardless of strike price
- Much more effective for smaller cap stocks than traditional volume/OI filters
- Averages IV across multiple qualifying options for robust estimates