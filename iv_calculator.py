"""
Proper implied volatility calculator using py_vollib Black-Scholes model
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from py_vollib.black_scholes.implied_volatility import implied_volatility
from py_vollib.black_scholes import black_scholes
import numpy as np
from typing import Optional
import math

class ImpliedVolatilityCalculator:
    """
    Calculate real implied volatilities from option prices using Black-Scholes
    """
    
    @staticmethod
    def calculate_iv(
        option_price: float,
        underlying_price: float, 
        strike_price: float,
        time_to_expiry: float,  # in years
        risk_free_rate: float = 0.05,  # 5% default
        option_type: str = 'c'  # 'c' for call, 'p' for put
    ) -> Optional[float]:
        """
        Calculate implied volatility from option price
        
        Args:
            option_price: Current option price (mid or last)
            underlying_price: Current stock price
            strike_price: Option strike price
            time_to_expiry: Time to expiration in years
            risk_free_rate: Risk-free interest rate (default 5%)
            option_type: 'c' for call, 'p' for put
            
        Returns:
            Implied volatility as decimal (e.g., 0.25 for 25%) or None if calculation fails
        """
        try:
            # Validate inputs
            if (option_price <= 0 or underlying_price <= 0 or 
                strike_price <= 0 or time_to_expiry <= 0):
                return None
            
            # For deep ITM options, check if price makes sense
            if option_type.lower() == 'c':
                intrinsic = max(0, underlying_price - strike_price)
            else:
                intrinsic = max(0, strike_price - underlying_price)
            
            # Option price must be at least intrinsic value
            if option_price < intrinsic:
                return None
            
            # Use py_vollib to calculate IV
            iv = implied_volatility(
                price=option_price,
                S=underlying_price,
                K=strike_price, 
                t=time_to_expiry,
                r=risk_free_rate,
                flag=option_type.lower()
            )
            
            # Sanity check - IV should be between 0% and 300%
            if 0.01 <= iv <= 3.0:  # 1% to 300%
                return iv
            else:
                return None
                
        except (ZeroDivisionError, ValueError, OverflowError, Exception) as e:
            # IV calculation can fail for various reasons including division by zero
            return None
    
    @staticmethod
    def get_option_mid_price(bid: float, ask: float, last: float) -> Optional[float]:
        """
        Get best estimate of option's current price
        
        Args:
            bid: Bid price
            ask: Ask price  
            last: Last traded price
            
        Returns:
            Best price estimate or None
        """
        # Prefer mid price if bid/ask are valid
        if bid > 0 and ask > 0 and ask > bid:
            return (bid + ask) / 2.0
        
        # Fall back to last price if it's reasonable
        if last > 0:
            return last
            
        return None
    
    @staticmethod
    def days_to_years(days: int) -> float:
        """Convert days to expiration to years"""
        return days / 365.0

# Test the IV calculator
def test_iv_calculator():
    """Test the IV calculator with TEAM data"""
    try:
        from options_scanner import SchwabOptionsScanner
        
        print("=== Testing Real IV Calculator ===")
        
        scanner = SchwabOptionsScanner()
        
        # Authenticate first
        if not scanner.is_authenticated():
            scanner.authenticate()
        
        near_chain, next_chain = scanner.get_near_and_next_term_chains("TEAM")
        
        calc = ImpliedVolatilityCalculator()
        underlying = near_chain.underlying_price
        
        print(f"Underlying: ${underlying:.2f}")
        print(f"Near-term: {near_chain.days_to_expiration} DTE")
        print(f"Next-term: {next_chain.days_to_expiration} DTE")
        
        # Test near-term ATM calls
        print(f"\n=== Near-term ATM Call IVs ===")
        near_ivs = []
        for key, option in near_chain.strikes.items():
            if (option.option_type == 'CALL' and 
                abs(option.strike - underlying) < 5.0):
                
                mid_price = calc.get_option_mid_price(option.bid, option.ask, option.last)
                if mid_price:
                    time_to_expiry = calc.days_to_years(near_chain.days_to_expiration)
                    
                    real_iv = calc.calculate_iv(
                        mid_price, underlying, option.strike, 
                        time_to_expiry, option_type='c'
                    )
                    
                    if real_iv:
                        near_ivs.append(real_iv)
                        print(f"  ${option.strike}: Price=${mid_price:.2f}, "
                              f"Schwab={option.implied_volatility*100:.1f}%, "
                              f"Real_IV={real_iv*100:.1f}%")
        
        # Test next-term ATM calls  
        print(f"\n=== Next-term ATM Call IVs ===")
        next_ivs = []
        for key, option in next_chain.strikes.items():
            if (option.option_type == 'CALL' and 
                abs(option.strike - underlying) < 5.0):
                
                mid_price = calc.get_option_mid_price(option.bid, option.ask, option.last)
                if mid_price:
                    time_to_expiry = calc.days_to_years(next_chain.days_to_expiration)
                    
                    real_iv = calc.calculate_iv(
                        mid_price, underlying, option.strike,
                        time_to_expiry, option_type='c'
                    )
                    
                    if real_iv:
                        next_ivs.append(real_iv)
                        print(f"  ${option.strike}: Price=${mid_price:.2f}, "
                              f"Schwab={option.implied_volatility*100:.1f}%, "
                              f"Real_IV={real_iv*100:.1f}%")
        
        # Compare ATM IVs
        if near_ivs and next_ivs:
            near_atm_iv = np.mean(near_ivs) * 100
            next_atm_iv = np.mean(next_ivs) * 100
            
            print(f"\n=== ATM IV Comparison ===")
            print(f"Near-term ATM IV: {near_atm_iv:.1f}%")
            print(f"Next-term ATM IV: {next_atm_iv:.1f}%")
            print(f"Difference: {next_atm_iv - near_atm_iv:.1f}%")
            
            if abs(next_atm_iv - near_atm_iv) > 1.0:
                print("✅ Real IV term structure detected!")
            else:
                print("⚠️ IVs still very similar")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_iv_calculator()