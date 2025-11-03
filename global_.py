"""
Global configuration for Schwab API credentials
Loads credentials from classified_info.py file following your pattern
"""

import os
import platform
import importlib.util
from pathlib import Path

# Credential Storage
cred_location = "local"  # Default value is "local"

# Determine the base path based on the operating system
if platform.system() == "Linux":
    base_path = os.path.join(str(Path.home()), 'SchwabAccountConfig')
else:  
    # Assuming Windows
    base_path = r'C:\SchwabAccountConfig'

# Construct the full paths
classifiedInfo = os.path.join(base_path, 'classified_info.py')
schwab_token_path = os.path.join(base_path, 'DirectAPIUsage', 'token.json')

# Import private info such as credentials from classifiedInfo module
spec = importlib.util.spec_from_file_location("classified_info", classifiedInfo)
classifiedModule = importlib.util.module_from_spec(spec)
spec.loader.exec_module(classifiedModule)

# Load credentials from classified module
CLIENT_ID = classifiedModule.SCHWAB_API_KEY
CLIENT_SECRET = classifiedModule.SCHWAB_SECRET
REDIRECT_URI = classifiedModule.REDIRECT_URI