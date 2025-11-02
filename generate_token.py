#!/usr/bin/env python3
"""
Simple utility to generate and save Schwab API tokens.
Use this when you just want to refresh your tokens without running the main script.
"""

import sys
import os
import platform
from pathlib import Path

# Determine the base path based on the operating system
if platform.system() == "Linux":
    base_path = os.path.join(str(Path.home()), 'SchwabAccountConfig')
else:  
    base_path = r'C:\SchwabAccountConfig'

# Add the path to the classified_info.py file
sys.path.append(base_path)

try:
    import classified_info
except ImportError:
    print(f"❌ Could not import classified_info.py from {base_path}")
    print("Please ensure the file exists and contains the required credentials.")
    sys.exit(1)

# Import the client from our main script
from schwab_orders import SchwabAPIClient

def main():
    print("🔑 Schwab Token Generator")
    print("=" * 40)
    print("This utility will generate fresh Schwab API tokens.")
    print("You'll need to complete the OAuth flow in your browser.")
    print()
    print("📁 Tokens will be saved to: C:\\SchwabAccountConfig\\DirectAPIUsage\\token.json")
    print("   (This won't affect your existing tokens used by other programs)")
    print()
    
    try:
        # Create client and force fresh authentication
        client = SchwabAPIClient()
        
        # Clear any existing tokens
        print("🧹 Clearing existing tokens...")
        client._clear_tokens()
        
        # Get fresh tokens
        print("🔄 Starting fresh authentication...")
        client.authenticate()
        
        # Test the new tokens
        print("🧪 Testing new tokens...")
        if client._test_token_validity():
            print("✅ Success! New tokens are working correctly.")
            print(f"📁 Tokens saved to: {client.token_path}")
            print("🔒 Your existing tokens in other locations are untouched.")
        else:
            print("⚠️  Warning: Tokens were created but may not be working properly.")
            
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()