"""
Liquidity filtering system for options trading.

This module provides filters to identify liquid options suitable for trading
based on volume, open interest, bid-ask spreads, and other liquidity metrics.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from options_scanner import OptionData, OptionChain


@dataclass
class LiquidityThresholds:
    """Configuration for liquidity filtering thresholds"""
    min_volume: int = 50
    min_open_interest: int = 100
    max_bid_ask_spread_pct: float = 10.0  # Maximum spread as % of mid price
    min_bid: float = 0.05  # Minimum bid price to avoid penny options
    min_ask: float = 0.10  # Minimum ask price
    max_bid_ask_spread_abs: float = 2.0  # Maximum absolute spread in dollars
    min_mid_price: float = 0.10  # Minimum mid price
    
    # Advanced filters
    min_volume_oi_ratio: float = 0.1  # Minimum volume/OI ratio for recent activity
    max_days_to_expiration: int = 90  # Maximum DTE to avoid illiquid far-dated options
    min_days_to_expiration: int = 7   # Minimum DTE to avoid gamma risk


@dataclass
class LiquidityScore:
    """Liquidity scoring for an option"""
    option: OptionData
    volume_score: float
    open_interest_score: float
    spread_score: float
    overall_score: float
    is_liquid: bool
    reasons: List[str]


class LiquidityFilter:
    """
    Options liquidity filtering and scoring system.
    
    Evaluates options based on multiple liquidity metrics and provides
    scoring to rank options by tradability.
    """
    
    def __init__(self, thresholds: Optional[LiquidityThresholds] = None):
        """
        Initialize liquidity filter.
        
        Args:
            thresholds: Custom liquidity thresholds. Uses defaults if None.
        """
        self.thresholds = thresholds or LiquidityThresholds()
    
    def calculate_bid_ask_spread_pct(self, option: OptionData) -> float:
        """Calculate bid-ask spread as percentage of mid price."""
        if option.bid <= 0 or option.ask <= 0:
            return float('inf')
        
        mid_price = (option.bid + option.ask) / 2
        if mid_price <= 0:
            return float('inf')
        
        spread = option.ask - option.bid
        return (spread / mid_price) * 100
    
    def calculate_mid_price(self, option: OptionData) -> float:
        """Calculate mid price between bid and ask."""
        if option.bid <= 0 or option.ask <= 0:
            return 0.0
        return (option.bid + option.ask) / 2
    
    def calculate_volume_oi_ratio(self, option: OptionData) -> float:
        """Calculate volume to open interest ratio."""
        if option.open_interest <= 0:
            return 0.0
        return option.volume / option.open_interest
    
    def evaluate_option_liquidity(self, option: OptionData) -> LiquidityScore:
        """
        Evaluate liquidity for a single option.
        
        Args:
            option: OptionData to evaluate
            
        Returns:
            LiquidityScore with detailed evaluation
        """
        reasons = []
        is_liquid = True
        
        # Basic price validation
        mid_price = self.calculate_mid_price(option)
        spread_pct = self.calculate_bid_ask_spread_pct(option)
        spread_abs = option.ask - option.bid if option.ask > option.bid else float('inf')
        volume_oi_ratio = self.calculate_volume_oi_ratio(option)
        
        # Volume scoring (0-100)
        volume_score = min(100, (option.volume / self.thresholds.min_volume) * 25)
        if option.volume < self.thresholds.min_volume:
            is_liquid = False
            reasons.append(f"Low volume: {option.volume} < {self.thresholds.min_volume}")
        
        # Open interest scoring (0-100)
        oi_score = min(100, (option.open_interest / self.thresholds.min_open_interest) * 25)
        if option.open_interest < self.thresholds.min_open_interest:
            is_liquid = False
            reasons.append(f"Low OI: {option.open_interest} < {self.thresholds.min_open_interest}")
        
        # Spread scoring (0-100, inverted - lower spread = higher score)
        if spread_pct == float('inf'):
            spread_score = 0
            is_liquid = False
            reasons.append("Invalid bid/ask prices")
        else:
            spread_score = max(0, 100 - (spread_pct * 5))  # Penalty for wide spreads
            
            if spread_pct > self.thresholds.max_bid_ask_spread_pct:
                is_liquid = False
                reasons.append(f"Wide spread: {spread_pct:.1f}% > {self.thresholds.max_bid_ask_spread_pct}%")
            
            if spread_abs > self.thresholds.max_bid_ask_spread_abs:
                is_liquid = False
                reasons.append(f"Wide spread: ${spread_abs:.2f} > ${self.thresholds.max_bid_ask_spread_abs}")
        
        # Additional filters
        if option.bid < self.thresholds.min_bid:
            is_liquid = False
            reasons.append(f"Low bid: ${option.bid:.2f} < ${self.thresholds.min_bid}")
        
        if option.ask < self.thresholds.min_ask:
            is_liquid = False
            reasons.append(f"Low ask: ${option.ask:.2f} < ${self.thresholds.min_ask}")
        
        if mid_price < self.thresholds.min_mid_price:
            is_liquid = False
            reasons.append(f"Low mid price: ${mid_price:.2f} < ${self.thresholds.min_mid_price}")
        
        if volume_oi_ratio < self.thresholds.min_volume_oi_ratio:
            is_liquid = False
            reasons.append(f"Low volume/OI ratio: {volume_oi_ratio:.2f} < {self.thresholds.min_volume_oi_ratio}")
        
        # Calculate overall score (weighted average)
        overall_score = (volume_score * 0.4 + oi_score * 0.4 + spread_score * 0.2)
        
        if not reasons:
            reasons.append("Meets all liquidity criteria")
        
        return LiquidityScore(
            option=option,
            volume_score=volume_score,
            open_interest_score=oi_score,
            spread_score=spread_score,
            overall_score=overall_score,
            is_liquid=is_liquid,
            reasons=reasons
        )
    
    def filter_chain_for_liquidity(self, chain: OptionChain) -> Dict[str, LiquidityScore]:
        """
        Filter an entire option chain for liquid options.
        
        Args:
            chain: OptionChain to filter
            
        Returns:
            Dict mapping option key -> LiquidityScore for liquid options only
        """
        liquid_options = {}
        
        # Check DTE constraints first
        if (chain.days_to_expiration < self.thresholds.min_days_to_expiration or 
            chain.days_to_expiration > self.thresholds.max_days_to_expiration):
            return liquid_options  # Return empty dict if DTE is out of range
        
        for option_key, option in chain.strikes.items():
            score = self.evaluate_option_liquidity(option)
            if score.is_liquid:
                liquid_options[option_key] = score
        
        return liquid_options
    
    def find_most_liquid_atm_options(
        self, 
        chain: OptionChain, 
        option_type: str = 'CALL'
    ) -> Optional[LiquidityScore]:
        """
        Find the most liquid at-the-money option of specified type.
        
        Args:
            chain: OptionChain to search
            option_type: 'CALL' or 'PUT'
            
        Returns:
            LiquidityScore for the most liquid ATM option, or None
        """
        liquid_options = self.filter_chain_for_liquidity(chain)
        
        # Filter by option type
        filtered_options = {
            key: score for key, score in liquid_options.items() 
            if key.endswith(f'_{option_type}')
        }
        
        if not filtered_options:
            return None
        
        # Find ATM (closest to underlying price)
        underlying = chain.underlying_price
        best_option = None
        min_distance = float('inf')
        
        for score in filtered_options.values():
            distance = abs(score.option.strike - underlying)
            if distance < min_distance:
                min_distance = distance
                best_option = score
        
        return best_option
    
    def rank_options_by_liquidity(
        self, 
        options: Dict[str, LiquidityScore]
    ) -> List[Tuple[str, LiquidityScore]]:
        """
        Rank options by liquidity score.
        
        Args:
            options: Dict of option_key -> LiquidityScore
            
        Returns:
            List of (option_key, score) tuples sorted by liquidity score (best first)
        """
        return sorted(
            options.items(), 
            key=lambda x: x[1].overall_score, 
            reverse=True
        )
    
    def get_liquidity_summary(self, chain: OptionChain) -> Dict[str, any]:
        """Get liquidity summary statistics for a chain."""
        liquid_options = self.filter_chain_for_liquidity(chain)
        
        if not liquid_options:
            return {
                'ticker': chain.ticker,
                'expiration': chain.expiration_date,
                'dte': chain.days_to_expiration,
                'total_options': len(chain.strikes),
                'liquid_options': 0,
                'liquidity_ratio': 0.0,
                'avg_liquidity_score': 0.0,
                'best_liquidity_score': 0.0
            }
        
        scores = [score.overall_score for score in liquid_options.values()]
        
        return {
            'ticker': chain.ticker,
            'expiration': chain.expiration_date,
            'dte': chain.days_to_expiration,
            'total_options': len(chain.strikes),
            'liquid_options': len(liquid_options),
            'liquidity_ratio': len(liquid_options) / len(chain.strikes) if len(chain.strikes) > 0 else 0,
            'avg_liquidity_score': sum(scores) / len(scores) if len(scores) > 0 else 0,
            'best_liquidity_score': max(scores) if scores else 0,
            'avg_volume': sum(s.option.volume for s in liquid_options.values()) / len(liquid_options) if len(liquid_options) > 0 else 0,
            'avg_open_interest': sum(s.option.open_interest for s in liquid_options.values()) / len(liquid_options) if len(liquid_options) > 0 else 0
        }
    
    def filter_chain_for_atm_liquidity(self, chain: OptionChain, min_delta: float = 35.0, max_delta: float = 50.0) -> Dict[str, LiquidityScore]:
        """
        Filter an option chain focusing on options between 35-50 delta (ATM region).
        This targets the most liquid options while staying close to ATM for reliable IV.
        
        Args:
            chain: OptionChain to filter
            min_delta: Minimum delta for inclusion (default 35.0)
            max_delta: Maximum delta for inclusion (default 50.0, which is ATM)
            
        Returns:
            Dict mapping option key -> LiquidityScore for delta-focused options
        """
        delta_focused_options = {}
        
        # Check DTE constraints first
        if (chain.days_to_expiration < self.thresholds.min_days_to_expiration or 
            chain.days_to_expiration > self.thresholds.max_days_to_expiration):
            return delta_focused_options
        
        underlying = chain.underlying_price
        
        # Target strikes that would have delta between 35-50
        # For calls: strikes slightly OTM to ATM
        # For puts: strikes slightly ITM to ATM
        target_strikes = []
        
        for option_key, option in chain.strikes.items():
            # Estimate if this option would be in our target delta range
            # For calls: delta ~50 at ATM, decreases as strike goes up
            # For puts: delta ~-50 at ATM, increases (becomes less negative) as strike goes up
            
            moneyness = option.strike / underlying  # 1.0 = ATM
            
            if option.option_type == 'CALL':
                # For calls, we want strikes from slightly OTM to ATM (delta 35-50)
                # ATM (moneyness=1.0) has ~50 delta, OTM (moneyness>1.0) has lower delta
                if 0.95 <= moneyness <= 1.05:  # ATM to slightly OTM
                    estimated_delta = max(20, 50 * (2 - moneyness))  # Rough estimate
                    if min_delta <= estimated_delta <= max_delta:
                        target_strikes.append((option_key, option, abs(50 - estimated_delta)))
            
            elif option.option_type == 'PUT':
                # For puts, we want strikes from ATM to slightly ITM (delta -35 to -50)
                # ATM (moneyness=1.0) has ~-50 delta, ITM (moneyness<1.0) has higher delta
                if 0.95 <= moneyness <= 1.05:  # Slightly ITM to ATM
                    estimated_delta = max(20, 50 * (2 - moneyness))  # Absolute value estimate
                    if min_delta <= estimated_delta <= max_delta:
                        target_strikes.append((option_key, option, abs(50 - estimated_delta)))
        
        # Sort by distance to 50 delta (ATM)
        target_strikes.sort(key=lambda x: x[2])
        
        # Evaluate options with relaxed criteria for delta-focused analysis
        for option_key, option, delta_distance in target_strikes:
            # Create a more relaxed liquidity score for delta-focused options
            score = self.evaluate_delta_option_liquidity(option, delta_distance)
            if score.is_liquid:
                delta_focused_options[option_key] = score
        
        # If we didn't find enough options in the target delta range, expand the search
        if len(delta_focused_options) < 3:  # Need at least 3 options for reliable IV
            # Expand to 25-60 delta range for more coverage
            for option_key, option in chain.strikes.items():
                if option_key in delta_focused_options:
                    continue  # Already included
                    
                moneyness = option.strike / underlying
                
                if option.option_type == 'CALL':
                    # Expand to wider range for calls (25-60 delta)
                    if 0.90 <= moneyness <= 1.15:  # Wider ATM range
                        estimated_delta = max(15, 60 * (2 - moneyness))
                        if 25 <= estimated_delta <= 60:
                            score = self.evaluate_delta_option_liquidity(option, abs(50 - estimated_delta))
                            if score.is_liquid:
                                delta_focused_options[option_key] = score
                
                elif option.option_type == 'PUT':
                    # Expand to wider range for puts (25-60 delta)
                    if 0.90 <= moneyness <= 1.15:  # Wider ATM range
                        estimated_delta = max(15, 60 * (2 - moneyness))
                        if 25 <= estimated_delta <= 60:
                            score = self.evaluate_delta_option_liquidity(option, abs(50 - estimated_delta))
                            if score.is_liquid:
                                delta_focused_options[option_key] = score
                
        return delta_focused_options
    
    def evaluate_delta_option_liquidity(self, option: OptionData, delta_distance: float) -> LiquidityScore:
        """
        Evaluate liquidity for delta-focused options (35-50 delta range) with relaxed criteria.
        
        Args:
            option: OptionData to evaluate
            delta_distance: Distance from target 50 delta (ATM)
            
        Returns:
            LiquidityScore with relaxed delta-focused evaluation
        """
        reasons = []
        is_liquid = True
        
        # Basic price validation
        mid_price = self.calculate_mid_price(option)
        spread_pct = self.calculate_bid_ask_spread_pct(option)
        spread_abs = option.ask - option.bid if option.ask > option.bid else float('inf')
        
        # Very relaxed criteria for 35-50 delta options
        relaxed_min_volume = max(1, self.thresholds.min_volume // 20)  # 20x more relaxed
        relaxed_min_oi = max(1, self.thresholds.min_open_interest // 20)  # 20x more relaxed
        relaxed_max_spread_pct = min(75.0, self.thresholds.max_bid_ask_spread_pct * 5)  # 5x more relaxed
        
        # Volume scoring with very relaxed thresholds
        volume_score = min(100, (option.volume / relaxed_min_volume) * 30)
        if option.volume < relaxed_min_volume:
            is_liquid = False
            reasons.append(f"Low volume: {option.volume} < {relaxed_min_volume}")
        
        # Open interest scoring with very relaxed thresholds
        oi_score = min(100, (option.open_interest / relaxed_min_oi) * 30)
        if option.open_interest < relaxed_min_oi:
            is_liquid = False
            reasons.append(f"Low OI: {option.open_interest} < {relaxed_min_oi}")
        
        # Spread scoring with very relaxed thresholds
        if spread_pct == float('inf'):
            spread_score = 0
            is_liquid = False
            reasons.append("Invalid bid/ask prices")
        else:
            spread_score = max(0, 100 - (spread_pct * 1.5))  # Very low penalty for spreads
            
            if spread_pct > relaxed_max_spread_pct:
                is_liquid = False
                reasons.append(f"Extremely wide spread: {spread_pct:.1f}% > {relaxed_max_spread_pct}%")
        
        # Minimal price filters - just need some pricing
        if option.bid <= 0 and option.ask <= 0:
            is_liquid = False
            reasons.append("No bid or ask price")
        
        if mid_price < 0.005:  # Very minimal mid price requirement (half a penny)
            is_liquid = False
            reasons.append(f"Extremely low mid price: ${mid_price:.4f}")
        
        # Bonus scoring for being closer to 50 delta (ATM)
        delta_bonus = max(0, 15 - delta_distance)  # Bonus for being close to ATM
        
        # Calculate overall score with delta bonus
        overall_score = (volume_score * 0.25 + oi_score * 0.25 + spread_score * 0.25 + delta_bonus * 0.25)
        
        if not reasons:
            reasons.append(f"Meets delta-focused criteria (delta ~{50-delta_distance:.0f})")
        
        return LiquidityScore(
            option=option,
            volume_score=volume_score,
            open_interest_score=oi_score,
            spread_score=spread_score,
            overall_score=overall_score,
            is_liquid=is_liquid,
            reasons=reasons
        )

    def update_thresholds(self, **kwargs):
        """Update liquidity thresholds dynamically."""
        for key, value in kwargs.items():
            if hasattr(self.thresholds, key):
                setattr(self.thresholds, key, value)


if __name__ == "__main__":
    # Test liquidity filtering
    print("Liquidity Filter Test")
    print("=" * 50)
    
    # Create sample option data for testing
    from options_scanner import OptionData
    
    # Create test options with different liquidity profiles
    test_options = [
        OptionData(
            ticker='TEST', expiration='2024-01-19', strike=100.0, option_type='CALL',
            bid=2.50, ask=2.70, last=2.60, volume=150, open_interest=500,
            implied_volatility=0.25
        ),
        OptionData(
            ticker='TEST', expiration='2024-01-19', strike=105.0, option_type='CALL',
            bid=1.80, ask=1.90, last=1.85, volume=50, open_interest=200,
            implied_volatility=0.28
        ),
        OptionData(
            ticker='TEST', expiration='2024-01-19', strike=110.0, option_type='CALL',
            bid=0.05, ask=0.15, last=0.10, volume=10, open_interest=50,
            implied_volatility=0.35
        ),
        OptionData(
            ticker='TEST', expiration='2024-01-19', strike=95.0, option_type='CALL',
            bid=5.20, ask=5.50, last=5.35, volume=300, open_interest=1000,
            implied_volatility=0.22
        )
    ]
    
    filter_sys = LiquidityFilter()
    
    print("Testing individual option liquidity:")
    for i, option in enumerate(test_options):
        score = filter_sys.evaluate_option_liquidity(option)
        print(f"\nOption {i+1}: ${option.strike} strike")
        print(f"  Bid/Ask: ${option.bid}/{option.ask}")
        print(f"  Volume: {option.volume}, OI: {option.open_interest}")
        print(f"  Liquid: {'✓' if score.is_liquid else '✗'}")
        print(f"  Score: {score.overall_score:.1f}")
        print(f"  Reasons: {', '.join(score.reasons[:2])}")  # Show first 2 reasons
    
    # Test with different thresholds
    print(f"\n\nTesting with stricter thresholds:")
    strict_filter = LiquidityFilter(LiquidityThresholds(
        min_volume=100,
        min_open_interest=300,
        max_bid_ask_spread_pct=5.0
    ))
    
    liquid_count = 0
    for option in test_options:
        score = strict_filter.evaluate_option_liquidity(option)
        if score.is_liquid:
            liquid_count += 1
    
    print(f"  Liquid options with strict thresholds: {liquid_count}/{len(test_options)}")