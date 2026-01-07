# Gemini-Sniper 🎯

AI-powered autonomous stock analysis and trading simulation system using Google Gemini 2.0 Flash/Pro.

## Overview
Gemini-Sniper screens US stocks, generates technical charts, and uses Gemini's multi-modal capabilities to analyze them alongside news and fundamentals. It executes trades in a "Paper Trading" environment to simulate performance.

## Features
- **Screener**: Filters NASDAQ 100 for high-volatility, liquid stocks.
- **Chart Analysis**: Uses `mplfinance` to generate candlestick charts with Indicators (MA, BB, Volume) for the AI to "see".
- **AI Analyst**: Gemini 2.0 Flash examines the chart image + text (News/Fundamentals) to give a BUY/SELL/HOLD rating.
- **Paper Trading**: Tracks a virtual $100k portfolio.
- **Serverless**: Designed to run via GitHub Actions (Free Tier).

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   Create a `.env` file:
   ```env
   GEMINI_API_KEY=your_google_api_key_here
   GEMINI_MODEL_NAME=gemini-2.0-flash-exp
   ```

3. **Run Locally**
   ```bash
   python main.py
   ```

## Testing
Run the comprehensive unit test suite:
```bash
python -m pytest tests/
```

## Deployment (GitHub Actions)
The project includes a workflow `.github/workflows/daily_run.yml` that runs daily at market close.
1. Push code to GitHub.
2. Go to **Settings > Secrets and variables > Actions**.
3. Add `GEMINI_API_KEY`.
4. The workflow will run automatically or can be triggered manually.
5. Check "Artifacts" in the Action run to see the logs and `paper_portfolio.json`.

## Project Structure
- `src/screening`: Logic for finding candidates.
- `src/analysis`: LLM and Charting modules.
- `src/execution`: Paper trading engine.
- `main.py`: Main entry point.
