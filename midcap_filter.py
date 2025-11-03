"""
Midcap ticker filtering system for Forward Factor strategy.
Focuses on midcap stocks while excluding large cap names.

This module provides ticker filtering based on market cap tiers and 
index membership to maintain midcap focus as requested.
"""

import json
from typing import Set, List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MarketCapTier:
    """Market cap tier definitions"""
    LARGE_CAP_MIN = 10_000_000_000      # $10B+ = Large Cap
    MID_CAP_MIN = 2_000_000_000         # $2B-$10B = Mid Cap  
    SMALL_CAP_MIN = 300_000_000         # $300M-$2B = Small Cap
    MICRO_CAP_MAX = 300_000_000         # <$300M = Micro Cap


class MidcapFilter:
    """
    Midcap stock filtering system.
    
    Excludes large cap stocks and focuses on midcap opportunities.
    Uses multiple filtering approaches:
    1. Large cap blacklist (S&P 100, Dow 30, etc.)
    2. Market cap ranges
    3. Configurable ticker lists
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize midcap filter.
        
        Args:
            config_dir: Directory for configuration files. Defaults to current directory.
        """
        self.config_dir = Path(config_dir) if config_dir else Path(".")
        
        # Large cap tickers to exclude (major indices)
        self.large_cap_blacklist = self._get_large_cap_blacklist()
        
        # Midcap whitelist (optional - can be empty for broader scanning)
        self.midcap_whitelist = self._load_ticker_list("midcap_whitelist.json")
        
        # Additional exclusions
        self.manual_blacklist = self._load_ticker_list("manual_blacklist.json")
        
    def _get_large_cap_blacklist(self) -> Set[str]:
        """
        Get large cap tickers to exclude.
        Based on major indices and known large cap names.
        """
        # Dow 30 components (all large cap)
        dow_30 = {
            'AAPL', 'MSFT', 'UNH', 'GS', 'HD', 'AMGN', 'MCD', 'CAT', 'CRM', 'V',
            'AXP', 'BA', 'TRV', 'JPM', 'IBM', 'WMT', 'JNJ', 'PG', 'CVX', 'NKE',
            'MRK', 'DIS', 'KO', 'WBA', 'CSCO', 'VZ', 'INTC', 'DOW', 'HON', 'MMM'
        }
        
        # S&P 100 largest components (top market caps)
        sp100_largest = {
            'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK.B',
            'UNH', 'XOM', 'JNJ', 'JPM', 'PG', 'V', 'HD', 'CVX', 'MA', 'PFE', 'ABBV',
            'BAC', 'KO', 'AVGO', 'PEP', 'TMO', 'COST', 'WFC', 'DIS', 'ABT', 'CRM',
            'ACN', 'LIN', 'MRK', 'VZ', 'ADBE', 'DHR', 'TXN', 'NEE', 'WMT', 'NFLX',
            'NKE', 'COP', 'RTX', 'ORCL', 'CMCSA', 'IBM', 'QCOM', 'UPS', 'SPGI', 'AMGN'
        }
        
        # Additional mega caps
        other_large_caps = {
            'BERKSHIRE', 'TSMC', 'ASML', 'LLY', 'NOVO', 'ORCL', 'TM', 'NVO', 'TSM'
        }
        
        # Combine all exclusions
        all_large_caps = dow_30.union(sp100_largest).union(other_large_caps)
        
        return all_large_caps
    
    def _load_ticker_list(self, filename: str) -> Set[str]:
        """Load ticker list from JSON file if it exists."""
        file_path = self.config_dir / filename
        if not file_path.exists():
            return set()
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
                elif isinstance(data, dict) and 'tickers' in data:
                    return set(data['tickers'])
                else:
                    return set()
        except (json.JSONDecodeError, FileNotFoundError):
            return set()
    
    def is_midcap_candidate(self, ticker: str) -> bool:
        """
        Check if ticker is a midcap candidate.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            True if ticker passes midcap filters
        """
        ticker = ticker.upper().strip()
        
        # Exclude large caps
        if ticker in self.large_cap_blacklist:
            return False
        
        # Exclude manual blacklist
        if ticker in self.manual_blacklist:
            return False
        
        # If whitelist exists and ticker not in it, exclude
        if self.midcap_whitelist and ticker not in self.midcap_whitelist:
            return False
        
        # Basic ticker validation
        if not self._is_valid_ticker(ticker):
            return False
        
        return True
    
    def _is_valid_ticker(self, ticker: str) -> bool:
        """Basic ticker symbol validation."""
        if not ticker or len(ticker) > 5:
            return False
        
        # Must be letters/numbers/dots only
        if not ticker.replace('.', '').replace('-', '').isalnum():
            return False
        
        # Exclude some obvious non-equity patterns
        exclude_patterns = ['SPXW', 'QQQ', 'SPY', 'IWM', 'ETF', 'FUND']
        for pattern in exclude_patterns:
            if pattern in ticker:
                return False
        
        return True
    
    def filter_ticker_list(self, tickers: List[str]) -> List[str]:
        """
        Filter a list of tickers to midcap candidates.
        
        Args:
            tickers: List of ticker symbols to filter
            
        Returns:
            Filtered list containing only midcap candidates
        """
        return [ticker for ticker in tickers if self.is_midcap_candidate(ticker)]
    
    def get_suggested_midcap_universe(self) -> List[str]:
        """
        Get a suggested universe of midcap tickers for scanning.
        
        This is a curated list of known midcap names across various sectors.
        """
        suggested_midcaps = [
            # Technology midcaps
            'TEAM', 'OKTA', 'ZS', 'CRWD', 'NET', 'DDOG', 'SNOW', 'PATH', 'ESTC', 'DOCU',
            'TWLO', 'ZM', 'PINS', 'SNAP', 'UBER', 'LYFT', 'RBLX', 'U', 'PLTR', 'COIN',
            
            # Healthcare midcaps  
            'MRNA', 'REGN', 'BIIB', 'ILMN', 'VRTX', 'ALNY', 'BMRN', 'SGEN', 'TECH', 'EXAS',
            'TDOC', 'VEEV', 'ZBH', 'ALGN', 'DXCM', 'ISRG', 'HOLX', 'IDXX', 'IQV', 'MTD',
            
            # Financial midcaps
            'SCHW', 'MS', 'BLK', 'GS', 'CB', 'AIG', 'TFC', 'USB', 'PNC', 'COF',
            'FITB', 'HBAN', 'RF', 'CFG', 'MTB', 'KEY', 'SIVB', 'ZION', 'CMA', 'NTRS',
            
            # Industrial midcaps
            'FDX', 'UPS', 'NSC', 'CSX', 'UNP', 'ODFL', 'CHRW', 'EXPD', 'JBHT', 'SAIA',
            'FAST', 'ITW', 'ETN', 'EMR', 'ROK', 'PH', 'CMI', 'IR', 'OTIS', 'CARR',
            
            # Consumer midcaps
            'SBUX', 'MCD', 'CMG', 'QSR', 'DPZ', 'YUM', 'EAT', 'TXRH', 'WING', 'SHAK',
            'LULU', 'NKE', 'DECK', 'CROX', 'SKX', 'UAA', 'RL', 'PVH', 'TPG', 'GOOS',
            
            # Energy midcaps
            'EOG', 'PXD', 'COP', 'SLB', 'HAL', 'BKR', 'OXY', 'DVN', 'FANG', 'MRO',
            'APA', 'CVE', 'CNQ', 'SU', 'TTE', 'BP', 'RDS.A', 'E', 'SHEL', 'ENB',
            
            # Materials midcaps
            'FCX', 'NEM', 'GOLD', 'AEM', 'KGC', 'AU', 'EGO', 'AGI', 'CDE', 'HL',
            'CLF', 'X', 'MT', 'VALE', 'RIO', 'SCCO', 'TXG', 'AA', 'CENX', 'KALU',
            
            # Real Estate midcaps
            'AMT', 'CCI', 'EQIX', 'DLR', 'PSA', 'EXR', 'AVB', 'EQR', 'UDR', 'CPT',
            'MAA', 'AIV', 'ESS', 'BXP', 'VTR', 'WELL', 'HCP', 'PEAK', 'MPW', 'OHI'
        ]
        
        # Filter the suggested list through our filters
        return self.filter_ticker_list(suggested_midcaps)
    
    def save_configuration(self):
        """Save current filter configuration to files."""
        # Save whitelist if it exists
        if self.midcap_whitelist:
            whitelist_path = self.config_dir / "midcap_whitelist.json"
            with open(whitelist_path, 'w') as f:
                json.dump({"tickers": sorted(list(self.midcap_whitelist))}, f, indent=2)
        
        # Save blacklist if it exists
        if self.manual_blacklist:
            blacklist_path = self.config_dir / "manual_blacklist.json"
            with open(blacklist_path, 'w') as f:
                json.dump({"tickers": sorted(list(self.manual_blacklist))}, f, indent=2)
        
        # Save large cap exclusions for reference
        large_cap_path = self.config_dir / "large_cap_exclusions.json"
        with open(large_cap_path, 'w') as f:
            json.dump({
                "description": "Large cap tickers automatically excluded from midcap scanning",
                "count": len(self.large_cap_blacklist),
                "tickers": sorted(list(self.large_cap_blacklist))
            }, f, indent=2)
    
    def add_to_whitelist(self, tickers: List[str]):
        """Add tickers to midcap whitelist."""
        for ticker in tickers:
            self.midcap_whitelist.add(ticker.upper().strip())
    
    def add_to_blacklist(self, tickers: List[str]):
        """Add tickers to manual blacklist.""" 
        for ticker in tickers:
            self.manual_blacklist.add(ticker.upper().strip())
    
    def get_filter_stats(self) -> Dict[str, int]:
        """Get statistics about filter configuration."""
        return {
            "large_cap_exclusions": len(self.large_cap_blacklist),
            "midcap_whitelist_size": len(self.midcap_whitelist),
            "manual_blacklist_size": len(self.manual_blacklist),
            "suggested_universe_size": len(self.get_suggested_midcap_universe())
        }


if __name__ == "__main__":
    # Test the midcap filter
    print("Midcap Filter System Test")
    print("=" * 50)
    
    filter_sys = MidcapFilter()
    
    # Test some tickers
    test_tickers = ['AAPL', 'MSFT', 'TEAM', 'SNOW', 'CRWD', 'SPY', 'QQQ', 'MRNA', 'ZM']
    
    print("Testing ticker filtering:")
    for ticker in test_tickers:
        is_midcap = filter_sys.is_midcap_candidate(ticker)
        print(f"  {ticker}: {'✓ Midcap candidate' if is_midcap else '✗ Excluded'}")
    
    print(f"\nFilter statistics:")
    stats = filter_sys.get_filter_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print(f"\nSample midcap universe (first 10):")
    universe = filter_sys.get_suggested_midcap_universe()
    for ticker in universe[:10]:
        print(f"  {ticker}")
    
    print(f"\nTotal suggested midcap universe size: {len(universe)}")