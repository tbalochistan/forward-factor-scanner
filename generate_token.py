"""
Schwab API Token Generator

This script helps generate and refresh Schwab API tokens.
Handles the OAuth2 flow for getting access and refresh tokens.
"""

import os
import json
import requests
import base64
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
import webbrowser
import time


class SchwabTokenGenerator:
    """Generates and manages Schwab API tokens"""
    
    def __init__(self):
        # Load credentials
        self.client_id = None
        self.client_secret = None
        self.redirect_uri = "https://localhost:8080/callback"
        
        self._load_credentials()
        
        # API endpoints
        self.auth_url = "https://api.schwabapi.com/v1/oauth/authorize"
        self.token_url = "https://api.schwabapi.com/v1/oauth/token"
        
        # Token file location
        self.token_file = Path("C:/SchwabAccountConfig/DirectAPIUsage/token.json")
    
    def _load_credentials(self):
        """Load credentials from file or environment"""
        import platform
        
        # Use your existing credential pattern
        if platform.system() == "Linux":
            base_path = os.path.join(str(Path.home()), 'SchwabAccountConfig')
        else:  
            # Assuming Windows
            base_path = r'C:\SchwabAccountConfig'
        
        # Try to import from local global_.py first
        try:
            import global_ as schwab_globals
            
            self.client_id = schwab_globals.CLIENT_ID
            self.client_secret = schwab_globals.CLIENT_SECRET  
            self.redirect_uri = schwab_globals.REDIRECT_URI
            
            print("✅ Loaded credentials from local global_.py")
            return True
            
        except Exception as e:
            print(f"⚠️ Could not load from local global_.py: {e}")
        
        # Fallback: Try to import from your main global_.py 
        try:
            import sys
            sys.path.append(r'c:\SchwabApps\TradingApp\schwab_flask_bot')
            import global_ as schwab_globals
            
            self.client_id = schwab_globals.CLIENT_ID
            self.client_secret = schwab_globals.CLIENT_SECRET  
            self.redirect_uri = schwab_globals.REDIRECT_URI
            
            print("✅ Loaded credentials from global_.py")
            return True
            
        except Exception as e:
            print(f"⚠️ Could not load from global_.py: {e}")
        
        # Try environment variables
        self.client_id = os.getenv('SCHWAB_CLIENT_ID')
        self.client_secret = os.getenv('SCHWAB_CLIENT_SECRET')
        
        # Try credentials file in SchwabAccountConfig
        cred_file = os.path.join(base_path, 'credentials.json')
        if os.path.exists(cred_file):
            try:
                with open(cred_file, 'r') as f:
                    creds = json.load(f)
                
                self.client_id = creds.get('client_id') or self.client_id
                self.client_secret = creds.get('client_secret') or self.client_secret
                self.redirect_uri = creds.get('redirect_uri', self.redirect_uri)
                
                print(f"✅ Loaded credentials from {cred_file}")
            except Exception as e:
                print(f"❌ Error loading {cred_file}: {e}")
        
        if not self.client_id or not self.client_secret:
            print("❌ Missing Schwab API credentials!")
            print("Check your global_.py or set environment variables")
            return False
        
        return True
    
    def generate_auth_url(self):
        """Generate authorization URL"""
        if not self.client_id:
            print("❌ Missing client ID")
            return None
        
        auth_url = (
            f"{self.auth_url}?"
            f"client_id={self.client_id}&"
            f"redirect_uri={urllib.parse.quote(self.redirect_uri)}&"
            f"response_type=code"
        )
        
        return auth_url
    
    def get_authorization_code(self):
        """Get authorization code through browser flow"""
        auth_url = self.generate_auth_url()
        if not auth_url:
            return None
        
        print("🌐 Opening browser for authorization...")
        print(f"Auth URL: {auth_url}")
        print()
        
        # Try to open browser
        try:
            webbrowser.open(auth_url)
        except:
            print("Could not open browser automatically")
        
        print("Steps:")
        print("1. Complete authorization in browser")
        print("2. Copy the authorization code from the redirect URL")
        print("3. The URL will look like: https://localhost:8080/callback?code=YOUR_CODE_HERE")
        print()
        
        code = input("Enter the authorization code: ").strip()
        return code
    
    def exchange_code_for_tokens(self, authorization_code: str):
        """Exchange authorization code for tokens"""
        if not self.client_id or not self.client_secret:
            print("❌ Missing credentials")
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
            
            print("🔄 Exchanging code for tokens...")
            response = requests.post(self.token_url, headers=headers, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                self._save_tokens(token_data)
                print("✅ Tokens generated successfully!")
                return True
            else:
                print(f"❌ Token exchange failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def _save_tokens(self, token_data):
        """Save tokens to file"""
        try:
            # Calculate expiration timestamp
            expires_in = token_data.get('expires_in', 1800)  # Default 30 minutes
            expires_at = time.time() + expires_in
            
            # Prepare token data
            tokens = {
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'expires_at': expires_at,
                'token_type': token_data.get('token_type', 'Bearer'),
                'expires_in': expires_in
            }
            
            # Ensure directory exists
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save tokens
            with open(self.token_file, 'w') as f:
                json.dump(tokens, f, indent=2)
            
            expiry_time = datetime.fromtimestamp(expires_at)
            print(f"💾 Tokens saved to: {self.token_file}")
            print(f"🕒 Expires at: {expiry_time}")
            
        except Exception as e:
            print(f"❌ Error saving tokens: {e}")
    
    def refresh_existing_token(self):
        """Refresh existing token using refresh token"""
        if not self.token_file.exists():
            print("❌ No existing token file found")
            return False
        
        try:
            # Load existing tokens
            with open(self.token_file, 'r') as f:
                tokens = json.load(f)
            
            refresh_token = tokens.get('refresh_token')
            if not refresh_token:
                print("❌ No refresh token found")
                return False
            
            # Prepare refresh request
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }
            
            print("🔄 Refreshing token...")
            response = requests.post(self.token_url, headers=headers, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                self._save_tokens(token_data)
                print("✅ Token refreshed successfully!")
                return True
            else:
                print(f"❌ Token refresh failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error refreshing token: {e}")
            return False
    
    def check_token_status(self):
        """Check current token status"""
        if not self.token_file.exists():
            print("❌ No token file found")
            return
        
        try:
            with open(self.token_file, 'r') as f:
                tokens = json.load(f)
            
            expires_at = tokens.get('expires_at')
            if expires_at:
                expiry_time = datetime.fromtimestamp(expires_at)
                current_time = datetime.now()
                
                print(f"📄 Token file: {self.token_file}")
                print(f"🕒 Current time: {current_time}")
                print(f"⏰ Token expires: {expiry_time}")
                
                if current_time < expiry_time:
                    remaining = expiry_time - current_time
                    print(f"✅ Token is valid for {remaining}")
                else:
                    expired_for = current_time - expiry_time
                    print(f"❌ Token expired {expired_for} ago")
                    print("🔄 Use refresh_token() to get a new one")
            
            print(f"🔑 Has refresh token: {bool(tokens.get('refresh_token'))}")
            
        except Exception as e:
            print(f"❌ Error checking token: {e}")


def main():
    """Main token generator interface"""
    generator = SchwabTokenGenerator()
    
    print("🔐 Schwab API Token Generator")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("1. Check token status")
        print("2. Refresh existing token")
        print("3. Generate new token (full auth flow)")
        print("4. Exit")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == '1':
            generator.check_token_status()
        
        elif choice == '2':
            generator.refresh_existing_token()
        
        elif choice == '3':
            code = generator.get_authorization_code()
            if code:
                generator.exchange_code_for_tokens(code)
        
        elif choice == '4':
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice")


if __name__ == "__main__":
    main()