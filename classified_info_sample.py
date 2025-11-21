DEFAULT_PORT = 8080  

SCHWAB_API_KEY = 'xxxxx'
SCHWAB_SECRET = 'xxxx'

SCHWAB_TOKEN_PATH = r'C:\SchwabAccountConfig\token'

# Redirect URL
REDIRECT_URI = 'https://127.0.0.1'                      # Works with client_from_manual_flow()
REDIRECT_URI_WITH_PORT = 'https://127.0.0.1:8182'               # Works with easy_client()


# Accounts Info (IMPORTANT: only include accounts you want to trade/monitor)
NUM_SCHWAB_ACCOUNTS = 2

# SCHWAB Account Numbers
ACCOUNT_1_NUM = 11111111                # Act1
ACCOUNT_2_NUM = 22222222                # Act2

# SCHWAB Account hashes
ACCOUNT_1_HASH = 'xxxxxx'
ACCOUNT_2_HASH = 'xxxxxx'

# Account number to Nick Name Map (Optional)
account_mapping = {
    ACCOUNT_1_NUM: 'Serious',
    ACCOUNT_2_NUM: 'Fun',
}
