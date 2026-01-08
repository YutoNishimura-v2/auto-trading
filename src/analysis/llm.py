import os
import json
import logging
import google.generativeai as genai
from typing import Dict, Optional, Any
from src.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiAnalyst:
    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Enable Google Search Tool
            tools = [
                {"google_search_retrieval": {
                    "dynamic_retrieval_config": {
                        "mode": "dynamic",
                        "dynamic_threshold": 0.3,
                    }
                }}
            ]
            self.model = genai.GenerativeModel(Config.GEMINI_MODEL_NAME, tools=tools)
        else:
            logger.warning("GEMINI_API_KEY not found. Running in MOCK mode.")
            self.model = None

    def analyze_stock(self, ticker: str, chart_image: bytes, technicals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes a stock using Gemini 2.0 with Google Search Grounding.
        
        Args:
            ticker: Stock Ticker
            chart_image: Bytes of the chart image (PNG)
            technicals: Dict of technical indicators
        
        Returns:
            JSON Dict with analysis results.
        """
        
        system_instruction = f"""
        You are a Wall Street Day Trader and Hedge Fund Manager.
        Your goal is to analyze the provided US Stock data and decide whether to Buy, Sell, or Hold for a DAY TRADE (Intraday).
        
        Input Data:
        1. **Technical Chart**: A daily candle stick chart.
        2. **Technical Metrics**: {technicals}
        
        Task:
        1. **SEARCH**: Use Google Search to find the LATEST news (today/yesterday) explaining why {ticker} is moving. Look for Earnings, FDA approvals, Analyst upgrades, or Macro news.
        2. **Analyze Chart**: Look for patterns.
        3. **Decide Strategy**:
            - **Action**: BUY/SELL/HOLD.
            - **Time Horizon**: 
                - "DAY": Close before market close (Intraday).
                - "SWING": Hold overnight (Multi-day).
            - **Levels**: Set realistic Stop Loss and Take Profit based on ATR or Support/Resistance.
        
        Output Format (JSON Only):
        {{
            "ticker": "{ticker}",
            "action": "STRONG_BUY" | "BUY" | "HOLD" | "SELL",
            "time_horizon": "DAY" | "SWING",
            "confidence": <0-100 integer>,
            "reasoning": "<Concise analysis. Cite news. Explain why DAY or SWING.>",
            "stop_loss_suggestion": <float price>,
            "take_profit_suggestion": <float price>
        }}
        """

        if not self.model: # Mock Mode
            return self._mock_response(ticker)

        try:
            # Construct the prompt parts
            prompt_parts = [
                system_instruction,
                "Here is the chart image:",
                {"mime_type": "image/png", "data": chart_image},
                f"Find out why {ticker} is moving today and provide your trading decision.",
            ]
            
            # Generate response
            response = self.model.generate_content(
                prompt_parts,
                generation_config={"response_mime_type": "application/json"}
            )
            
            # Parse JSON
            try:
                result = json.loads(response.text)
                return result
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from Gemini: {response.text}")
                return self._mock_response(ticker, error="JSON Parse Error")
                
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            return self._mock_response(ticker, error=str(e))

    def _mock_response(self, ticker: str, error: str = "") -> Dict[str, Any]:
        """Returns a dummy response for testing/offline mode."""
        return {
            "ticker": ticker,
            "action": "BUY", # Force BUY for demonstration
            "time_horizon": "DAY",
            "confidence": 90,
            "reasoning": f"Mock Analysis (API Key missing or Error: {error}). Chart shows strong breakout. Day Trade setup.",
            "take_profit_suggestion": 0.0
        }

    def reevaluate_position(self, ticker: str, entry_price: float, current_price: float, chart_image: bytes) -> Dict[str, Any]:
        """
        Re-evaluates an open position at End of Day.
        Decides whether to HOLD OVERNIGHT (Swing) or CLOSE NOW (Day Trade).
        """
        pnl_percent = ((current_price - entry_price) / entry_price) * 100
        
        system_instruction = f"""
        You are a Senior Portfolio Manager.
        It is Market Close (End of Day). You have an open position in {ticker}.
        
        Status:
        - Entry: ${entry_price:.2f}
        - Current: ${current_price:.2f}
        - P&L: {pnl_percent:.2f}%
        
        Task:
        Analyze the chart and news to decide:
        1. **CLOSE_NOW**: If the trend is fading, or if it was a pure day trade and risk is high.
        2. **HOLD_OVERNIGHT**: If the trend is strong and likely to gap up tomorrow.
        
        Output Format (JSON Only):
        {{
            "ticker": "{ticker}",
            "action": "CLOSE_NOW" | "HOLD_OVERNIGHT",
            "confidence": <0-100 integer>,
            "reasoning": "<Why hold or close? Cite chart pattern or news.>"
        }}
        """
        
        if not self.model: # Mock Mode
            return {
                "ticker": ticker,
                "action": "HOLD_OVERNIGHT" if pnl_percent > 0 else "CLOSE_NOW",
                "confidence": 80,
                "reasoning": "Mock EOD Review. Holding winners, cutting losers."
            }

        try:
            prompt_parts = [
                system_instruction,
                "Here is the EOD chart:",
                {"mime_type": "image/png", "data": chart_image},
                "Decide: Hold Overnight or Close Now?"
            ]
            
            response = self.model.generate_content(
                prompt_parts,
                generation_config={"response_mime_type": "application/json"}
            )
            
            return json.loads(response.text)
            
        except Exception as e:
            logger.error(f"Gemini EOD Error: {e}")
            return {
                "ticker": ticker,
                "action": "HOLD_OVERNIGHT", # Default to hold if error
                "confidence": 0,
                "reasoning": f"Error during analysis: {e}"
            }
