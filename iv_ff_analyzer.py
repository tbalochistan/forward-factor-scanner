"""
IV Analysis and Forward Factor Integration

This module integrates implied volatility analysis with Forward Factor calculations
for the options trading strategy. It processes option chains to extract IV data
and calculates Forward Factor opportunities.
"""

from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import statistics
import logging
import math

from options_scanner import OptionChain, OptionData, SchwabOptionsScanner
from liquidity_filter import LiquidityFilter, LiquidityScore, LiquidityThresholds
from iv_calculator import ImpliedVolatilityCalculator


@dataclass
class ForwardFactorResult:
    """Result of Forward Factor calculation"""
    forward_factor: float
    forward_factor_percent: float
    near_term_dte: int
    next_term_dte: int
    near_term_iv: float
    next_term_iv: float
    is_valid: bool
    error_message: Optional[str] = None


def calculate_forward_factor(dte1: int, iv1: float, dte2: int, iv2: float) -> ForwardFactorResult:
    """
    Calculate Forward Factor between two option terms using proper variance-weighted method
    
    Steps:
    1. Convert IV to variance: V1 = σ1², V2 = σ2²
    2. Calculate time fractions: T1 = DTE1/365, T2 = DTE2/365
    3. Calculate forward variance: Vf = (V2×T2 - V1×T1) / (T2 - T1)
    4. Calculate forward volatility: σf = √Vf
    5. Calculate Forward Factor: FF = (σ1 - σf) / σf
    
    Args:
        dte1: Days to expiration for near term
        iv1: Implied volatility for near term (as decimal, e.g., 0.25 for 25%)
        dte2: Days to expiration for next term
        iv2: Implied volatility for next term (as decimal, e.g., 0.20 for 20%)
    
    Returns:
        ForwardFactorResult with calculation details
    """
    # Validation
    if dte1 >= dte2:
        return ForwardFactorResult(
            forward_factor=0.0,
            forward_factor_percent=0.0,
            near_term_dte=dte1,
            next_term_dte=dte2,
            near_term_iv=iv1,
            next_term_iv=iv2,
            is_valid=False,
            error_message=f"Near term DTE ({dte1}) must be less than next term DTE ({dte2})"
        )
    
    if iv1 <= 0 or iv2 <= 0:
        return ForwardFactorResult(
            forward_factor=0.0,
            forward_factor_percent=0.0,
            near_term_dte=dte1,
            next_term_dte=dte2,
            near_term_iv=iv1,
            next_term_iv=iv2,
            is_valid=False,
            error_message=f"Invalid IV values: near={iv1:.4f}, next={iv2:.4f}"
        )
    
    if not all(math.isfinite(x) for x in [iv1, iv2]):
        return ForwardFactorResult(
            forward_factor=0.0,
            forward_factor_percent=0.0,
            near_term_dte=dte1,
            next_term_dte=dte2,
            near_term_iv=iv1,
            next_term_iv=iv2,
            is_valid=False,
            error_message="Invalid IV values (not finite numbers)"
        )

    # Detect if percentage values were passed instead of decimals
    # Valid IV decimals are typically 0.01 to 3.0 (1% to 300%)
    # Values > 3.0 are almost certainly percentages (e.g., 25.0 instead of 0.25)
    if iv1 > 3.0 or iv2 > 3.0:
        return ForwardFactorResult(
            forward_factor=0.0,
            forward_factor_percent=0.0,
            near_term_dte=dte1,
            next_term_dte=dte2,
            near_term_iv=iv1,
            next_term_iv=iv2,
            is_valid=False,
            error_message=f"IV values appear to be percentages instead of decimals (iv1={iv1:.2f}, iv2={iv2:.2f}). "
                         f"Expected decimal format (e.g., 0.25 for 25%). Convert by dividing by 100."
        )

    # Step 1: Convert IV to variance
    v1 = iv1 * iv1  # V1 = σ1²
    v2 = iv2 * iv2  # V2 = σ2²
    
    # Step 2: Calculate time fractions
    t1 = dte1 / 365.0  # T1 = DTE1/365
    t2 = dte2 / 365.0  # T2 = DTE2/365
    
    # Step 3: Calculate forward variance
    # Vf = (V2×T2 - V1×T1) / (T2 - T1)
    time_diff = t2 - t1
    if time_diff <= 0:
        return ForwardFactorResult(
            forward_factor=0.0,
            forward_factor_percent=0.0,
            near_term_dte=dte1,
            next_term_dte=dte2,
            near_term_iv=iv1,
            next_term_iv=iv2,
            is_valid=False,
            error_message="Time difference must be positive"
        )
    
    forward_variance = (v2 * t2 - v1 * t1) / time_diff
    
    # Step 4: Calculate forward volatility
    if forward_variance <= 0:
        return ForwardFactorResult(
            forward_factor=0.0,
            forward_factor_percent=0.0,
            near_term_dte=dte1,
            next_term_dte=dte2,
            near_term_iv=iv1,
            next_term_iv=iv2,
            is_valid=False,
            error_message=f"Forward variance is negative or zero: {forward_variance:.6f}"
        )
    
    forward_volatility = math.sqrt(forward_variance)  # σf = √Vf
    
    # Step 5: Calculate Forward Factor with zero-division protection
    if forward_volatility == 0:
        return ForwardFactorResult(
            forward_factor=0.0,
            forward_factor_percent=0.0,
            near_term_dte=dte1,
            next_term_dte=dte2,
            near_term_iv=iv1,
            next_term_iv=iv2,
            is_valid=False,
            error_message="Forward volatility is zero - cannot calculate Forward Factor"
        )
    
    # FF = (σ1 - σf) / σf
    forward_factor = (iv1 - forward_volatility) / forward_volatility
    forward_factor_percent = forward_factor * 100
    
    return ForwardFactorResult(
        forward_factor=forward_factor,
        forward_factor_percent=forward_factor_percent,
        near_term_dte=dte1,
        next_term_dte=dte2,
        near_term_iv=iv1,
        next_term_iv=iv2,
        is_valid=True
    )


@dataclass
class IVAnalysis:
    """Implied volatility analysis for an option chain"""
    ticker: str
    expiration: str
    days_to_expiration: int
    atm_iv: Optional[float]  # ATM implied volatility
    iv_skew: Optional[float]  # Put-call IV skew
    iv_smile_slope: Optional[float]  # IV smile slope
    avg_call_iv: Optional[float]
    avg_put_iv: Optional[float]
    liquid_options_count: int


@dataclass
class ForwardFactorOpportunity:
    """Complete Forward Factor opportunity analysis"""
    ticker: str
    underlying_price: float
    
    # Option chain info
    near_term_chain: OptionChain
    next_term_chain: OptionChain
    
    # IV analysis
    near_term_iv: IVAnalysis
    next_term_iv: IVAnalysis
    
    # Forward Factor calculation
    ff_result: ForwardFactorResult
    
    # Liquidity scores
    near_term_liquidity: Dict[str, LiquidityScore]
    next_term_liquidity: Dict[str, LiquidityScore]
    
    # Strategy signals
    is_valid_opportunity: bool
    opportunity_type: str  # 'bullish', 'bearish', 'neutral'
    confidence_score: float  # 0-100
    reasons: List[str]


class IVForwardFactorAnalyzer:
    """
    Analyzer that combines IV analysis with Forward Factor calculations.
    
    This class processes option chains to extract implied volatility data
    and calculates Forward Factor opportunities for trading strategies.
    """
    
    def __init__(self, liquidity_filter: Optional[LiquidityFilter] = None):
        """
        Initialize the analyzer.
        
        Args:
            liquidity_filter: LiquidityFilter instance. Uses default if None.
        """
        self.liquidity_filter = liquidity_filter or LiquidityFilter()
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
    
    def analyze_chain_iv(self, chain: OptionChain) -> IVAnalysis:
        """
        Analyze implied volatility characteristics of an option chain.
        
        Args:
            chain: OptionChain to analyze
            
        Returns:
            IVAnalysis with IV metrics
        """
        try:
            if not chain or not chain.strikes:
                return IVAnalysis(
                    ticker=chain.ticker if chain else "",
                    expiration=chain.expiration_date if chain else "",
                    days_to_expiration=chain.days_to_expiration if chain else 0,
                    atm_iv=None, iv_skew=None, iv_smile_slope=None,
                    avg_call_iv=None, avg_put_iv=None, liquid_options_count=0
                )
            
            # Get liquid options with ATM focus for better coverage on smaller cap stocks
            liquid_options = self.liquidity_filter.filter_chain_for_atm_liquidity(chain)
            
            # If ATM-focused filter doesn't yield results, fall back to regular filter
            if not liquid_options:
                liquid_options = self.liquidity_filter.filter_chain_for_liquidity(chain)
            
            if not liquid_options:
                return IVAnalysis(
                    ticker=chain.ticker,
                    expiration=chain.expiration_date,
                    days_to_expiration=chain.days_to_expiration,
                    atm_iv=None, iv_skew=None, iv_smile_slope=None,
                    avg_call_iv=None, avg_put_iv=None, liquid_options_count=0
                )
            
            if not liquid_options:
                return IVAnalysis(
                    ticker=chain.ticker,
                    expiration=chain.expiration_date,
                    days_to_expiration=chain.days_to_expiration,
                    atm_iv=None, iv_skew=None, iv_smile_slope=None,
                    avg_call_iv=None, avg_put_iv=None, liquid_options_count=0
                )
            
            # Extract IVs by option type
            call_ivs = []
            put_ivs = []
            underlying = chain.underlying_price
            
            # Find ATM options
            atm_call = None
            atm_put = None
            atm_call_iv = None
            atm_put_iv = None
            min_call_diff = float('inf')
            min_put_diff = float('inf')
            
            for score in liquid_options.values():
                option = score.option
                
                # Calculate proper IV using py_vollib instead of using Schwab's IV
                mid_price = ImpliedVolatilityCalculator.get_option_mid_price(
                    option.bid, option.ask, option.last
                )
                
                if mid_price and mid_price > 0:
                    time_to_expiry = ImpliedVolatilityCalculator.days_to_years(chain.days_to_expiration)
                    option_type = 'c' if option.option_type == 'CALL' else 'p'
                    
                    # Calculate real IV using py_vollib Black-Scholes with error handling
                    try:
                        real_iv = ImpliedVolatilityCalculator.calculate_iv(
                            option_price=mid_price,
                            underlying_price=underlying,
                            strike_price=option.strike,
                            time_to_expiry=time_to_expiry,
                            option_type=option_type
                        )
                    except (ZeroDivisionError, ValueError, OverflowError) as e:
                        # Skip this option if IV calculation fails
                        continue
                    
                    if real_iv and 0.01 <= real_iv <= 3.0:  # Valid IV between 1% and 300%
                        real_iv_pct = real_iv * 100  # Convert to percentage
                        
                        if option.option_type == 'CALL':
                            call_ivs.append(real_iv_pct)
                            strike_diff = abs(option.strike - underlying)
                            if strike_diff < min_call_diff:
                                min_call_diff = strike_diff
                                atm_call = option
                                atm_call_iv = real_iv  # Store the calculated IV
                        
                        elif option.option_type == 'PUT':
                            put_ivs.append(real_iv_pct)
                            strike_diff = abs(option.strike - underlying)
                            if strike_diff < min_put_diff:
                                min_put_diff = strike_diff
                                atm_put = option
                                atm_put_iv = real_iv  # Store the calculated IV
            
            # Calculate metrics with safety checks
            atm_iv = None
            if atm_call_iv and atm_put_iv and atm_call_iv > 0 and atm_put_iv > 0:
                # Use average of ATM call and put IVs (already in decimal, convert to %)
                atm_iv = (atm_call_iv + atm_put_iv) / 2 * 100
            elif atm_call_iv and atm_call_iv > 0:
                atm_iv = atm_call_iv * 100
            elif atm_put_iv and atm_put_iv > 0:
                atm_iv = atm_put_iv * 100
            
            # IV skew (put IV - call IV for ATM) 
            iv_skew = None
            if atm_call_iv and atm_put_iv and atm_call_iv > 0 and atm_put_iv > 0:
                iv_skew = (atm_put_iv - atm_call_iv) * 100
            
            # Average IVs with safety checks
            avg_call_iv = statistics.mean(call_ivs) if call_ivs and len(call_ivs) > 0 else None
            avg_put_iv = statistics.mean(put_ivs) if put_ivs and len(put_ivs) > 0 else None
            
            # IV smile slope (simplified - just range)
            iv_smile_slope = None
            if call_ivs and len(call_ivs) > 1:
                iv_smile_slope = max(call_ivs) - min(call_ivs)
            
            return IVAnalysis(
                ticker=chain.ticker,
                expiration=chain.expiration_date,
                days_to_expiration=chain.days_to_expiration,
                atm_iv=atm_iv,
                iv_skew=iv_skew,
                iv_smile_slope=iv_smile_slope,
                avg_call_iv=avg_call_iv,
                avg_put_iv=avg_put_iv,
                liquid_options_count=len(liquid_options)
            )
            
        except Exception as e:
            self.logger.error(f"Error in analyze_chain_iv for {chain.ticker if chain else 'unknown'}: {e}")
            return IVAnalysis(
                ticker=chain.ticker if chain else "",
                expiration=chain.expiration_date if chain else "",
                days_to_expiration=chain.days_to_expiration if chain else 0,
                atm_iv=None, iv_skew=None, iv_smile_slope=None,
                avg_call_iv=None, avg_put_iv=None, liquid_options_count=0
            )
    
    def calculate_forward_factor_opportunity(
        self, 
        near_chain: OptionChain, 
        next_chain: OptionChain
    ) -> Optional[ForwardFactorOpportunity]:
        """
        Calculate Forward Factor opportunity from two option chains.
        
        Args:
            near_chain: Near-term option chain
            next_chain: Next-term option chain
            
        Returns:
            ForwardFactorOpportunity if valid, None otherwise
        """
        if not near_chain or not next_chain:
            return None
        
        # Analyze IV for both chains
        near_iv = self.analyze_chain_iv(near_chain)
        next_iv = self.analyze_chain_iv(next_chain)
        
        # Get liquidity scores with ATM focus for smaller cap stocks
        near_liquidity = self.liquidity_filter.filter_chain_for_atm_liquidity(near_chain)
        next_liquidity = self.liquidity_filter.filter_chain_for_atm_liquidity(next_chain)
        
        # Fall back to regular filter if ATM-focused doesn't work
        if not near_liquidity:
            near_liquidity = self.liquidity_filter.filter_chain_for_liquidity(near_chain)
        if not next_liquidity:
            next_liquidity = self.liquidity_filter.filter_chain_for_liquidity(next_chain)
        
        # Validation checks
        reasons = []
        is_valid = True
        
        if near_iv.atm_iv is None:
            is_valid = False
            reasons.append("No liquid ATM options in near-term chain")
        
        if next_iv.atm_iv is None:
            is_valid = False
            reasons.append("No liquid ATM options in next-term chain")
        
        if near_iv.liquid_options_count < 5:
            is_valid = False
            reasons.append(f"Insufficient liquid near-term options: {near_iv.liquid_options_count}")
        
        if next_iv.liquid_options_count < 5:
            is_valid = False
            reasons.append(f"Insufficient liquid next-term options: {next_iv.liquid_options_count}")
        
        # Calculate Forward Factor if we have valid IV data
        ff_result = None
        if near_iv.atm_iv is not None and next_iv.atm_iv is not None:
            ff_result = calculate_forward_factor(
                dte1=near_chain.days_to_expiration,
                iv1=near_iv.atm_iv / 100,  # Convert percentage to decimal (stored as 25.0, need 0.25)
                dte2=next_chain.days_to_expiration,
                iv2=next_iv.atm_iv / 100   # Convert percentage to decimal (stored as 25.0, need 0.25)
            )
            
            if not ff_result.is_valid:
                is_valid = False
                reasons.append(f"Invalid Forward Factor calculation: {ff_result.error_message}")
        else:
            is_valid = False
            reasons.append("Cannot calculate Forward Factor without valid IV data")
        
        # Determine opportunity type and confidence
        opportunity_type = 'neutral'
        confidence_score = 0.0
        
        if ff_result and ff_result.is_valid and ff_result.forward_factor_percent is not None:
            ff_pct = ff_result.forward_factor_percent
            
            # Classify opportunity
            if ff_pct > 5.0:
                opportunity_type = 'bullish'
                confidence_score = min(100, abs(ff_pct) * 5)  # Scale confidence
                reasons.append(f"Bullish signal: FF = {ff_pct:.1f}% (front month elevated)")
            elif ff_pct < -5.0:
                opportunity_type = 'bearish'
                confidence_score = min(100, abs(ff_pct) * 5)
                reasons.append(f"Bearish signal: FF = {ff_pct:.1f}% (front month depressed)")
            else:
                opportunity_type = 'neutral'
                confidence_score = 20.0  # Low confidence for neutral
                reasons.append(f"Neutral: FF = {ff_pct:.1f}% (within normal range)")
            
            # Adjust confidence based on liquidity
            liquidity_adjustment = min(
                near_iv.liquid_options_count / 20.0,  # More liquid = higher confidence
                next_iv.liquid_options_count / 20.0
            )
            confidence_score *= liquidity_adjustment
        
        if not reasons:
            reasons.append("Analysis completed successfully")
        
        return ForwardFactorOpportunity(
            ticker=near_chain.ticker,
            underlying_price=near_chain.underlying_price,
            near_term_chain=near_chain,
            next_term_chain=next_chain,
            near_term_iv=near_iv,
            next_term_iv=next_iv,
            ff_result=ff_result,
            near_term_liquidity=near_liquidity,
            next_term_liquidity=next_liquidity,
            is_valid_opportunity=is_valid,
            opportunity_type=opportunity_type,
            confidence_score=confidence_score,
            reasons=reasons
        )
    
    def scan_ticker_for_opportunities(
        self, 
        ticker: str, 
        scanner: SchwabOptionsScanner
    ) -> Optional[ForwardFactorOpportunity]:
        """
        Scan a single ticker for Forward Factor opportunities.
        
        Args:
            ticker: Stock symbol to scan
            scanner: Authenticated SchwabOptionsScanner
            
        Returns:
            ForwardFactorOpportunity if found, None otherwise
        """
        try:
            near_chain, next_chain = scanner.get_near_and_next_term_chains(ticker)
            
            if not near_chain or not next_chain:
                self.logger.warning(f"{ticker}: No valid option chains found")
                return None
            
            opportunity = self.calculate_forward_factor_opportunity(near_chain, next_chain)
            
            if opportunity and opportunity.is_valid_opportunity:
                self.logger.info(
                    f"{ticker}: Found {opportunity.opportunity_type} opportunity "
                    f"(FF: {opportunity.ff_result.forward_factor_percent:.1f}%, "
                    f"Confidence: {opportunity.confidence_score:.1f})"
                )
            else:
                self.logger.debug(f"{ticker}: No valid opportunity found")
            
            return opportunity
            
        except Exception as e:
            self.logger.error(f"Error scanning {ticker}: {e}")
            return None
    
    def scan_multiple_tickers(
        self, 
        tickers: List[str], 
        scanner: SchwabOptionsScanner,
        min_confidence: float = 30.0
    ) -> List[ForwardFactorOpportunity]:
        """
        Scan multiple tickers for Forward Factor opportunities.
        
        Args:
            tickers: List of stock symbols
            scanner: Authenticated SchwabOptionsScanner
            min_confidence: Minimum confidence score to include
            
        Returns:
            List of valid opportunities sorted by confidence
        """
        opportunities = []
        
        for ticker in tickers:
            opportunity = self.scan_ticker_for_opportunities(ticker, scanner)
            
            if (opportunity and 
                opportunity.is_valid_opportunity and 
                opportunity.confidence_score >= min_confidence):
                opportunities.append(opportunity)
        
        # Sort by confidence score (highest first)
        opportunities.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return opportunities
    
    def get_opportunity_summary(self, opportunity: ForwardFactorOpportunity) -> Dict[str, Any]:
        """Get summary of a Forward Factor opportunity."""
        if not opportunity.ff_result:
            return {'error': 'No Forward Factor result available'}
        
        return {
            'ticker': opportunity.ticker,
            'underlying_price': opportunity.underlying_price,
            'opportunity_type': opportunity.opportunity_type,
            'confidence_score': opportunity.confidence_score,
            'forward_factor_pct': opportunity.ff_result.forward_factor_percent,
            'forward_volatility_pct': getattr(opportunity.ff_result, 'forward_volatility', 0) * 100 if hasattr(opportunity.ff_result, 'forward_volatility') else None,
            'near_term_dte': opportunity.near_term_chain.days_to_expiration,
            'next_term_dte': opportunity.next_term_chain.days_to_expiration,
            'near_term_iv': opportunity.near_term_iv.atm_iv,
            'next_term_iv': opportunity.next_term_iv.atm_iv,
            'near_term_liquidity_count': opportunity.near_term_iv.liquid_options_count,
            'next_term_liquidity_count': opportunity.next_term_iv.liquid_options_count,
            'primary_reason': opportunity.reasons[0] if opportunity.reasons else "No reason provided"
        }


if __name__ == "__main__":
    # Test IV analysis and Forward Factor integration
    print("IV Analysis and Forward Factor Integration Test")
    print("=" * 60)
    
    # Create test data
    from options_scanner import OptionChain, OptionData
    from datetime import date, timedelta
    
    # Mock option data for testing
    near_exp = (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
    next_exp = (date.today() + timedelta(days=60)).strftime('%Y-%m-%d')
    
    # Create sample option chains
    near_strikes = {}
    next_strikes = {}
    
    # Add some sample options around $100 underlying
    for strike in [95, 100, 105]:
        # Near term - higher IV (25%)
        near_strikes[f"{strike}_CALL"] = OptionData(
            ticker='TEST', expiration=near_exp, strike=float(strike), option_type='CALL',
            bid=2.50, ask=2.70, last=2.60, volume=150, open_interest=500,
            implied_volatility=0.25
        )
        near_strikes[f"{strike}_PUT"] = OptionData(
            ticker='TEST', expiration=near_exp, strike=float(strike), option_type='PUT',
            bid=2.30, ask=2.50, last=2.40, volume=120, open_interest=400,
            implied_volatility=0.27  # Put skew
        )
        
        # Next term - lower IV (22%)
        next_strikes[f"{strike}_CALL"] = OptionData(
            ticker='TEST', expiration=next_exp, strike=float(strike), option_type='CALL',
            bid=3.20, ask=3.40, last=3.30, volume=100, open_interest=300,
            implied_volatility=0.22
        )
        next_strikes[f"{strike}_PUT"] = OptionData(
            ticker='TEST', expiration=next_exp, strike=float(strike), option_type='PUT',
            bid=3.00, ask=3.20, last=3.10, volume=80, open_interest=250,
            implied_volatility=0.24
        )
    
    near_chain = OptionChain(
        ticker='TEST', expiration_date=near_exp, days_to_expiration=30,
        strikes=near_strikes, underlying_price=100.0
    )
    
    next_chain = OptionChain(
        ticker='TEST', expiration_date=next_exp, days_to_expiration=60,
        strikes=next_strikes, underlying_price=100.0
    )
    
    # Test the analyzer
    analyzer = IVForwardFactorAnalyzer()
    
    print("Testing IV analysis:")
    near_iv = analyzer.analyze_chain_iv(near_chain)
    next_iv = analyzer.analyze_chain_iv(next_chain)
    
    print(f"  Near term ({near_iv.days_to_expiration} DTE):")
    print(f"    ATM IV: {near_iv.atm_iv:.1f}%")
    print(f"    IV Skew: {near_iv.iv_skew:.1f}%")
    print(f"    Liquid options: {near_iv.liquid_options_count}")
    
    print(f"  Next term ({next_iv.days_to_expiration} DTE):")
    print(f"    ATM IV: {next_iv.atm_iv:.1f}%")
    print(f"    IV Skew: {next_iv.iv_skew:.1f}%")
    print(f"    Liquid options: {next_iv.liquid_options_count}")
    
    print(f"\nTesting Forward Factor opportunity:")
    opportunity = analyzer.calculate_forward_factor_opportunity(near_chain, next_chain)
    
    if opportunity:
        summary = analyzer.get_opportunity_summary(opportunity)
        print(f"  Opportunity type: {summary['opportunity_type']}")
        print(f"  Forward Factor: {summary['forward_factor_pct']:.1f}%")
        print(f"  Confidence: {summary['confidence_score']:.1f}")
        print(f"  Reason: {summary['primary_reason']}")
    else:
        print("  No opportunity found")