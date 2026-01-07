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
from src.data.news import fetch_latest_news, fetch_fundamental_summary
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

def main():
    logger.info("Starting Gemini-Sniper Daily Run...")
    
    # 1. Screen Stocks
    logger.info("Phase 1: Screening...")
    screened_df = screen_stocks()
    if screened_df.empty:
        logger.info("No stocks passed screening.")
        return
        
    top_candidates = screened_df.head(3) # Limit to top 3 for MVP/Cost
    logger.info(f"Top Candidates: {top_candidates['Ticker'].tolist()}")
    
    # Initialize Components
    analyst = GeminiAnalyst()
    trader = TradeManager()
    
    # 2. Analyze & Execute
    logger.info("Phase 2 & 3: Analysis & Execution...")
    
    for _, row in top_candidates.iterrows():
        ticker = row['Ticker']
        price = row['Price']
        atr = row['ATR']
        
        logger.info(f"Analyzing {ticker}...")
        
        # A. Fetch Data
        df = fetch_stock_data(ticker)
        if df.empty:
            continue
            
        df = calculate_technical_indicators(df)
        
        # B. Generate Chart
        # Convert chart to in-memory bytes
        chart_bytes = generate_chart_image(df, ticker)
        
        # C. Fetch News
        news = fetch_latest_news(ticker)
        news_str = "\n".join([f"- {n['title']}" for n in news])
        fundamentals = fetch_fundamental_summary(ticker)
        
        # D. LLM Analysis
        technicals = {
            "RSI": row['RSI'],
            "ATR": atr,
            "Price": price
        }
        
        analysis_result = analyst.analyze_stock(ticker, chart_bytes, news_str, fundamentals, technicals)
        logger.info(f"Gemini Analysis for {ticker}: {analysis_result}")
        
        # E. Execution
        trader.process_analysis(analysis_result, price, atr)

    # Final Summary
    logger.info("Daily Run Completed.")
    summary = trader.engine.get_portfolio_summary()
    logger.info(f"Portfolio Status: Cash=${summary['cash']:.2f}, Positions={len(summary['positions'])}")

if __name__ == "__main__":
    main()
