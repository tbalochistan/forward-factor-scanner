#!/usr/bin/env python3

import math

def test_forward_factor_calculation():
    """Test the correct Forward Factor calculation against your manual calculation"""
    
    # Your values
    iv1 = 0.604  # 60.4%
    iv2 = 0.496  # 49.6%
    dte1 = 25
    dte2 = 74
    
    print("=== Forward Factor Test Calculation ===")
    print(f"25 Day IV = {iv1*100:.1f}% = {iv1:.3f}")
    print(f"74 Day IV = {iv2*100:.1f}% = {iv2:.3f}")
    print()
    
    # Step 1: Convert IV to variance
    v1 = iv1 * iv1  # V1 = σ1²
    v2 = iv2 * iv2  # V2 = σ2²
    print(f"V1 = {iv1:.3f}² = {v1:.4f}")
    print(f"V2 = {iv2:.3f}² = {v2:.4f}")
    print()
    
    # Step 2: Calculate time fractions
    t1 = dte1 / 365.0  # T1 = DTE1/365
    t2 = dte2 / 365.0  # T2 = DTE2/365
    print(f"T1 = {dte1}/365 = {t1:.4f}")
    print(f"T2 = {dte2}/365 = {t2:.4f}")
    print()
    
    # Step 3: Calculate forward variance
    time_diff = t2 - t1
    forward_variance = (v2 * t2 - v1 * t1) / time_diff
    print(f"Forward Variance = ({v2:.4f} * {t2:.4f} - {v1:.4f} * {t1:.4f}) / ({t2:.4f} - {t1:.4f})")
    print(f"                 = ({v2 * t2:.6f} - {v1 * t1:.6f}) / {time_diff:.4f}")
    print(f"                 = {forward_variance:.6f}")
    print()
    
    # Step 4: Calculate forward volatility
    forward_volatility = math.sqrt(forward_variance)
    print(f"Forward Volatility = √{forward_variance:.6f} = {forward_volatility:.6f}")
    print(f"                   = {forward_volatility*100:.2f}%")
    print()
    
    # Step 5: Calculate Forward Factor
    forward_factor = (iv1 - forward_volatility) / forward_volatility
    forward_factor_percent = forward_factor * 100
    print(f"Forward Factor = ({iv1:.3f} - {forward_volatility:.6f}) / {forward_volatility:.6f}")
    print(f"               = {forward_factor:.6f}")
    print(f"               = {forward_factor_percent:.1f}%")
    print()
    
    print("Expected: 40.3%")
    print(f"Got:      {forward_factor_percent:.1f}%")
    print(f"Difference: {abs(forward_factor_percent - 40.3):.1f}%")

if __name__ == "__main__":
    test_forward_factor_calculation()