import sys
import os
import logging
from typing import List

# Fix path
sys.path.append(os.getcwd())

from src.screening.screener import screen_stocks
from src.data.loader import fetch_stock_data
from src.screening.indicators import calculate_technical_indicators
from src.analysis.chart import generate_chart_image
from src.analysis.llm import GeminiAnalyst
from src.execution.manager import TradeManager
from src.config import Config

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("gemini_sniper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Main")

from src.data.market_provider import RealTimeProvider, HistoricalReplayProvider
from datetime import datetime

def run_session(simulation_date: datetime = None):
    """
    Generator function that runs the session and yields updates for the UI.
    Yields tuples: (STEP_TYPE, DATA)
    """
    yield ("STATUS", "Starting Gemini-Sniper Day Trading Session...")
    
    # Initialize Components
    analyst = GeminiAnalyst()
    trader = TradeManager() 
    
    # Initialize Market Provider
    sim_universe = None
    if simulation_date:
        yield ("STATUS", f"Initializing Simulation Mode for {simulation_date.date()}...")
        
        # Load FULL NASDAQ 100 (No limits, relying on curl_cffi)
        from src.data.loader import get_nasdaq_100_tickers
        sim_universe = get_nasdaq_100_tickers() 
        
        # FAIL-SAFE: Pre-flight Data Check
        # We must ensure we can fetch data for at least a subset before proceeding.
        # If the provider fails to initialize (e.g., all downloads fail), we abort.
        try:
            provider = HistoricalReplayProvider(sim_universe, simulation_date)
            # Check if provider has valid data
            # data_cache is a DataFrame with tickers as columns
            valid_tickers = [t for t in sim_universe if t in provider.data_cache.columns]
            
            if not valid_tickers:
                yield ("ERROR", "CRITICAL: No historical data available for ANY ticker. Aborting Simulation.")
                return
            
            # Update universe to only valid tickers to prevent 0.0 price errors
            sim_universe = valid_tickers
            yield ("STATUS", f"Simulation Ready: {len(sim_universe)} tickers loaded successfully.")
            
        except Exception as e:
            yield ("ERROR", f"CRITICAL: Simulation Initialization Failed: {e}")
            return

    else:
        provider = RealTimeProvider()

    # 1. Screen Stocks
    yield ("STATUS", "Phase 1: Screening for Day Trading Setups...")
    # Pass the VALIDATED universe AND the provider to screener
    # Now provider is ALWAYS passed, ensuring unified logic
    screened_df = screen_stocks(whitelist=sim_universe, provider=provider)
    
    if screened_df.empty:
        yield ("ERROR", "No stocks passed screening.")
        return
        
    top_candidates = screened_df
    yield ("SCREENER_RESULT", top_candidates)
    
    # 2. Analyze & Execute
    yield ("STATUS", "Phase 2: Analysis & Entry...")
    
    for _, row in top_candidates.iterrows():
        ticker = row['Ticker']
        price = row['Price']
        atr = row['ATR']
        
        yield ("STATUS", f"Analyzing {ticker}...")
        
        # A. Fetch Data
        df = fetch_stock_data(ticker)
        if df.empty:
            continue
        df = calculate_technical_indicators(df)
        
        # B. Generate Chart
        chart_bytes = generate_chart_image(df, ticker)
        
        # C. LLM Analysis
        technicals = {
            "RSI": row['RSI'],
            "ATR": atr,
            "Gap%": row['Gap%'],
            "RelVol": row['RelVol'],
            "Price": price
        }
        
        analysis_result = analyst.analyze_stock(ticker, chart_bytes, technicals)
        
        # Yield Analysis Result for UI
        yield ("ANALYSIS", {
            "ticker": ticker,
            "chart": chart_bytes,
            "result": analysis_result
        })
        
        # D. Execution
        trade_event = trader.process_analysis(analysis_result, price, atr, current_time=provider.get_time())
        if trade_event:
            yield trade_event
        
        # Yield Trade Updates (Snapshot of portfolio)
        account = trader.broker.get_account()
        yield ("PORTFOLIO_UPDATE", account)

    # Phase 3 Transition
    yield ("STATUS", "Phase 3: Real-time Monitoring & Management...")
    
    # We need to monitor the positions we actually entered.
    # The 'trader' object has the portfolio.
    
    # Initial Chart for the first entered position (if any)
    current_positions = trader.get_portfolio()
    active_ticker = None
    if current_positions:
        active_ticker = list(current_positions.keys())[0]
    elif not top_candidates.empty:
        active_ticker = top_candidates.iloc[0]['Ticker']

    # Run monitoring loop (e.g., 400 iterations for sim)
    max_iter = 400 if simulation_date else 10

    for step_data in trader.start_monitoring_loop(provider, max_iterations=max_iter):
        # step_data is whatever start_monitoring_loop yields
        # It yields ("MONITOR", {...}) or ("TRADE_ALERT", ...)
        
        msg_type = step_data[0]
        payload = step_data[1]
        
        if msg_type == "MONITOR":
            # Update UI with current price/status
            # payload might be dict of prices?
            # Let's yield a status update
            
            # Check if we have an active position to chart
            positions = trader.get_portfolio()
            if positions:
                # If we have positions, ALWAYS chart the first one (or cycle them?)
                # User wants to see the held stock.
                target_ticker = list(positions.keys())[0]
                
                # Generate chart for this ticker
                # We need a provider to get history for the chart?
                # generate_chart_image uses fetch_stock_data internally currently?
                # We should refactor generate_chart_image to use provider too, but for now
                # let's just pass the ticker.
                
                # Note: generate_chart_image calls fetch_stock_data. 
                # In simulation, this might fail if we don't pass the provider's data.
                # For now, let's assume fetch_stock_data works (it does, via provider or direct).
                # Wait, generate_chart_image imports fetch_stock_data directly.
                # We need to pass the dataframe to it if we want to be pure.
                # But for now, let's just try to generate it.
                
                # Get history from provider to ensure consistency
                hist_df = provider.get_history(target_ticker, period="1d") # Get intraday if possible?
                # provider.get_history returns daily data by default in our interface.
                # We might need intraday for the chart?
                # The chart function fetches 1mo/3mo daily data usually.
                
                chart_path = generate_chart_image(hist_df, target_ticker) # This uses default fetcher
                
                yield ("ANALYSIS", {
                    "ticker": target_ticker,
                    "price": provider.get_current_price(target_ticker),
                    "chart": chart_path,
                    "time": provider.get_time()
                })
            elif active_ticker:
                 # No positions, show the watchlist candidate
                 chart_path = generate_chart_image(active_ticker)
                 yield ("ANALYSIS", {
                    "ticker": active_ticker,
                    "price": provider.get_current_price(active_ticker),
                    "chart": chart_path,
                    "time": provider.get_time()
                })

            yield step_data
            
        elif msg_type == "TRADE_ALERT":
            yield step_data
            
        # Pass through other messages
        else:
            yield step_data
    
    # 4. End of Session (EOD Re-evaluation)
    yield ("STATUS", "🔔 Market Closing! Starting EOD Re-evaluation...")
    
    for step_type, data in trader.perform_eod_review(analyst):
        yield (step_type, data)
    
    yield ("STATUS", "Session Cycle Finished. Remaining positions are HELD OVERNIGHT.")
    
    final_account = trader.broker.get_account()
    yield ("PORTFOLIO_UPDATE", final_account)

def main():
    # CLI Wrapper for run_session
    for step_type, data in run_session():
        if step_type == "STATUS":
            logger.info(data)
        elif step_type == "ANALYSIS":
            logger.info(f"Analysis for {data['ticker']}: {data['result']['action']}")
        elif step_type == "ERROR":
            logger.error(data)

