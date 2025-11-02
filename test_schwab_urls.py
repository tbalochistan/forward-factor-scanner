"""
Test the official Schwab API endpoints
"""
import requests

# Test the official Schwab API endpoints
official_urls = [
    "https://api.schwabapi.com",
    "https://api.schwabapi.com/v1/oauth/authorize",
    "https://api.schwabapi.com/v1/oauth/token",
    "https://api.schwabapi.com/trader/v1"
]

print("Testing official Schwab API endpoints...")

for url in official_urls:
    try:
        response = requests.get(url, timeout=5)
        print(f"✓ {url} - Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ {url} - Error: {e}")

print("\nNote: 404 errors are expected for base URLs without specific endpoints.")
print("The OAuth endpoints should return different status codes when accessed directly.")