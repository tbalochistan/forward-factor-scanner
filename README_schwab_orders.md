# Schwab API Order History Script

This Python script connects to the Charles Schwab API to retrieve order history for your accounts using OAuth 2.0 authentication.

## Features

- **OAuth 2.0 Authentication**: Secure authentication with automatic token refresh
- **Cross-platform**: Works on both Windows and Linux
- **Date Range Filtering**: Filter orders by start and end dates
- **Multiple Account Support**: Query individual accounts or all accounts
- **Error Handling**: Graceful handling of rate limits, expired tokens, and API errors
- **File Output**: Save results to JSON file for further analysis
- **Detailed Logging**: Clear status messages and error reporting

## Prerequisites

1. **Schwab API Credentials**: You need a Schwab API key and secret
2. **Credentials File**: Create a `classified_info.py` file with your credentials
3. **Python Environment**: Python 3.7+ with required packages

## Setup

### 1. Install Required Packages

```bash
pip install requests argparse
```

### 2. Credentials File

Create a `classified_info.py` file in:
- **Windows**: `C:\SchwabAccountConfig\classified_info.py`
- **Linux**: `~/SchwabAccountConfig/classified_info.py`

The file should contain:

```python
# Schwab API Credentials
SCHWAB_API_KEY = 'your_api_key_here'
SCHWAB_SECRET = 'your_secret_here'
SCHWAB_TOKEN_PATH = r'C:\SchwabAccountConfig\token'  # Windows
# SCHWAB_TOKEN_PATH = '/home/username/SchwabAccountConfig/token'  # Linux

# Redirect URL (must match your Schwab app configuration)
REDIRECT_URI = 'https://127.0.0.1'

# Account Information
ACCOUNT_1_NUM = 12345678  # Your account number
ACCOUNT_2_NUM = 87654321  # Your second account number (if any)

# Account Hashes (encrypted account numbers from Schwab API)
ACCOUNT_1_HASH = 'your_account_1_hash_here'
ACCOUNT_2_HASH = 'your_account_2_hash_here'
```

## Usage

### Basic Examples

```bash
# Get all orders for all accounts
python schwab_orders.py

# Get orders for a specific date range
python schwab_orders.py --start_date 2025-10-01 --end_date 2025-10-31

# Get orders for only account 1
python schwab_orders.py --account 1 --start_date 2025-11-01

# Save to a custom file
python schwab_orders.py --save_file my_orders.json

# Don't save to file, just display results
python schwab_orders.py --no_save
```

### Command Line Options

- `--start_date`: Start date in YYYY-MM-DD format
- `--end_date`: End date in YYYY-MM-DD format
- `--save_file`: Custom filename for JSON output (default: orders.json)
- `--no_save`: Don't save results to file
- `--account`: Which account to query (1, 2, or all)

## Authentication Flow

### First Time Setup

1. Run the script
2. A web browser will open for Schwab authorization
3. Log in to your Schwab account and authorize the application
4. Copy the authorization code from the redirect URL
5. Paste the code when prompted
6. The script will save your tokens for future use

### Subsequent Runs

The script automatically refreshes tokens as needed. You only need to re-authorize if:
- Tokens expire (rare)
- You revoke access in your Schwab account
- Token files are deleted

## Output Format

The script provides:

1. **Console Output**: Real-time status and order summaries
2. **JSON File**: Complete order data saved to file
3. **Error Messages**: Clear error descriptions and troubleshooting tips

### Sample Output

```
Authenticating with Schwab API...
✓ Using existing valid access token
Retrieving orders for account 68089999...
Date range: 2025-10-01 to 2025-10-31

============================================================
ORDER HISTORY SUMMARY
============================================================

Account_39687527_RegT: 15 orders
  Recent orders:
    1. AAPL - LIMIT - FILLED - 2025-10-30T14:30:00Z
    2. MSFT - MARKET - FILLED - 2025-10-29T09:15:00Z
    3. TSLA - LIMIT - CANCELLED - 2025-10-28T16:00:00Z

Total orders across all accounts: 15

✓ Order data saved to orders.json
✓ Order history retrieval completed successfully
```

## Error Handling

The script handles common errors:

- **Rate Limiting**: Automatic retry with backoff
- **Token Expiration**: Automatic token refresh
- **Network Issues**: Clear error messages
- **Invalid Dates**: Date format validation
- **Missing Credentials**: Helpful setup instructions

## Troubleshooting

### Common Issues

1. **Import Error**: Ensure `classified_info.py` is in the correct directory
2. **Authentication Failed**: Check API key and secret
3. **No Orders Returned**: Verify account hashes and date ranges
4. **Rate Limit**: Wait a few minutes and try again

### Getting Account Hashes

Account hashes are encrypted versions of your account numbers. You can get them by:
1. Making a call to the accounts endpoint after authentication
2. Using Schwab's API documentation tools
3. Checking your first successful API response

## Security Notes

- **Never commit credentials**: Keep `classified_info.py` out of version control
- **Token Security**: Tokens are stored locally and auto-refresh
- **API Limits**: Respect Schwab's rate limits and usage policies

## Support

For issues with:
- **Schwab API**: Check Schwab's developer documentation
- **This Script**: Review error messages and troubleshooting section
- **Authentication**: Verify your Schwab developer account setup