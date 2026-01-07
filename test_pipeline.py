import sys
import os

# Add root to path
sys.path.append(os.getcwd())

from src.data.loader import fetch_stock_data, get_nasdaq_100_tickers
from src.screening.indicators import calculate_technical_indicators
from src.analysis.chart import generate_chart_image
from src.data.news import fetch_latest_news, fetch_fundamental_summary
from src.analysis.llm import GeminiAnalyst

def test_pipeline():
    ticker = "NVDA"
    print(f"Testing pipeline for {ticker}...")
    
    # 1. Fetch Data
    df = fetch_stock_data(ticker)
    if df.empty:
        print("Failed to fetch data.")
        return

    # 2. Add Indicators
    df = calculate_technical_indicators(df)
    
    # 3. Generate Chart
    print("Generating Chart...")
    image_bytes = generate_chart_image(df, ticker, output_path="test_chart.png")
    print(f"Chart generated ({len(image_bytes)} bytes). Saved to test_chart.png")
    
    # 4. Fetch News/Fundamentals
    print("Fetching News...")
    news = fetch_latest_news(ticker)
    news_str = "\n".join([f"- {n['title']} ({n['source']})" for n in news])
    
    print("Fetching Fundamentals...")
    fundamentals = fetch_fundamental_summary(ticker)
    
    # 5. Analyze with Gemini
    print("Analyzing with Gemini...")
    analyst = GeminiAnalyst()
    
    technicals = {
        "RSI": df['RSI'].iloc[-1],
        "Price": df['Close'].iloc[-1]
    }
    
    result = analyst.analyze_stock(ticker, image_bytes, news_str, fundamentals, technicals)
    
    print("\n--- Analysis Result ---")
    print(result)

if __name__ == "__main__":
    test_pipeline()
