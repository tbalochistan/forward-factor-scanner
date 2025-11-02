Write a Python script that connects to the Charles Schwab API to retrieve my order history.

Requirements:
1. Use OAuth 2.0 for authentication (following Schwab’s API documentation).
2. Once authenticated, call the endpoint that returns account order history.
3. Allow filtering by date range (e.g., start_date and end_date as parameters).
4. Print the results in a readable JSON format and optionally save them to a local file (orders.json).
5. Include clear comments explaining each step (authentication, API call, data parsing).
6. Use environment variables for API keys, secrets, and tokens — do not hardcode credentials.
7. Use the `requests` library.
8. Handle errors gracefully (e.g., expired tokens, rate limits, invalid responses).

Example usage:
```bash
python schwab_orders.py --start_date 2024-01-01 --end_date 2024-12-31