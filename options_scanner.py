"""
Schwab Options Chain Scanner for Forward Factor Strategy

This module provides options chain scanning capabilities using the Schwab API.
Retrieves options data for multiple expirations to support Forward Factor calculations.
"""

import sys
import os
import json
import requests
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import time
import logging
from pathlib import Path

# Import the existing Schwab API client
from schwab_api_utils import SchwabAPIClient

# Import IV calculator
from iv_calculator import ImpliedVolatilityCalculator


@dataclass 
class OptionChain:
    """Container for option chain data"""
    ticker: str
    expiration_date: str
    days_to_expiration: int
    strikes: Dict[str, Any]  # Strike -> option data
    underlying_price: float
    
    
@dataclass
class OptionData:
    """Individual option contract data"""
    ticker: str
    expiration: str
    strike: float
    option_type: str  # 'CALL' or 'PUT'
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None


class SchwabOptionsScanner(SchwabAPIClient):
    """
    Options chain scanner extending the base Schwab API client.
    
    Provides methods to retrieve and analyze options chains for 
    Forward Factor calculations.
    """
    
    def __init__(self):
        """Initialize the options scanner."""
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Configure logging if not already done
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def is_authenticated(self) -> bool:
        """
        Check if the scanner is properly authenticated.
        
        Returns:
            True if we have a valid access token, False otherwise
        """
        if not self.access_token:
            return False
        
        # Check if token is expired
        if self.token_expires_at and datetime.now() >= self.token_expires_at:
            return False
        
        return True
    
    def get_option_chain(
        self, 
        ticker: str, 
        contract_type: str = "ALL",
        strategy: str = "SINGLE",
        range_option: str = "ALL",
        expiration_count: int = 2
    ) -> Optional[Dict]:
        """
        Retrieve option chain for a given ticker.
        
        Args:
            ticker: Stock symbol (e.g., 'AAPL')
            contract_type: 'CALL', 'PUT', or 'ALL'
            strategy: 'SINGLE', 'ANALYTICAL', etc.
            range_option: 'ITM', 'NTM', 'OTM', 'SAK', 'SBK', 'SNK', 'ALL'
            expiration_count: Number of expiration months to retrieve
            
        Returns:
            Raw option chain data from Schwab API
        """
        if not self.is_authenticated():
            self.logger.error("Not authenticated. Call authenticate() first.")
            return None
        
        url = "https://api.schwabapi.com/marketdata/v1/chains"
        
        # Limit strikes for large tickers to avoid buffer overflow
        strike_count = None
        if ticker.upper() in ['SPY', 'QQQ', 'IWM', 'DIA']:
            strike_count = 50  # Limit to 50 strikes around ATM
            range_option = "NTM"  # Near the money only
        
        params = {
            'symbol': ticker.upper(),
            'contractType': contract_type,
            'strategy': strategy,
            'range': range_option,
            'optionType': 'S'  # Standard options
        }
        
        # Add strike count if specified
        if strike_count:
            params['strikeCount'] = strike_count
        
        # For expiration months, use 'ALL' to get all available expirations
        # The expiration_count parameter is not supported by Schwab API
        params['expMonth'] = 'ALL'
            
        try:
            # Create headers with authorization
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json'
            }
            
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=30
            )
            
            self.logger.debug(f"Options chain request: {response.url}")
            
            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"Successfully retrieved option chain for {ticker}")
                return data
            else:
                self.logger.error(
                    f"Failed to retrieve option chain for {ticker}. "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed for {ticker}: {e}")
            return None
    
    def parse_option_chain(self, raw_data: Dict, ticker: str) -> List[OptionChain]:
        """
        Parse raw option chain data into structured format.
        
        Args:
            raw_data: Raw JSON response from Schwab API
            ticker: Stock ticker symbol
            
        Returns:
            List of OptionChain objects organized by expiration
        """
        if not raw_data:
            return []
        
        chains = []
        underlying_price = raw_data.get('underlyingPrice', 0.0)
        
        # Process call options
        call_exp_map = raw_data.get('callExpDateMap', {})
        put_exp_map = raw_data.get('putExpDateMap', {})
        
        # Combine all expiration dates
        all_expirations = set(call_exp_map.keys()).union(set(put_exp_map.keys()))
        
        for exp_key in sorted(all_expirations):
            # Parse expiration date and calculate DTE
            exp_date_str = exp_key.split(':')[0]  # Remove :X suffix if present
            exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
            dte = (exp_date - date.today()).days
            
            if dte < 0:  # Skip expired options
                continue
            
            strikes = {}
            
            # Process calls for this expiration
            if exp_key in call_exp_map:
                for strike_price, strike_data in call_exp_map[exp_key].items():
                    if not isinstance(strike_data, list):
                        continue
                    
                    for option in strike_data:
                        strikes[f"{strike_price}_CALL"] = self._parse_option_data(
                            option, ticker, exp_date_str, float(strike_price), 'CALL',
                            underlying_price, dte
                        )
            
            # Process puts for this expiration
            if exp_key in put_exp_map:
                for strike_price, strike_data in put_exp_map[exp_key].items():
                    if not isinstance(strike_data, list):
                        continue
                    
                    for option in strike_data:
                        strikes[f"{strike_price}_PUT"] = self._parse_option_data(
                            option, ticker, exp_date_str, float(strike_price), 'PUT',
                            underlying_price, dte
                        )
            
            if strikes:  # Only add if we have option data
                chain = OptionChain(
                    ticker=ticker,
                    expiration_date=exp_date_str,
                    days_to_expiration=dte,
                    strikes=strikes,
                    underlying_price=underlying_price
                )
                chains.append(chain)
        
        return chains
    
    def _parse_option_data(
        self, 
        option_data: Dict, 
        ticker: str, 
        expiration: str, 
        strike: float, 
        option_type: str,
        underlying_price: float = 0.0,
        days_to_expiration: int = 0
    ) -> OptionData:
        """Parse individual option contract data with real IV calculation."""
        
        # Get basic option data
        bid = option_data.get('bid', 0.0)
        ask = option_data.get('ask', 0.0)
        last = option_data.get('last', 0.0)
        
        # Calculate real implied volatility using py_vollib
        calc = ImpliedVolatilityCalculator()
        mid_price = calc.get_option_mid_price(bid, ask, last)
        
        real_iv = 0.0  # Default fallback
        if mid_price and underlying_price > 0 and days_to_expiration > 0:
            time_to_expiry = calc.days_to_years(days_to_expiration)
            flag = 'c' if option_type == 'CALL' else 'p'
            
            calculated_iv = calc.calculate_iv(
                mid_price, underlying_price, strike, 
                time_to_expiry, option_type=flag
            )
            
            if calculated_iv:
                real_iv = calculated_iv
            else:
                # Fallback to Schwab's theoretical volatility if calculation fails
                real_iv = option_data.get('theoreticalVolatility', 0.0) / 100.0
        else:
            # Use Schwab's data as fallback if we can't calculate
            real_iv = option_data.get('theoreticalVolatility', 0.0) / 100.0
        
        return OptionData(
            ticker=ticker,
            expiration=expiration,
            strike=strike,
            option_type=option_type,
            bid=bid,
            ask=ask,
            last=last,
            volume=option_data.get('totalVolume', 0),
            open_interest=option_data.get('openInterest', 0),
            implied_volatility=real_iv,  # Use real calculated IV
            delta=option_data.get('delta'),
            gamma=option_data.get('gamma'),
            theta=option_data.get('theta'),
            vega=option_data.get('vega')
        )
    
    def get_near_and_next_term_chains(self, ticker: str) -> Tuple[Optional[OptionChain], Optional[OptionChain]]:
        """
        Get option chains for professional Forward Factor timeframes.
        Checks all three standard pairs: 30/60, 30/90, and 60/90 DTE with ±5 day buffers.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Tuple of (near_term_chain, next_term_chain) with optimal timeframes
        """
        raw_data = self.get_option_chain(ticker, expiration_count=10)  # Get more options for selection
        if not raw_data:
            return None, None
        
        chains = self.parse_option_chain(raw_data, ticker)
        if len(chains) < 2:
            self.logger.warning(f"Insufficient option chains for {ticker}. Need at least 2, got {len(chains)}")
            return None, None
        
        # Sort by DTE
        chains.sort(key=lambda x: x.days_to_expiration)
        
        # Filter for valid chains (minimum 7 DTE)
        valid_chains = [chain for chain in chains if chain.days_to_expiration >= 7]
        
        if len(valid_chains) < 2:
            self.logger.warning(f"Insufficient valid option chains for {ticker} after DTE filtering")
            return None, None
        
        # Define professional timeframe targets with larger buffers to capture real expirations
        timeframe_pairs = [
            # (near_target, near_buffer, next_target, next_buffer, name)
            (30, 15, 60, 20, "30/60"),  # 15-45 DTE vs 40-80 DTE
            (30, 15, 90, 25, "30/90"),  # 15-45 DTE vs 65-115 DTE  
            (60, 20, 90, 25, "60/90"),  # 40-80 DTE vs 65-115 DTE
        ]
        
        best_pair = None
        best_score = float('inf')  # Lower score is better
        
        # Try each professional timeframe combination
        for near_target, near_buffer, next_target, next_buffer, name in timeframe_pairs:
            near_min = near_target - near_buffer
            near_max = near_target + near_buffer
            next_min = next_target - next_buffer
            next_max = next_target + next_buffer
            
            # Find chains that match this timeframe
            for i, chain1 in enumerate(valid_chains):
                if near_min <= chain1.days_to_expiration <= near_max:
                    for chain2 in valid_chains[i+1:]:
                        if next_min <= chain2.days_to_expiration <= next_max:
                            # Calculate how close this is to the ideal targets
                            near_deviation = abs(chain1.days_to_expiration - near_target)
                            next_deviation = abs(chain2.days_to_expiration - next_target)
                            total_score = near_deviation + next_deviation
                            
                            if total_score < best_score:
                                best_score = total_score
                                best_pair = (chain1, chain2, name)
                                
        if best_pair:
            near_chain, next_chain, timeframe_name = best_pair
            self.logger.info(f"Found optimal {timeframe_name} timeframe for {ticker}: {near_chain.days_to_expiration} vs {next_chain.days_to_expiration} DTE")
            return near_chain, next_chain
        
        # If no professional timeframes available, fall back to best available with minimum gap
        self.logger.warning(f"No professional timeframes available for {ticker}, using fallback")
        
        # Look for chains with at least 14-day gap (better than 7)
        for i, chain1 in enumerate(valid_chains[:-1]):
            for chain2 in valid_chains[i+1:]:
                if chain2.days_to_expiration - chain1.days_to_expiration >= 14:
                    self.logger.info(f"Using fallback timeframe for {ticker}: {chain1.days_to_expiration} vs {chain2.days_to_expiration}")
                    return chain1, chain2
        
        # Last resort: just use first two valid chains
        near_chain = valid_chains[0]
        next_chain = valid_chains[1]
        self.logger.warning(f"Using minimal timeframe for {ticker}: {near_chain.days_to_expiration} vs {next_chain.days_to_expiration}")
        
        return near_chain, next_chain
    
    def find_atm_options(self, chain: OptionChain, option_type: str = 'CALL') -> Optional[OptionData]:
        """
        Find the at-the-money option for a given chain.
        
        Args:
            chain: OptionChain object
            option_type: 'CALL' or 'PUT'
            
        Returns:
            OptionData for the ATM option
        """
        underlying = chain.underlying_price
        min_diff = float('inf')
        atm_option = None
        
        for key, option in chain.strikes.items():
            if not key.endswith(f"_{option_type}"):
                continue
            
            strike_diff = abs(option.strike - underlying)
            if strike_diff < min_diff:
                min_diff = strike_diff
                atm_option = option
        
        return atm_option
    
    def scan_multiple_tickers(
        self, 
        tickers: List[str], 
        delay_seconds: float = 0.5
    ) -> Dict[str, Tuple[Optional[OptionChain], Optional[OptionChain]]]:
        """
        Scan option chains for multiple tickers.
        
        Args:
            tickers: List of stock symbols
            delay_seconds: Delay between API calls to avoid rate limits
            
        Returns:
            Dict mapping ticker -> (near_term_chain, next_term_chain)
        """
        results = {}
        
        for i, ticker in enumerate(tickers):
            self.logger.info(f"Scanning {ticker} ({i+1}/{len(tickers)})")
            
            try:
                near_chain, next_chain = self.get_near_and_next_term_chains(ticker)
                results[ticker] = (near_chain, next_chain)
                
                if near_chain and next_chain:
                    self.logger.info(
                        f"{ticker}: Found chains with DTE {near_chain.days_to_expiration} "
                        f"and {next_chain.days_to_expiration}"
                    )
                else:
                    self.logger.warning(f"{ticker}: Failed to get valid option chains")
                
            except Exception as e:
                self.logger.error(f"Error scanning {ticker}: {e}")
                results[ticker] = (None, None)
            
            # Rate limiting
            if i < len(tickers) - 1:  # Don't sleep after the last ticker
                time.sleep(delay_seconds)
        
        return results
    
    def get_chain_summary(self, chain: OptionChain) -> Dict[str, Any]:
        """Get summary statistics for an option chain."""
        if not chain or not chain.strikes:
            return {}
        
        call_count = sum(1 for key in chain.strikes.keys() if key.endswith('_CALL'))
        put_count = sum(1 for key in chain.strikes.keys() if key.endswith('_PUT'))
        
        # Calculate average volume and open interest
        total_volume = sum(opt.volume for opt in chain.strikes.values())
        total_oi = sum(opt.open_interest for opt in chain.strikes.values())
        
        return {
            'ticker': chain.ticker,
            'expiration': chain.expiration_date,
            'dte': chain.days_to_expiration,
            'underlying_price': chain.underlying_price,
            'call_count': call_count,
            'put_count': put_count,
            'total_volume': total_volume,
            'total_open_interest': total_oi,
            'avg_volume': total_volume / len(chain.strikes) if chain.strikes else 0,
            'avg_open_interest': total_oi / len(chain.strikes) if chain.strikes else 0
        }


if __name__ == "__main__":
    # Test the options scanner
    print("Schwab Options Scanner Test")
    print("=" * 50)
    
    scanner = SchwabOptionsScanner()
    
    # Authenticate first
    try:
        scanner.authenticate()
        print("✓ Authentication successful")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        sys.exit(1)
    
    # Test with a few midcap tickers
    test_tickers = ['TEAM', 'SNOW', 'CRWD']
    
    print(f"\nScanning options for: {', '.join(test_tickers)}")
    results = scanner.scan_multiple_tickers(test_tickers, delay_seconds=1.0)
    
    print(f"\nResults:")
    for ticker, (near_chain, next_chain) in results.items():
        print(f"\n{ticker}:")
        if near_chain and next_chain:
            near_summary = scanner.get_chain_summary(near_chain)
            next_summary = scanner.get_chain_summary(next_chain)
            
            print(f"  Near term: {near_summary['dte']} DTE, "
                  f"{near_summary['call_count']} calls, {near_summary['put_count']} puts")
            print(f"  Next term: {next_summary['dte']} DTE, "
                  f"{next_summary['call_count']} calls, {next_summary['put_count']} puts")
            print(f"  Underlying: ${near_summary['underlying_price']:.2f}")
        else:
            print("  ✗ No valid option chains found")