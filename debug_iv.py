"""
Debug script to investigate IV calculation issues
"""
from options_scanner import SchwabOptionsScanner
from iv_calculator import ImpliedVolatilityCalculator

def debug_iv_calculation():
    scanner = SchwabOptionsScanner()
    scanner.authenticate()
    
    # Get SPY options data
    raw_data = scanner.get_option_chain("SPY", expiration_count=3)
    chains = scanner.parse_option_chain(raw_data, "SPY")
    
    if chains:
        # Find a chain with reasonable DTE (not expiring today)
        chain = None
        for c in chains:
            if c.days_to_expiration >= 7:  # At least a week
                chain = c
                break
        
        if not chain:
            print("No valid chains found!")
            return
            
        print(f"=== Debugging SPY Chain ===")
        print(f"Underlying: ${chain.underlying_price:.2f}")
        print(f"Days to expiry: {chain.days_to_expiration}")
        print(f"Time to expiry (years): {chain.days_to_expiration / 365:.4f}")
        print()
        
        calc = ImpliedVolatilityCalculator()
        
        # Look at first few ATM options
        atm_strike = round(chain.underlying_price / 5) * 5  # Round to nearest $5
        print(f"Looking for options near ATM strike: ${atm_strike}")
        print()
        
        count = 0
        for key, option in chain.strikes.items():
            if abs(option.strike - atm_strike) <= 10 and count < 5:
                print(f"=== {option.option_type} ${option.strike} ===")
                print(f"Bid/Ask/Last: ${option.bid:.2f}/${option.ask:.2f}/${option.last:.2f}")
                print(f"Schwab IV: {option.implied_volatility:.4f} ({option.implied_volatility*100:.1f}%)")
                
                # Get mid price
                mid_price = calc.get_option_mid_price(option.bid, option.ask, option.last)
                print(f"Mid price: ${mid_price:.2f}")
                
                if mid_price and mid_price > 0:
                    # Calculate IV using py_vollib
                    time_to_expiry = calc.days_to_years(chain.days_to_expiration)
                    option_type = 'c' if option.option_type == 'CALL' else 'p'
                    
                    real_iv = calc.calculate_iv(
                        option_price=mid_price,
                        underlying_price=chain.underlying_price,
                        strike_price=option.strike,
                        time_to_expiry=time_to_expiry,
                        option_type=option_type
                    )
                    
                    if real_iv:
                        print(f"py_vollib IV: {real_iv:.4f} ({real_iv*100:.1f}%)")
                        print(f"Difference: {abs(option.implied_volatility - real_iv)*100:.1f} percentage points")
                    else:
                        print("py_vollib IV: FAILED")
                else:
                    print("Mid price: INVALID")
                
                print()
                count += 1

if __name__ == "__main__":
    debug_iv_calculation()