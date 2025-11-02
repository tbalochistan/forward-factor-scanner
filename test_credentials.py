#!/usr/bin/env python3
"""
Test script to verify credentials are accessible.
"""

import sys
import os
import platform
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
    print("✓ Successfully imported classified_info")
    print(f"✓ Base path used: {base_path}")
    print(f"✓ API Key: {classified_info.SCHWAB_API_KEY[:10]}...")
    print(f"✓ Account 1 Number: {classified_info.ACCOUNT_1_NUM}")
    print(f"✓ Account 1 Hash: {classified_info.ACCOUNT_1_HASH[:16]}...")
    print(f"✓ Token Path: {classified_info.SCHWAB_TOKEN_PATH}")
    print(f"✓ Redirect URI: {classified_info.REDIRECT_URI}")
except ImportError as e:
    print(f"❌ Could not import classified_info: {e}")
    print(f"Please ensure the file exists at {base_path}\\classified_info.py")
except AttributeError as e:
    print(f"❌ Missing required attribute in classified_info: {e}")