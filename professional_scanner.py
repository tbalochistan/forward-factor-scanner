"""
Professional Forward Factor Scanner
Uses the same timeframes as professional scanners: 30/60, 30/90, 60/90 DTE

This is your main script to run Forward Factor analysis.
"""

from forward_factor_strategy_fixed import ForwardFactorStrategy

def scan_professional_forward_factors(tickers):
    """
    Scan tickers using ALL professional timeframes: 30/60, 30/90, 60/90 DTE
    """
    print("=== Professional Forward Factor Scanner ===")
    print("Timeframes: 30/60, 30/90, 60/90 DTE")
    print()
    
    strategy = ForwardFactorStrategy()
    
    # Authenticate with Schwab API
    if not strategy.scanner.authenticate():
        print("❌ Failed to authenticate with Schwab API")
        return
    
    all_opportunities = []
    
    for ticker in tickers:
        try:
            # Get all professional timeframe combinations for this ticker
            raw_data = strategy.scanner.get_option_chain(ticker, expiration_count=12)
            if not raw_data:
                continue
            
            chains = strategy.scanner.parse_option_chain(raw_data, ticker)
            if len(chains) < 2:
                continue
            
            # Sort by DTE
            chains.sort(key=lambda x: x.days_to_expiration)
            valid_chains = [chain for chain in chains if chain.days_to_expiration >= 7]
            
            if len(valid_chains) < 2:
                continue
            
            # Check all three professional timeframe combinations
            timeframe_specs = [
                (30, 15, 60, 20, "30/60"),  # 15-45 DTE vs 40-80 DTE
                (30, 15, 90, 25, "30/90"),  # 15-45 DTE vs 65-115 DTE  
                (60, 20, 90, 25, "60/90"),  # 40-80 DTE vs 65-115 DTE
            ]
            
            ticker_opportunities = []
            
            for near_target, near_buffer, next_target, next_buffer, timeframe_name in timeframe_specs:
                near_min, near_max = near_target - near_buffer, near_target + near_buffer
                next_min, next_max = next_target - next_buffer, next_target + next_buffer
                
                best_pair = None
                best_score = float('inf')
                
                # Find the best match for this timeframe spec
                for i, chain1 in enumerate(valid_chains):
                    if near_min <= chain1.days_to_expiration <= near_max:
                        for chain2 in valid_chains[i+1:]:
                            if next_min <= chain2.days_to_expiration <= next_max:
                                # Calculate deviation from ideal targets
                                near_dev = abs(chain1.days_to_expiration - near_target)
                                next_dev = abs(chain2.days_to_expiration - next_target)
                                score = near_dev + next_dev
                                
                                if score < best_score:
                                    best_score = score
                                    best_pair = (chain1, chain2, timeframe_name)
                
                if best_pair:
                    near_chain, next_chain, tf_name = best_pair
                    
                    # Calculate Forward Factor for this timeframe
                    opportunity = strategy.analyzer.calculate_forward_factor_opportunity(near_chain, next_chain)
                    
                    if opportunity and opportunity.ff_result and opportunity.ff_result.is_valid:
                        ff_pct = opportunity.ff_result.forward_factor_percent
                        near_iv = opportunity.near_term_iv.atm_iv * 100 if opportunity.near_term_iv.atm_iv else 0
                        next_iv = opportunity.next_term_iv.atm_iv * 100 if opportunity.next_term_iv.atm_iv else 0
                        
                        # Debug output
                        print(f"Found {tf_name} opportunity for {ticker}: FF={ff_pct:.1f}% (DTE: {near_chain.days_to_expiration}/{next_chain.days_to_expiration})")
                        
                        ticker_opportunities.append({
                            'ticker': ticker,
                            'timeframe': tf_name,
                            'price': near_chain.underlying_price,
                            'forward_factor': ff_pct,
                            'near_iv': near_iv,
                            'next_iv': next_iv,
                            'dte_pair': f"{near_chain.days_to_expiration}/{next_chain.days_to_expiration}",
                            'volume': getattr(near_chain, 'total_volume', 0)  # If available
                        })
                    else:
                        print(f"No valid opportunity for {ticker} {tf_name}: DTE {near_chain.days_to_expiration}/{next_chain.days_to_expiration}")
                else:
                    print(f"No matching chains for {ticker} {timeframe_name}")
            
            all_opportunities.extend(ticker_opportunities)
            
        except Exception as e:
            print(f"  ❌ {ticker}: Error - {e}")
        
    print("=" * 80)
    
    # Group opportunities by timeframe for display
    timeframes = ['30/60', '30/90', '60/90']
    
    for timeframe in timeframes:
        tf_opportunities = [opp for opp in all_opportunities if opp['timeframe'] == timeframe]
        
        if tf_opportunities:
            print(f"\n🏷️  Displaying plays for timeframe: {timeframe}")
            print(f"📋 Preview (top {min(10, len(tf_opportunities))}):")
            print()
            print(f"{'Ticker Symbol':<12} | {'Price':<8} | {'Forward Factor':<25} | {'Option Volume':<20}")
            print("-" * 80)
            
            # Sort by Forward Factor magnitude
            tf_opportunities.sort(key=lambda x: abs(x['forward_factor']), reverse=True)
            
            for opp in tf_opportunities[:10]:
                ticker = opp['ticker']
                price = f"{opp['price']:.2f}"
                ff_pct = f"{opp['forward_factor']:.1f}%"
                volume = f"{opp.get('volume', 0):.0f}K"  # Placeholder volume
                
                print(f"{ticker:<12} | {price:<8} | {ff_pct:<25} | {volume:<20}")
            
            print()
    
    if not all_opportunities:
        print("No Forward Factor opportunities found across all timeframes.")

if __name__ == "__main__":
    # Test with tickers from professional scanner
    test_tickers = ["TSLA"]
    scan_professional_forward_factors(test_tickers)