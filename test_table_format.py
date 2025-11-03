"""
Test the professional table format with sample data
"""

def test_professional_table():
    # Sample data that mimics what we would find
    sample_opportunities = [
        {
            'ticker': 'TSLA',
            'timeframe': '30/60',
            'price': 248.50,
            'forward_factor': 12.3,
            'volume': 15600
        },
        {
            'ticker': 'AAPL', 
            'timeframe': '30/60',
            'price': 225.91,
            'forward_factor': 8.7,
            'volume': 23400
        },
        {
            'ticker': 'NVDA',
            'timeframe': '30/90', 
            'price': 132.65,
            'forward_factor': 15.2,
            'volume': 45200
        },
        {
            'ticker': 'SPY',
            'timeframe': '60/90',
            'price': 573.20,
            'forward_factor': 6.4,
            'volume': 78900
        }
    ]
    
    print("=== Professional Forward Factor Scanner ===")
    print("Timeframes: 30/60, 30/90, 60/90 DTE")
    print()
    
    # Group opportunities by timeframe for display
    timeframes = ['30/60', '30/90', '60/90']
    
    for timeframe in timeframes:
        tf_opportunities = [opp for opp in sample_opportunities if opp['timeframe'] == timeframe]
        
        if tf_opportunities:
            print(f"🏷️  Displaying plays for timeframe: {timeframe}")
            print(f"📋 Preview (top {min(10, len(tf_opportunities))}):")
            print()
            print(f"{'Ticker Symbol':<12} | {'Price':<8} | {'Forward Factor':<25} | {'Option Volume':<20}")
            print("-" * 80)
            
            # Sort by Forward Factor magnitude
            tf_opportunities.sort(key=lambda x: abs(x['forward_factor']), reverse=True)
            
            for opp in tf_opportunities[:10]:
                ticker = opp['ticker']
                price = f"${opp['price']:.2f}"
                ff_pct = f"{opp['forward_factor']:.1f}%"
                volume = f"{opp.get('volume', 0)/1000:.0f}K"
                
                print(f"{ticker:<12} | {price:<8} | {ff_pct:<25} | {volume:<20}")
            
            print()
    
    print("=" * 80)

if __name__ == "__main__":
    test_professional_table()