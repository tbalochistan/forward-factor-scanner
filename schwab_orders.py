#!/usr/bin/env python3
"""
Charles Schwab API Order History Retrieval Script

This script connects to the Charles Schwab API using OAuth 2.0 authentication
to retrieve order history for specified accounts within a given date range.

Author: Your Name
Date: November 2, 2025
"""

import os
import sys
import json
import argparse
import requests
import base64
import webbrowser
import urllib.parse
import platform
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from pathlib import Path

# Determine the base path based on the operating system
if platform.system() == "Linux":
    # Use the user's home directory (e.g. for me its, /home/talmas Therefore final path will be: '/home/talmas/SchwabAccountConfig')
    base_path = os.path.join(str(Path.home()), 'SchwabAccountConfig')
else:  
    # Assuming Windows
    base_path = r'C:\SchwabAccountConfig'

# Add the path to the classified_info.py file
sys.path.append(base_path)

try:
    import classified_info
except ImportError:
    print(f"Error: Could not import classified_info.py from {base_path}")
    print("Please ensure the file exists and contains the required credentials.")
    sys.exit(1)


class SchwabAPIClient:
    """
    A client for interacting with the Charles Schwab API.
    
    This class handles OAuth 2.0 authentication and provides methods
    to retrieve order history and other account information.
    """
    
    def __init__(self):
        """Initialize the Schwab API client with credentials from classified_info."""
        self.api_key = classified_info.SCHWAB_API_KEY
        self.secret = classified_info.SCHWAB_SECRET
        # Use the redirect URI that matches your Schwab app configuration
        self.redirect_uri = classified_info.REDIRECT_URI_WITH_PORT  # This should be https://127.0.0.1:8182
        
        # Use a separate token path for this script to avoid conflicts with other programs
        self.token_path = r'C:\SchwabAccountConfig\DirectAPIUsage\token.json'
        
        # Schwab API base URLs (OFFICIAL SCHWAB API ENDPOINTS)
        self.auth_url = "https://api.schwabapi.com/v1/oauth/authorize"
        self.token_url = "https://api.schwabapi.com/v1/oauth/token"  
        self.base_api_url = "https://api.schwabapi.com/trader/v1"
        
        # Enable debug mode to see what's happening
        self.debug_mode = True
        
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        
        # Load existing tokens if available
        self._load_tokens()
    
    def _load_tokens(self) -> None:
        """Load existing tokens from the token file."""
        try:
            if os.path.exists(self.token_path):
                with open(self.token_path, 'r') as f:
                    token_data = json.load(f)
                    self.access_token = token_data.get('access_token')
                    self.refresh_token = token_data.get('refresh_token')
                    self.token_expires_at = token_data.get('expires_at')
                    print("✓ Loaded existing tokens from file")
        except Exception as e:
            print(f"Warning: Could not load existing tokens: {e}")
    
    def _save_tokens(self, token_response: Dict) -> None:
        """Save tokens to the token file."""
        try:
            # Calculate expiration time
            expires_in = token_response.get('expires_in', 1800)  # Default 30 minutes
            expires_at = datetime.now().timestamp() + expires_in
            
            token_data = {
                'access_token': token_response['access_token'],
                'refresh_token': token_response.get('refresh_token', self.refresh_token),
                'expires_at': expires_at,
                'token_type': token_response.get('token_type', 'Bearer')
            }
            
            # Ensure directory exists (create DirectAPIUsage folder if needed)
            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
            
            with open(self.token_path, 'w') as f:
                json.dump(token_data, f, indent=2)
            
            # Update instance variables
            self.access_token = token_data['access_token']
            self.refresh_token = token_data['refresh_token']
            self.token_expires_at = token_data['expires_at']
            
            print("✓ Tokens saved successfully to DirectAPIUsage folder")
            
        except Exception as e:
            print(f"Error saving tokens: {e}")
    
    def _is_token_expired(self) -> bool:
        """Check if the current access token is expired."""
        if not self.access_token or not self.token_expires_at:
            return True
        
        # Add 5-minute buffer before expiration
        buffer_time = 300  # 5 minutes
        return datetime.now().timestamp() >= (self.token_expires_at - buffer_time)
    
    def _test_token_validity(self) -> bool:
        """Test if the current access token actually works by making a simple API call."""
        if not self.access_token:
            return False
        
        try:
            # Try a simple API call to test the token
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json'
            }
            
            # Test with account numbers endpoint (lightweight call)
            test_url = f"{self.base_api_url}/accounts/accountNumbers"
            response = requests.get(test_url, headers=headers, timeout=10)
            
            # Token is valid if we get a successful response
            return response.status_code == 200
            
        except Exception as e:
            print(f"Token validation failed: {e}")
            return False
    
    def _clear_tokens(self) -> None:
        """Clear stored tokens and delete token file."""
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        
        # Delete the token file if it exists
        try:
            if os.path.exists(self.token_path):
                os.remove(self.token_path)
                print("✓ Cleared old token file")
        except Exception as e:
            print(f"Warning: Could not delete token file: {e}")
    
    def _get_authorization_code(self) -> str:
        """
        Get authorization code through OAuth 2.0 flow.
        
        This method opens a web browser for user authorization and waits
        for the authorization code to be entered manually.
        """
        # Prepare authorization URL
        auth_params = {
            'client_id': self.api_key,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code'
            # Note: Schwab API may not require explicit scope parameter
        }
        
        auth_url_full = f"{self.auth_url}?{urllib.parse.urlencode(auth_params)}"
        
        print("\n" + "="*60)
        print("AUTHORIZATION REQUIRED")
        print("="*60)
        print("Opening web browser for Schwab authorization...")
        print(f"If browser doesn't open, visit: {auth_url_full}")
        print("\nAfter authorizing, you'll be redirected to a URL that starts with:")
        print(f"{self.redirect_uri}?code=...")
        print("\nPlease copy the 'code' parameter from the redirected URL.")
        
        # Open browser
        webbrowser.open(auth_url_full)
        
        # Get authorization code from user
        auth_code = input("\nEnter the authorization code: ").strip()
        
        # If user pasted the full URL, extract just the code parameter
        if auth_code.startswith('http'):
            try:
                parsed_url = urllib.parse.urlparse(auth_code)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                if 'code' in query_params:
                    auth_code = query_params['code'][0]
                    print(f"✓ Extracted authorization code from URL: {auth_code[:20]}...")
                else:
                    raise ValueError("No 'code' parameter found in URL")
            except Exception as e:
                raise ValueError(f"Could not extract code from URL: {e}")
        
        if not auth_code:
            raise ValueError("Authorization code is required")
        
        return auth_code
    
    def _exchange_code_for_tokens(self, auth_code: str) -> Dict:
        """Exchange authorization code for access and refresh tokens."""
        # Prepare credentials for Basic Auth
        credentials = f"{self.api_key}:{self.secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': self.redirect_uri
        }
        
        if hasattr(self, 'debug_mode') and self.debug_mode:
            print(f"DEBUG: Token URL: {self.token_url}")
            print(f"DEBUG: Headers: {headers}")
            print(f"DEBUG: Data: {data}")
        
        try:
            response = requests.post(self.token_url, headers=headers, data=data)
            
            if hasattr(self, 'debug_mode') and self.debug_mode:
                print(f"DEBUG: Response Status: {response.status_code}")
                print(f"DEBUG: Response Headers: {response.headers}")
                print(f"DEBUG: Response Text: {response.text}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Failed to exchange authorization code")
            print(f"Status Code: {getattr(e.response, 'status_code', 'N/A')}")
            print(f"Response Text: {getattr(e.response, 'text', 'N/A')}")
            raise Exception(f"Failed to exchange authorization code: {e}")
    
    def _refresh_access_token(self) -> Dict:
        """Refresh the access token using the refresh token."""
        if not self.refresh_token:
            raise ValueError("No refresh token available")
        
        credentials = f"{self.api_key}:{self.secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }
        
        try:
            response = requests.post(self.token_url, headers=headers, data=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to refresh token: {e}")
    
    def authenticate(self) -> None:
        """
        Authenticate with the Schwab API.
        
        This method handles the complete OAuth 2.0 flow:
        1. Check if existing tokens are valid
        2. Refresh tokens if needed and possible
        3. Perform full authorization only if necessary
        """
        print("Authenticating with Schwab API...")
        
        # If we have tokens, test if they actually work
        if self.access_token and not self._is_token_expired():
            print("Testing existing access token...")
            if self._test_token_validity():
                print("✓ Using existing valid access token")
                return
            else:
                print("✗ Existing token is invalid, will refresh or re-authenticate")
        
        # Try to refresh tokens if we have a refresh token
        if self.refresh_token:
            try:
                print("Attempting to refresh access token...")
                token_response = self._refresh_access_token()
                self._save_tokens(token_response)
                print("✓ Access token refreshed successfully")
                
                # Test the new token
                if self._test_token_validity():
                    print("✓ Refreshed token is working")
                    return
                else:
                    print("✗ Refreshed token still not working")
            except Exception as e:
                print(f"Failed to refresh token: {e}")
        
        # If we get here, we need full re-authentication
        print("⚠️  Full re-authentication required")
        print("Clearing old tokens and starting fresh...")
        self._clear_tokens()
        
        try:
            auth_code = self._get_authorization_code()
            token_response = self._exchange_code_for_tokens(auth_code)
            self._save_tokens(token_response)
            print("✓ Authentication completed successfully")
            
            # Final validation
            if self._test_token_validity():
                print("✓ New token is working correctly")
            else:
                print("⚠️  Warning: New token may have issues")
                
        except Exception as e:
            raise Exception(f"Authentication failed: {e}")
    
    def _make_api_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        Make an authenticated API request to Schwab.
        
        Args:
            endpoint: API endpoint (relative to base_api_url)
            params: Query parameters for the request
            
        Returns:
            JSON response from the API
        """
        if not self.access_token:
            raise ValueError("Not authenticated. Call authenticate() first.")
        
        url = f"{self.base_api_url}/{endpoint.lstrip('/')}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }
        
        if hasattr(self, 'debug_mode') and self.debug_mode:
            print(f"DEBUG: Making request to: {url}")
            print(f"DEBUG: Headers: {headers}")
            print(f"DEBUG: Params: {params}")
        
        try:
            response = requests.get(url, headers=headers, params=params or {})
            
            if hasattr(self, 'debug_mode') and self.debug_mode:
                print(f"DEBUG: Response Status: {response.status_code}")
                print(f"DEBUG: Response Headers: {dict(response.headers)}")
                print(f"DEBUG: Response Text: {response.text[:500]}...")
            
            # Handle rate limiting
            if response.status_code == 429:
                print("Rate limit exceeded. Please wait and try again later.")
                raise Exception("Rate limit exceeded")
            
            # Handle authentication errors
            if response.status_code == 401:
                print("Authentication failed. Token may be expired.")
                raise Exception("Authentication failed")
            
            # Handle bad request with more details
            if response.status_code == 400:
                print(f"Bad Request (400): {response.text}")
                raise Exception(f"Bad Request: {response.text}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {e}")
    
    def get_account_orders(self, account_hash: str, start_date: str = None, 
                          end_date: str = None, max_results: int = 3000) -> Dict:
        """
        Retrieve order history for a specific account.
        
        Args:
            account_hash: The account hash (encrypted account number)
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            max_results: Maximum number of results to return
            
        Returns:
            Order history data from the API
        """
        endpoint = f"accounts/{account_hash}/orders"
        
        params = {}
        
        # Add maxResults parameter
        if max_results:
            params['maxResults'] = max_results
        
        # Schwab API requires fromEnteredTime parameter
        if start_date:
            # Convert YYYY-MM-DD to ISO format with timezone
            start_datetime = f"{start_date}T00:00:00.000Z"
        else:
            # Default to 90 days ago if no start date provided
            from datetime import datetime, timedelta
            default_start = datetime.now() - timedelta(days=90)
            start_datetime = default_start.strftime("%Y-%m-%dT00:00:00.000Z")
        
        params['fromEnteredTime'] = start_datetime
        
        # Add end date if provided
        if end_date:
            end_datetime = f"{end_date}T23:59:59.999Z"
            params['toEnteredTime'] = end_datetime
        
        print(f"Retrieving orders for account {account_hash[:8]}...")
        if start_date or end_date:
            print(f"Date range: {start_date or 'auto-90-days'} to {end_date or 'now'}")
        
        print(f"DEBUG: Using endpoint: {endpoint}")
        print(f"DEBUG: Using params: {params}")
        
        return self._make_api_request(endpoint, params)
    
    def get_all_accounts_orders(self, start_date: str = None, 
                               end_date: str = None) -> Dict:
        """
        Retrieve order history for all configured accounts.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Combined order history data for all accounts
        """
        all_orders = {}
        
        # Get orders for Account 1
        try:
            account_1_orders = self.get_account_orders(
                classified_info.ACCOUNT_1_HASH, start_date, end_date
            )
            all_orders[f"Account_{classified_info.ACCOUNT_1_NUM}_RegT"] = account_1_orders
        except Exception as e:
            print(f"Failed to get orders for Account 1: {e}")
        
        # Get orders for Account 2
        try:
            account_2_orders = self.get_account_orders(
                classified_info.ACCOUNT_2_HASH, start_date, end_date
            )
            all_orders[f"Account_{classified_info.ACCOUNT_2_NUM}_ROTH"] = account_2_orders
        except Exception as e:
            print(f"Failed to get orders for Account 2: {e}")
        
        return all_orders


def validate_date_format(date_string: str) -> bool:
    """Validate that a date string is in YYYY-MM-DD format."""
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def save_orders_to_file(orders_data: Dict, filename: str = "orders.json") -> None:
    """Save order data to a JSON file."""
    try:
        with open(filename, 'w') as f:
            json.dump(orders_data, f, indent=2, default=str)
        print(f"✓ Order data saved to {filename}")
    except Exception as e:
        print(f"Error saving to file: {e}")


def print_order_summary(orders_data: Dict) -> None:
    """Print a summary of the order data."""
    print("\n" + "="*60)
    print("ORDER HISTORY SUMMARY")
    print("="*60)
    
    total_orders = 0
    
    for account_name, account_orders in orders_data.items():
        if isinstance(account_orders, list):
            order_count = len(account_orders)
            total_orders += order_count
            print(f"\n{account_name}: {order_count} orders")
            
            # Show recent orders summary
            if order_count > 0:
                print("  Recent orders:")
                for i, order in enumerate(account_orders[:5]):  # Show first 5
                    symbol = order.get('orderLegCollection', [{}])[0].get('symbol', 'N/A')
                    status = order.get('status', 'N/A')
                    order_type = order.get('orderType', 'N/A')
                    entered_time = order.get('enteredTime', 'N/A')
                    print(f"    {i+1}. {symbol} - {order_type} - {status} - {entered_time}")
                
                if order_count > 5:
                    print(f"    ... and {order_count - 5} more orders")
    
    print(f"\nTotal orders across all accounts: {total_orders}")


def main():
    """Main function to handle command line arguments and execute the script."""
    parser = argparse.ArgumentParser(
        description="Retrieve order history from Charles Schwab API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python schwab_orders.py --start_date 2025-10-01 --end_date 2025-10-31
  python schwab_orders.py --start_date 2025-11-01
  python schwab_orders.py --save_file my_orders.json
        """
    )
    
    parser.add_argument(
        '--start_date',
        type=str,
        help='Start date for order history (YYYY-MM-DD format)'
    )
    
    parser.add_argument(
        '--end_date',
        type=str,
        help='End date for order history (YYYY-MM-DD format)'
    )
    
    parser.add_argument(
        '--save_file',
        type=str,
        default='orders.json',
        help='Filename to save order data (default: orders.json)'
    )
    
    parser.add_argument(
        '--no_save',
        action='store_true',
        help='Do not save results to file'
    )
    
    parser.add_argument(
        '--account',
        type=str,
        choices=['1', '2', 'all'],
        default='all',
        help='Which account to query (1, 2, or all)'
    )
    
    parser.add_argument(
        '--force_auth',
        action='store_true',
        help='Force re-authentication (clear existing tokens and get new ones)'
    )
    
    args = parser.parse_args()
    
    # Validate date formats
    if args.start_date and not validate_date_format(args.start_date):
        print("Error: start_date must be in YYYY-MM-DD format")
        sys.exit(1)
    
    if args.end_date and not validate_date_format(args.end_date):
        print("Error: end_date must be in YYYY-MM-DD format")
        sys.exit(1)
    
    # Validate date range
    if args.start_date and args.end_date:
        start = datetime.strptime(args.start_date, '%Y-%m-%d')
        end = datetime.strptime(args.end_date, '%Y-%m-%d')
        if start > end:
            print("Error: start_date must be before end_date")
            sys.exit(1)
    
    try:
        # Initialize and authenticate the client
        client = SchwabAPIClient()
        
        # Force fresh authentication if requested
        if args.force_auth:
            print("🔄 Force authentication requested - clearing existing tokens")
            client._clear_tokens()
        
        client.authenticate()
        
        # Retrieve order history based on account selection
        if args.account == 'all':
            orders_data = client.get_all_accounts_orders(args.start_date, args.end_date)
        elif args.account == '1':
            orders_data = {
                f"Account_{classified_info.ACCOUNT_1_NUM}_RegT": 
                client.get_account_orders(classified_info.ACCOUNT_1_HASH, args.start_date, args.end_date)
            }
        elif args.account == '2':
            orders_data = {
                f"Account_{classified_info.ACCOUNT_2_NUM}_ROTH": 
                client.get_account_orders(classified_info.ACCOUNT_2_HASH, args.start_date, args.end_date)
            }
        
        # Print results in readable format
        print("\n" + "="*60)
        print("RAW ORDER DATA")
        print("="*60)
        print(json.dumps(orders_data, indent=2, default=str))
        
        # Print summary
        print_order_summary(orders_data)
        
        # Save to file unless --no_save is specified
        if not args.no_save:
            save_orders_to_file(orders_data, args.save_file)
        
        print(f"\n✓ Order history retrieval completed successfully")
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()