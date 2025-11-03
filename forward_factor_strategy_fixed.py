"""
Forward Factor Trading Strategy - Main Orchestrator

This is the main script that orchestrates the entire Forward Factor trading strategy:
1. Filter midcap tickers
2. Scan options chains via Schwab API
3. Apply liquidity filters
4. Analyze implied volatility
5. Calculate Forward Factor opportunities
6. Rank and output trading opportunities

Author: Generated for ForwardFactorStrat project
Date: December 2024
"""

import sys
import json
import time
import logging
import argparse
from datetime import datetime, date
from typing import List, Dict, Optional
from pathlib import Path

# Rich library for professional table formatting
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns
from rich import box

# Import our custom modules
from midcap_filter import MidcapFilter
from options_scanner import SchwabOptionsScanner
from liquidity_filter import LiquidityFilter, LiquidityThresholds
from iv_ff_analyzer import IVForwardFactorAnalyzer, ForwardFactorOpportunity


class ForwardFactorStrategy:
    """
    Main orchestrator for the Forward Factor trading strategy.
    
    Coordinates all components to identify midcap options trading opportunities
    based on Forward Factor analysis.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the strategy.
        
        Args:
            config_file: Optional path to configuration file
        """
        self.config = self._load_config(config_file)
        self.setup_logging()
        
        # Initialize Rich console for professional formatting
        self.console = Console()
        
        # Initialize components
        self.midcap_filter = MidcapFilter()
        self.liquidity_filter = LiquidityFilter(self._create_liquidity_thresholds())
        self.scanner = SchwabOptionsScanner()
        self.analyzer = IVForwardFactorAnalyzer(self.liquidity_filter)
        
        self.logger = logging.getLogger(__name__)
        
    def _load_config(self, config_file: Optional[str]) -> Dict:
        """Load configuration from file or use defaults."""
        default_config = {
            "scanning": {
                "max_tickers": 50,
                "api_delay_seconds": 0.5,
                "timeout_seconds": 30
            },
            "liquidity": {
                "min_volume": 50,
                "min_open_interest": 100,
                "max_bid_ask_spread_pct": 10.0,
                "min_bid": 0.05,
                "min_ask": 0.10,
                "max_bid_ask_spread_abs": 2.0,
                "min_mid_price": 0.10,
                "min_volume_oi_ratio": 0.1,
                "max_days_to_expiration": 90,
                "min_days_to_expiration": 7
            },
            "forward_factor": {
                "min_confidence": 30.0,
                "bullish_threshold": 5.0,
                "bearish_threshold": -5.0,
                "max_opportunities": 20
            },
            "output": {
                "save_detailed_results": True,
                "save_csv": True,
                "results_directory": "results",
                "timestamp_files": True
            },
            "logging": {
                "level": "INFO",
                "file_logging": True,
                "console_logging": True
            }
        }
        
        if config_file and Path(config_file).exists():
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                    # Merge configs (user config overwrites defaults)
                    for section, values in user_config.items():
                        if section in default_config:
                            default_config[section].update(values)
                        else:
                            default_config[section] = values
            except Exception as e:
                print(f"Warning: Could not load config file {config_file}: {e}")
                print("Using default configuration.")
        
        return default_config
    
    def _create_liquidity_thresholds(self) -> LiquidityThresholds:
        """Create liquidity thresholds from config."""
        liq_config = self.config["liquidity"]
        return LiquidityThresholds(
            min_volume=liq_config["min_volume"],
            min_open_interest=liq_config["min_open_interest"],
            max_bid_ask_spread_pct=liq_config["max_bid_ask_spread_pct"],
            min_bid=liq_config["min_bid"],
            min_ask=liq_config["min_ask"],
            max_bid_ask_spread_abs=liq_config["max_bid_ask_spread_abs"],
            min_mid_price=liq_config["min_mid_price"],
            min_volume_oi_ratio=liq_config["min_volume_oi_ratio"],
            max_days_to_expiration=liq_config["max_days_to_expiration"],
            min_days_to_expiration=liq_config["min_days_to_expiration"]
        )
    
    def setup_logging(self):
        """Setup logging configuration."""
        log_config = self.config["logging"]
        level = getattr(logging, log_config["level"].upper(), logging.INFO)
        
        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        formatters = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console logging
        if log_config["console_logging"]:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatters)
            root_logger.addHandler(console_handler)
        
        # File logging
        if log_config["file_logging"]:
            results_dir = Path(self.config["output"]["results_directory"])
            results_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = results_dir / f"ff_strategy_{timestamp}.log"
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatters)
            root_logger.addHandler(file_handler)
        
        root_logger.setLevel(level)
    
    def get_ticker_universe(self, custom_tickers: Optional[List[str]] = None) -> List[str]:
        """
        Get the universe of tickers to scan.
        
        Args:
            custom_tickers: Optional custom ticker list. Uses suggested midcaps if None.
            
        Returns:
            List of ticker symbols to scan
        """
        if custom_tickers:
            # Use custom tickers directly without midcap filtering
            tickers = [ticker.upper() for ticker in custom_tickers]
            self.logger.info(f"Using custom ticker list: {len(tickers)} tickers")
        else:
            # Use suggested midcap universe
            tickers = self.midcap_filter.get_suggested_midcap_universe()
            self.logger.info(f"Using suggested midcap universe: {len(tickers)} tickers")
        
        # Limit to max_tickers for performance
        max_tickers = self.config["scanning"]["max_tickers"]
        if len(tickers) > max_tickers:
            tickers = tickers[:max_tickers]
            self.logger.info(f"Limited to {max_tickers} tickers for performance")
        
        return tickers
    
    def authenticate_api(self) -> bool:
        """
        Authenticate with Schwab API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            self.scanner.authenticate()
            self.logger.info("Schwab API authentication successful")
            return True
        except Exception as e:
            self.logger.error(f"Schwab API authentication failed: {e}")
            return False
    
    def run_strategy(
        self, 
        custom_tickers: Optional[List[str]] = None,
        save_results: bool = True
    ) -> tuple[List[ForwardFactorOpportunity], List[dict], List[dict]]:
        """
        Run the complete Forward Factor strategy.
        
        Args:
            custom_tickers: Optional custom ticker list
            save_results: Whether to save results to files
            
        Returns:
            Tuple of (opportunities, opportunity_data) where opportunity_data contains timeframe info
        """
        start_time = datetime.now()
        self.logger.info("=" * 60)
        self.logger.info("Starting Forward Factor Strategy Scan")
        self.logger.info("=" * 60)
        
        # Step 1: Authenticate with Schwab API
        if not self.authenticate_api():
            self.logger.error("Cannot proceed without API authentication")
            return []
        
        # Step 2: Get ticker universe
        tickers = self.get_ticker_universe(custom_tickers)
        self.logger.info(f"Scanning {len(tickers)} midcap tickers")
        
        # Step 3: Scan for opportunities across all professional timeframes
        self.logger.info("Beginning options chain scanning...")
        
        # Professional timeframes: 30/60, 30/90, 60/90 DTE
        all_opportunities = []
        all_tested_tickers = []  # Track all tickers tested with their results
        
        for ticker in tickers:
            try:
                # Get option chains for this ticker
                raw_data = self.scanner.get_option_chain(ticker, expiration_count=12)
                if not raw_data:
                    self.logger.warning(f"No option chain data for {ticker}")
                    continue
                    
                chains = self.scanner.parse_option_chain(raw_data, ticker)
                if len(chains) < 2:
                    self.logger.warning(f"Insufficient option chains for {ticker}: {len(chains)} chains")
                    continue
                
                # Only include chains with sufficient time
                valid_chains = [chain for chain in chains if chain.days_to_expiration >= 7]
                if len(valid_chains) < 2:
                    self.logger.warning(f"Insufficient valid chains for {ticker}: {len(valid_chains)} chains with DTE >= 7")
                    continue
                
                self.logger.info(f"Scanning {ticker}: {len(valid_chains)} valid chains")
                
                # Get underlying price
                underlying_price = valid_chains[0].underlying_price if valid_chains else 0
                
                # Initialize ticker result tracking
                ticker_results = {
                    'ticker': ticker,
                    'price': underlying_price,
                    'timeframes': {}
                }
                
                # Check all three professional timeframe combinations  
                timeframe_specs = [
                    (30, 15, 60, 20, "30/60"),  # 15-45 DTE vs 40-80 DTE
                    (30, 15, 90, 25, "30/90"),  # 15-45 DTE vs 65-115 DTE  
                    (60, 20, 90, 25, "60/90"),  # 40-80 DTE vs 65-115 DTE
                ]
                
                ticker_found_any = False
                
                for near_target, near_buffer, next_target, next_buffer, timeframe_name in timeframe_specs:
                    near_min, near_max = near_target - near_buffer, near_target + near_buffer
                    next_min, next_max = next_target - next_buffer, next_target + next_buffer
                    
                    best_pair = None
                    best_score = float('inf')
                    
                    # Find best matching pair for this timeframe
                    for chain1 in valid_chains:
                        if near_min <= chain1.days_to_expiration <= near_max:
                            for chain2 in valid_chains:
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
                        
                        self.logger.info(f"Attempting {tf_name} for {ticker}: {near_chain.days_to_expiration}/{next_chain.days_to_expiration} DTE")
                        
                        # Calculate Forward Factor for this timeframe
                        try:
                            opportunity = self.analyzer.calculate_forward_factor_opportunity(near_chain, next_chain)
                        except Exception as e:
                            self.logger.warning(f"Error calculating FF for {ticker} {tf_name}: {e}")
                            
                            # Store failed result
                            ticker_results['timeframes'][tf_name] = {
                                'forward_factor': None,
                                'front_vol': 0.0,
                                'back_vol': 0.0,
                                'front_dte': near_chain.days_to_expiration if near_chain else 0,
                                'back_dte': next_chain.days_to_expiration if next_chain else 0,
                                'volume': 0,
                                'error': str(e)
                            }
                            continue
                        
                        # Process the opportunity result
                        if opportunity and opportunity.ff_result:
                            ff_pct = opportunity.ff_result.forward_factor_percent
                            near_iv = opportunity.near_term_iv.atm_iv if opportunity.near_term_iv.atm_iv else 0
                            next_iv = opportunity.next_term_iv.atm_iv if opportunity.next_term_iv.atm_iv else 0
                            
                            # Calculate total volume for the chain
                            chain_volume = sum(opt.volume for opt in near_chain.strikes.values()) if near_chain.strikes else 0
                            
                            # Store timeframe result
                            ticker_results['timeframes'][tf_name] = {
                                'forward_factor': ff_pct,
                                'front_vol': near_iv,
                                'back_vol': next_iv,
                                'front_dte': near_chain.days_to_expiration,
                                'back_dte': next_chain.days_to_expiration,
                                'volume': chain_volume,
                                'error': None
                            }
                            
                            # Accept all opportunities, regardless of is_valid flag (for now)
                            self.logger.info(f"Found {tf_name} opportunity for {ticker}: FF={ff_pct:.1f}% (DTE: {near_chain.days_to_expiration}/{next_chain.days_to_expiration}) [Valid: {opportunity.ff_result.is_valid}] Near IV: {near_iv:.1f}% Next IV: {next_iv:.1f}%")
                            
                            # Store opportunity with timeframe info
                            opp_data = {
                                'ticker': ticker,
                                'timeframe': tf_name,
                                'price': near_chain.underlying_price,
                                'forward_factor': ff_pct,
                                'near_iv': near_iv,
                                'next_iv': next_iv,
                                'opportunity': opportunity,
                                'dte_pair': f"{near_chain.days_to_expiration}/{next_chain.days_to_expiration}",
                                'volume': getattr(near_chain, 'total_volume', 0)
                            }
                            all_opportunities.append(opp_data)
                            ticker_found_any = True
                        elif opportunity:
                            # Even if no ff_result, store what we can
                            near_iv = opportunity.near_term_iv.atm_iv if opportunity.near_term_iv and opportunity.near_term_iv.atm_iv else 0
                            next_iv = opportunity.next_term_iv.atm_iv if opportunity.next_term_iv and opportunity.next_term_iv.atm_iv else 0
                            chain_volume = sum(opt.volume for opt in near_chain.strikes.values()) if near_chain.strikes else 0
                            
                            ticker_results['timeframes'][tf_name] = {
                                'forward_factor': None,
                                'front_vol': near_iv,
                                'back_vol': next_iv,
                                'front_dte': near_chain.days_to_expiration,
                                'back_dte': next_chain.days_to_expiration,
                                'volume': chain_volume,
                                'error': 'No FF result'
                            }
                            
                            self.logger.warning(f"FF opportunity for {ticker} {tf_name} has no result: ff_result={opportunity.ff_result} Near IV: {near_iv:.1f}% Next IV: {next_iv:.1f}%")
                        else:
                            # No opportunity object at all
                            ticker_results['timeframes'][tf_name] = {
                                'forward_factor': None,
                                'front_vol': 0.0,
                                'back_vol': 0.0,
                                'front_dte': near_chain.days_to_expiration if near_chain else 0,
                                'back_dte': next_chain.days_to_expiration if next_chain else 0,
                                'volume': 0,
                                'error': 'No opportunity object'
                            }
                            self.logger.warning(f"No FF opportunity object for {ticker} {tf_name}: DTE {near_chain.days_to_expiration}/{next_chain.days_to_expiration}")
                    else:
                        # No matching chains for this timeframe
                        ticker_results['timeframes'][tf_name] = {
                            'forward_factor': None,
                            'front_vol': 0.0,
                            'back_vol': 0.0,
                            'front_dte': 0,
                            'back_dte': 0,
                            'volume': 0,
                            'error': 'No matching chains'
                        }
                        self.logger.debug(f"No matching chains for {ticker} {timeframe_name}")
                
                # Add ticker results to tracking list
                all_tested_tickers.append(ticker_results)
                
                if not ticker_found_any:
                    dte_list = [chain.days_to_expiration for chain in valid_chains]
                    self.logger.info(f"No opportunities found for {ticker}. Available DTEs: {sorted(dte_list)}")
                        
            except Exception as e:
                self.logger.warning(f"Error scanning {ticker}: {e}")
                continue
        
        # Convert to original format for compatibility
        opportunities = [opp['opportunity'] for opp in all_opportunities]
        
        # Step 4: All opportunities (no artificial limits)
        # If tickers have FF > 20%, you want to see them all!
        
        # Log results
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        self.logger.info("=" * 60)
        self.logger.info("Forward Factor Strategy Scan Complete")
        self.logger.info("=" * 60)
        self.logger.info(f"Scan duration: {duration:.1f} seconds")
        self.logger.info(f"Tickers scanned: {len(tickers)}")
        self.logger.info(f"Opportunities found: {len(all_opportunities)}")
        
        # Step 5: Save results
        if save_results and opportunities:
            self.save_results(opportunities)
        
        return opportunities, all_opportunities, all_tested_tickers
    
    def save_results(self, opportunities: List[ForwardFactorOpportunity]):
        """Save results to files."""
        if not opportunities:
            return
        
        output_config = self.config["output"]
        results_dir = Path(output_config["results_directory"])
        results_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed JSON results
        if output_config["save_detailed_results"]:
            json_file = results_dir / f"ff_opportunities_{timestamp}.json"
            detailed_results = []
            
            for opp in opportunities:
                summary = self.analyzer.get_opportunity_summary(opp)
                detailed_results.append({
                    "summary": summary,
                    "scan_timestamp": datetime.now().isoformat(),
                    "near_term_liquidity_count": len(opp.near_term_liquidity),
                    "next_term_liquidity_count": len(opp.next_term_liquidity),
                    "all_reasons": opp.reasons
                })
            
            with open(json_file, 'w') as f:
                json.dump(detailed_results, f, indent=2)
            
            self.logger.info(f"Detailed results saved to: {json_file}")
        
        # Save CSV summary
        if output_config["save_csv"]:
            csv_file = results_dir / f"ff_opportunities_{timestamp}.csv"
            self._save_csv_results(opportunities, csv_file)
            self.logger.info(f"CSV summary saved to: {csv_file}")
    
    def _save_csv_results(self, opportunities: List[ForwardFactorOpportunity], csv_file: Path):
        """Save opportunities to CSV file."""
        import csv
        
        headers = [
            'ticker', 'underlying_price', 'opportunity_type', 'confidence_score',
            'forward_factor_pct', 'forward_volatility_pct', 'near_term_dte', 
            'next_term_dte', 'near_term_iv', 'next_term_iv', 'near_term_liquidity_count',
            'next_term_liquidity_count', 'primary_reason'
        ]
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            
            for opp in opportunities:
                summary = self.analyzer.get_opportunity_summary(opp)
                writer.writerow(summary)
    
    def create_professional_table(self, timeframe: str, timeframe_rows: List, threshold: float) -> Table:
        """Create a professional Rich table for a specific timeframe."""
        
        # Create table with professional styling
        table = Table(
            box=box.ROUNDED,
            show_header=True,
            header_style="bold white on blue",
            title=f"[bold cyan]🏷️  Timeframe: {timeframe}[/bold cyan]",
            title_style="bold",
            show_lines=True
        )
        
        # Add columns with proper styling
        table.add_column("Ticker", style="bold white", justify="center", min_width=8)
        table.add_column("Price", style="cyan", justify="right", min_width=8)
        table.add_column("Front Vol (DTE)", style="yellow", justify="center", min_width=14)
        table.add_column("Back Vol (DTE)", style="yellow", justify="center", min_width=13)
        table.add_column("Forward Factor", style="magenta", justify="center", min_width=15)
        table.add_column("FF Threshold", style="white", justify="center", min_width=12)
        table.add_column("Pass/Fail", justify="center", min_width=9)
        table.add_column("Option Volume", style="green", justify="right", min_width=15)
        
        # Add rows with conditional formatting
        for ticker, price, front_vol, back_vol, front_dte, back_dte, ff_display, threshold_display, pass_fail, volume in timeframe_rows:
            price_str = f"${price:.2f}" if price > 0 else "N/A"
            front_vol_str = f"{front_vol:.1f}% ({front_dte})" if front_vol > 0 and front_dte > 0 else "[dim]N/A[/dim]"
            back_vol_str = f"{back_vol:.1f}% ({back_dte})" if back_vol > 0 and back_dte > 0 else "[dim]N/A[/dim]"
            volume_str = f"{volume:,.0f}" if volume > 0 else "[dim]N/A[/dim]"
            
            # Determine pass/fail styling and text
            if "✓" in str(pass_fail):
                pass_fail_text = "[bold green]✓ PASS[/bold green]"
            else:
                pass_fail_text = "[bold red]✗ FAIL[/bold red]"
            
            # Color code the Forward Factor based on value
            if ff_display != "N/A":
                ff_val = float(ff_display.replace('%', ''))
                if ff_val >= threshold:
                    ff_colored = f"[bold green]{ff_display}[/bold green]"
                elif ff_val > 0:
                    ff_colored = f"[bold yellow]{ff_display}[/bold yellow]"
                else:
                    ff_colored = f"[bold red]{ff_display}[/bold red]"
            else:
                ff_colored = "[dim]N/A[/dim]"
            
            table.add_row(
                ticker,
                price_str,
                front_vol_str,
                back_vol_str,
                ff_colored,
                f"{threshold:.1f}%",
                pass_fail_text,
                volume_str
            )
        
        return table

    def print_summary(self, opportunities: List[ForwardFactorOpportunity], all_opportunities_data: List = None, all_tested_tickers: List = None):
        """Print a formatted summary of opportunities to console using professional Rich table format."""
        
        # Create header panel
        header_panel = Panel(
            "[bold white on blue] Forward Factor Scanner - Professional Results [/bold white on blue]\n"
            "[cyan]Timeframes: 30/60, 30/90, 60/90 DTE[/cyan]",
            box=box.DOUBLE,
            title="📊 FORWARD FACTOR STRATEGY",
            title_align="center",
            border_style="blue"
        )
        self.console.print(header_panel)
        self.console.print()
        
        # Get FF threshold from config (simplified)
        threshold = self.config["forward_factor"]["signal_threshold"]
        
        # Initialize all_opportunities_data and ticker data if None
        if not all_opportunities_data:
            all_opportunities_data = []
        if not all_tested_tickers:
            all_tested_tickers = []
        
        # Group opportunities by timeframe for display
        timeframes = ['30/60', '30/90', '60/90']
        found_any = False
        
        for timeframe in timeframes:
            timeframe_rows = []
            
            for ticker_data in all_tested_tickers:
                ticker = ticker_data['ticker']
                price = ticker_data['price']
                
                if timeframe in ticker_data['timeframes']:
                    tf_data = ticker_data['timeframes'][timeframe]
                    ff = tf_data['forward_factor']
                    front_vol = tf_data['front_vol']
                    back_vol = tf_data['back_vol']
                    front_dte = tf_data.get('front_dte', 0)
                    back_dte = tf_data.get('back_dte', 0)
                    volume = tf_data['volume']
                    
                    # Simple pass/fail: FF > 20% = signal
                    if ff is not None:
                        if abs(ff) > threshold:  # Your simple rule: FF > 20%
                            pass_fail = "\033[92m✓\033[0m"  # Green checkmark
                            found_any = True
                        else:
                            pass_fail = "\033[91m✗\033[0m"  # Red cross
                        ff_display = f"{ff:.1f}%"
                        threshold_display = f"{threshold:.1f}%"
                    else:
                        ff_display = "N/A"
                        threshold_display = f"{threshold:.1f}%"
                        pass_fail = "\033[91m✗\033[0m"  # Red cross
                    
                    timeframe_rows.append((
                        ticker, price, front_vol, back_vol, front_dte, back_dte, ff_display, threshold_display, pass_fail, volume
                    ))
            
            # Sort by ticker name for consistent display
            timeframe_rows.sort(key=lambda x: x[0])
            
            # Create and display professional table
            if timeframe_rows:
                table = self.create_professional_table(timeframe, timeframe_rows, threshold)
                self.console.print(table)
            else:
                empty_panel = Panel(
                    "[yellow]No tickers tested for this timeframe[/yellow]",
                    title=f"[bold cyan]🏷️  Timeframe: {timeframe}[/bold cyan]",
                    border_style="yellow"
                )
                self.console.print(empty_panel)
            
            self.console.print()
        
        # Summary panel
        if not found_any:
            summary_text = "[red]No Forward Factor opportunities found that meet threshold criteria across all timeframes.[/red]"
        else:
            passing_count = sum(
                1 for ticker_data in all_tested_tickers
                for tf_name, tf_data in ticker_data['timeframes'].items()
                if tf_data['forward_factor'] is not None and 
                abs(tf_data['forward_factor']) > threshold  # Simple: FF > 20%
            )
            summary_text = f"[green]Found {passing_count} opportunities meeting threshold criteria ({threshold:.1f}%) across all timeframes.[/green]"
        
        summary_panel = Panel(
            f"📝 [bold]SUMMARY[/bold]\n{summary_text}",
            title="[bold]SCAN RESULTS[/bold]",
            title_align="center",
            border_style="green" if found_any else "red",
            box=box.DOUBLE
        )
        self.console.print(summary_panel)


def main():
    """Main function for command-line execution."""
    parser = argparse.ArgumentParser(
        description="Forward Factor Trading Strategy Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python forward_factor_strategy.py                    # Scan suggested midcap universe
  python forward_factor_strategy.py --tickers TEAM,SNOW,CRWD  # Scan specific tickers
  python forward_factor_strategy.py --config my_config.json   # Use custom config
  python forward_factor_strategy.py --no-save                 # Don't save results
        """
    )
    
    parser.add_argument(
        '--tickers', '-t',
        help='Comma-separated list of tickers to scan (e.g., TEAM,SNOW,CRWD)'
    )
    
    parser.add_argument(
        '--config', '-c',
        help='Path to configuration JSON file'
    )
    
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Do not save results to files'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Minimal console output'
    )
    
    args = parser.parse_args()
    
    # Parse custom tickers
    custom_tickers = None
    if args.tickers:
        custom_tickers = [t.strip().upper() for t in args.tickers.split(',')]
    
    # Initialize and run strategy
    try:
        strategy = ForwardFactorStrategy(config_file=args.config)
        
        if not args.quiet:
            print("Forward Factor Trading Strategy")
            print("Developed for midcap options opportunity scanning")
            print("\nInitializing strategy components...")
        
        opportunities, all_opportunities_data, all_tested_tickers = strategy.run_strategy(
            custom_tickers=custom_tickers,
            save_results=not args.no_save
        )
        
        if not args.quiet:
            strategy.print_summary(opportunities, all_opportunities_data, all_tested_tickers)
        
        return len(opportunities)
        
    except KeyboardInterrupt:
        print("\nStrategy scan interrupted by user.")
        return 0
    except Exception as e:
        print(f"\nStrategy scan failed: {e}")
        import traceback
        traceback.print_exc()
        return -1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)