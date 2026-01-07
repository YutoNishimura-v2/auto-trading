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
            self.model = genai.GenerativeModel(Config.GEMINI_MODEL_NAME)
        else:
            logger.warning("GEMINI_API_KEY not found. Running in MOCK mode.")
            self.model = None

    def analyze_stock(self, ticker: str, chart_image: bytes, news_summary: str, fundamentals: str, technicals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes a stock using Gemini 1.5/2.0 Pro/Flash (Multi-modal).
        
        Args:
            ticker: Stock Ticker
            chart_image: Bytes of the chart image (PNG)
            news_summary: Text summary of news
            fundamentals: Text summary of fundamentals
            technicals: Dict of technical indicators
        
        Returns:
            JSON Dict with analysis results.
        """
        
        system_instruction = f"""
        You are a Wall Street Hedge Fund Manager with 20 years of experience.
        Your goal is to analyze the provided US Stock data and decide whether to Buy, Sell, or Hold.
        
        Input Data:
        1. **Technical Chart**: A generic daily candle stick chart with MA and Bollinger Bands.
        2. **News & Fundamentals**: Recent headlines and earnings context.
        3. **Technical Metrics**: {technicals}
        
        Task:
        1. Analyze the Chart pattern (Trend, Support/Res, Patterns like Cup & Handle, Double Bottom).
        2. Analyze the News sentiment (Is it a specific catalyst or noise?).
        3. Combine both to form a conviction.
        
        Constraints:
        - If the chart looks bullish but news is bad, be cautious (HOLD).
        - If the chart is broken (downtrend) but news is good, wait for base (HOLD/WATCH).
        - Only 'STRONG_BUY' if both Technicals and Fundamentals align perfectly.
        
        Output Format (JSON Only):
        {{
            "ticker": "{ticker}",
            "action": "STRONG_BUY" | "BUY" | "HOLD" | "SELL",
            "confidence": <0-100 integer>,
            "reasoning": "<Concise analysis in 3 bullet points>",
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
                f"\n\nHere are the News & Fundamentals:\n{news_summary}\n{fundamentals}\n",
                "Please provide your analysis in JSON format."
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
            "action": "HOLD",
            "confidence": 50,
            "reasoning": f"Mock Analysis (API Key missing or Error: {error}). Chart shows consolidation.",
            "stop_loss_suggestion": 0.0,
            "take_profit_suggestion": 0.0
        }
