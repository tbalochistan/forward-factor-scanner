"""
Schwab Orders API Client

Handles authentication and API requests to Charles Schwab API
for retrieving order history and market data.
"""

import os
import json
import requests
import time
import base64
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging


class SchwabAPIClient:
    """
    Charles Schwab API client for retrieving order history and market data.
    Handles OAuth2 authentication and token management.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # API endpoints
        self.base_url = "https://api.schwabapi.com"
        self.auth_url = "https://api.schwabapi.com/v1/oauth/authorize"
        self.token_url = "https://api.schwabapi.com/v1/oauth/token"
        
        # Try to load credentials from various sources
        self.client_id = None
        self.client_secret = None
        self.redirect_uri = "https://localhost:8080/callback"
        
        # Load credentials
        self._load_credentials()
        
        # Token storage - check multiple locations
        token_locations = [
            Path("C:/SchwabAccountConfig/DirectAPIUsage/token.json"),  # Your location
            Path("C:/SchwabAccountConfig/DirectAPIUsage/schwab_tokens.json"),  
            Path("schwab_tokens.json"),  # Current directory fallback
        ]
        
        self.token_file = None
        for location in token_locations:
            if location.exists():
                self.token_file = location
                break
        
        if not self.token_file:
            self.token_file = Path("schwab_tokens.json")  # Default fallback
        
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        
        # Load existing tokens
        self._load_tokens()
    
    def _load_credentials(self):
        """Load API credentials from various sources"""
        import platform
        from pathlib import Path
        
        # Use your existing credential pattern
        if platform.system() == "Linux":
            base_path = os.path.join(str(Path.home()), 'SchwabAccountConfig')
        else:  
            # Assuming Windows
            base_path = r'C:\SchwabAccountConfig'
        
        # Try to import from local global_.py first
        try:
            import global_ as schwab_globals
            
            # Use your existing variables
            self.client_id = schwab_globals.CLIENT_ID
            self.client_secret = schwab_globals.CLIENT_SECRET  
            self.redirect_uri = schwab_globals.REDIRECT_URI
            
            self.logger.info("Loaded credentials from local global_.py")
            return
            
        except Exception as e:
            self.logger.warning(f"Could not load from local global_.py: {e}")
        
        # Fallback: Try to import from your main global_.py
        try:
            import sys
            sys.path.append(r'c:\SchwabApps\TradingApp\schwab_flask_bot')
            import global_ as schwab_globals
            
            # Use your existing variables
            self.client_id = schwab_globals.CLIENT_ID
            self.client_secret = schwab_globals.CLIENT_SECRET  
            self.redirect_uri = schwab_globals.REDIRECT_URI
            
            self.logger.info("Loaded credentials from global_.py")
            return
            
        except Exception as e:
            self.logger.warning(f"Could not load from global_.py: {e}")
        
        # Fallback to environment variables
        self.client_id = os.getenv('SCHWAB_CLIENT_ID')
        self.client_secret = os.getenv('SCHWAB_CLIENT_SECRET')
        self.redirect_uri = os.getenv('SCHWAB_REDIRECT_URI', 'https://localhost:8080/callback')
        
        # Fallback to credentials file in your SchwabAccountConfig
        cred_file = os.path.join(base_path, 'credentials.json')
        if os.path.exists(cred_file):
            try:
                with open(cred_file, 'r') as f:
                    creds = json.load(f)
                
                self.client_id = creds.get('client_id') or self.client_id
                self.client_secret = creds.get('client_secret') or self.client_secret
                self.redirect_uri = creds.get('redirect_uri', self.redirect_uri)
                
                self.logger.info(f"Loaded credentials from {cred_file}")
            except Exception as e:
                self.logger.warning(f"Error loading credentials from {cred_file}: {e}")
    
    def _load_tokens(self):
        """Load existing tokens from file"""
        if self.token_file and self.token_file.exists():
            try:
                with open(self.token_file, 'r') as f:
                    tokens = json.load(f)
                
                self.access_token = tokens.get('access_token')
                self.refresh_token = tokens.get('refresh_token')
                
                # Parse expiration time - handle both string and timestamp formats
                expires_data = tokens.get('expires_at')
                if expires_data:
                    if isinstance(expires_data, str):
                        # ISO format string
                        self.token_expires_at = datetime.fromisoformat(expires_data)
                    elif isinstance(expires_data, (int, float)):
                        # Unix timestamp
                        self.token_expires_at = datetime.fromtimestamp(expires_data)
                
                self.logger.info(f"Loaded existing tokens from {self.token_file}")
                
            except Exception as e:
                self.logger.warning(f"Error loading tokens: {e}")
    
    def _save_tokens(self, token_data: Dict[str, Any]):
        """Save tokens to file"""
        try:
            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token')
            
            # Calculate expiration time
            expires_in = token_data.get('expires_in', 1800)  # Default 30 minutes
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            # Save to file
            tokens = {
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
                'expires_at': self.token_expires_at.isoformat(),
                'token_type': token_data.get('token_type', 'Bearer')
            }
            
            with open(self.token_file, 'w') as f:
                json.dump(tokens, f, indent=2)
            
            self.logger.info("Tokens saved successfully")
            
        except Exception as e:
            self.logger.error(f"Error saving tokens: {e}")
    
    def is_authenticated(self) -> bool:
        """Check if we have valid authentication"""
        if not self.access_token:
            return False
        
        if self.token_expires_at and datetime.now() >= self.token_expires_at:
            # Token expired, try to refresh
            if self.refresh_token:
                return self._refresh_access_token()
            return False
        
        return True
    
    def _refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token"""
        if not self.refresh_token or not self.client_id or not self.client_secret:
            return False
        
        try:
            # Prepare credentials for basic auth
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token
            }
            
            response = requests.post(self.token_url, headers=headers, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                self._save_tokens(token_data)
                self.logger.info("Access token refreshed successfully")
                return True
            else:
                self.logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error refreshing token: {e}")
            return False
    
    def authenticate(self) -> bool:
        """
        Authenticate with Schwab API.
        """
        if self.is_authenticated():
            return True
        
        # If we have a refresh token, try to use it
        if self.refresh_token:
            if self._refresh_access_token():
                return True
        
        # Check if we have credentials
        if not self.client_id or not self.client_secret:
            print("❌ Missing Schwab API credentials")
            print("Please set up credentials file or environment variables:")
            print("  SCHWAB_CLIENT_ID=your_client_id")
            print("  SCHWAB_CLIENT_SECRET=your_client_secret")
            return False
        
        # Need manual authorization
        auth_url = (
            f"{self.auth_url}?"
            f"client_id={self.client_id}&"
            f"redirect_uri={urllib.parse.quote(self.redirect_uri)}&"
            f"response_type=code"
        )
        
        print("Manual authentication required:")
        print(f"1. Visit: {auth_url}")
        print("2. Authorize the application")
        print("3. Copy the authorization code from the redirect URL")
        print("4. Run: client.exchange_code_for_tokens('your_code_here')")
        
        return False
    
    def exchange_code_for_tokens(self, authorization_code: str) -> bool:
        """Exchange authorization code for access and refresh tokens"""
        if not self.client_id or not self.client_secret:
            self.logger.error("Missing client credentials")
            return False
        
        try:
            # Prepare credentials for basic auth
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'authorization_code',
                'code': authorization_code,
                'redirect_uri': self.redirect_uri
            }
            
            response = requests.post(self.token_url, headers=headers, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                self._save_tokens(token_data)
                self.logger.info("Authentication successful")
                return True
            else:
                self.logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error exchanging code for tokens: {e}")
            return False
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Make authenticated request to Schwab API"""
        if not self.is_authenticated():
            self.logger.error("Not authenticated")
            return None
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                # Token expired, try to refresh
                if self._refresh_access_token():
                    headers['Authorization'] = f'Bearer {self.access_token}'
                    response = requests.get(url, headers=headers, params=params)
                    if response.status_code == 200:
                        return response.json()
                
                self.logger.error("Authentication failed")
                return None
            else:
                self.logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error making request: {e}")
            return None
    
    def get_option_chain(self, symbol: str, contract_type: str = 'ALL', 
                        strikes: int = None, include_quotes: bool = True,
                        strategy: str = 'SINGLE', interval: str = None,
                        strike: float = None, range_value: str = 'ALL',
                        from_date: str = None, to_date: str = None,
                        volatility: float = None, underlying_price: float = None,
                        interest_rate: float = None, days_to_expiration: int = None,
                        exp_month: str = 'ALL', option_type: str = 'ALL') -> Optional[Dict[str, Any]]:
        """
        Get option chain data for a symbol
        """
        endpoint = f"/marketdata/v1/chains"
        
        params = {
            'symbol': symbol.upper(),
            'contractType': contract_type,
            'includeQuotes': str(include_quotes).lower(),
            'strategy': strategy,
            'range': range_value,
            'expMonth': exp_month,
            'optionType': option_type
        }
        
        # Add optional parameters
        if strikes:
            params['strikeCount'] = strikes
        if interval:
            params['interval'] = interval
        if strike:
            params['strike'] = strike
        if from_date:
            params['fromDate'] = from_date
        if to_date:
            params['toDate'] = to_date
        if volatility:
            params['volatility'] = volatility
        if underlying_price:
            params['underlyingPrice'] = underlying_price
        if interest_rate:
            params['interestRate'] = interest_rate
        if days_to_expiration:
            params['daysToExpiration'] = days_to_expiration
        
        return self._make_request(endpoint, params)
    
    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get quote data for a symbol"""
        endpoint = f"/marketdata/v1/quotes/{symbol.upper()}"
        return self._make_request(endpoint)
    
    def get_multiple_quotes(self, symbols: List[str]) -> Optional[Dict[str, Any]]:
        """Get quotes for multiple symbols"""
        endpoint = "/marketdata/v1/quotes"
        params = {'symbols': ','.join([s.upper() for s in symbols])}
        return self._make_request(endpoint)
    
    def get_order_history(self, account_id: str, from_date: str = None, 
                         to_date: str = None, max_results: int = 100) -> Optional[Dict[str, Any]]:
        """Get order history for an account"""
        endpoint = f"/trader/v1/accounts/{account_id}/orders"
        
        params = {'maxResults': max_results}
        if from_date:
            params['fromEnteredTime'] = from_date
        if to_date:
            params['toEnteredTime'] = to_date
        
        return self._make_request(endpoint, params)
    
    def get_accounts(self) -> Optional[Dict[str, Any]]:
        """Get account information"""
        endpoint = "/trader/v1/accounts"
        return self._make_request(endpoint)


# Utility functions
def setup_schwab_credentials():
    """Helper to create credentials file"""
    print("Setting up Schwab API credentials...")
    print("You can get these from: https://developer.schwab.com/")
    
    client_id = input("Enter your Client ID: ").strip()
    client_secret = input("Enter your Client Secret: ").strip()
    
    credentials = {
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': 'https://localhost:8080/callback'
    }
    
    with open('schwab_credentials.json', 'w') as f:
        json.dump(credentials, f, indent=2)
    
    print("✅ Credentials saved to schwab_credentials.json")
    print("Now run your script again to authenticate")


def test_authentication():
    """Test Schwab API authentication"""
    client = SchwabAPIClient()
    
    if client.is_authenticated():
        print("✅ Already authenticated")
        
        # Test with a simple quote
        quote = client.get_quote("SPY")
        if quote:
            print("✅ API connection working")
            return True
        else:
            print("❌ API connection failed")
            return False
    else:
        print("❌ Not authenticated")
        if not client.client_id:
            print("Run setup_schwab_credentials() first")
        else:
            print("Run client.authenticate() for setup instructions")
        return False


if __name__ == "__main__":
    test_authentication()