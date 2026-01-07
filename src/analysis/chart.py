import mplfinance as mpf
import pandas as pd
import io
from pathlib import Path

def generate_chart_image(df: pd.DataFrame, ticker: str, output_path: Path = None) -> bytes:
    """
    Generates a candlestick chart with technical indicators (MA, Bollinger Bands, Volume).
    Returns the image bytes (PNG).
    If output_path is provided, saves the file there as well.
    """
    if df.empty:
        return b""

    # Prepare style
    style = mpf.make_mpf_style(base_mpf_style='yahoo', rc={'font.size': 10})

    # Prepare added plots (Indicators)
    # We assume 'SMA_50', 'SMA_200', 'BBL_20_2.0', 'BBU_20_2.0' might exist if calculated,
    # but mplfinance can also calculate them on the fly if we want, but we already have them.
    # However, mplfinance `make_addplot` expects series with same index.
    
    addplots = []
    
    # Moving Averages
    if 'SMA_50' in df.columns:
        addplots.append(mpf.make_addplot(df['SMA_50'], color='orange', width=1.0))
    if 'SMA_200' in df.columns:
        addplots.append(mpf.make_addplot(df['SMA_200'], color='blue', width=1.0))
        
    # Bollinger Bands
    # pandas_ta names: BBL_length_std, BBU_length_std, BBM_length_std
    # usually BBL_20_2.0, BBU_20_2.0
    # Let's find columns starting with BBL and BBU
    bbl_col = next((c for c in df.columns if c.startswith('BBL')), None)
    bbu_col = next((c for c in df.columns if c.startswith('BBU')), None)
    
    if bbl_col and bbu_col:
        addplots.append(mpf.make_addplot(df[bbl_col], color='gray', linestyle='dotted', width=0.8))
        addplots.append(mpf.make_addplot(df[bbu_col], color='gray', linestyle='dotted', width=0.8))

    # Buffer to save image
    buf = io.BytesIO()
    
    # Plot
    # Slice to last 6 months equivalent (approx 126 trading days) for clarity if df is long
    plot_df = df.tail(126) if len(df) > 126 else df

    # Note: addplots must be sliced to match plot_df
    # But mpf.make_addplot receives the full series? No, it needs to match the data passed to plot.
    # So we should re-create addplots with sliced data.
    
    addplots_sliced = []
    if 'SMA_50' in df.columns:
        addplots_sliced.append(mpf.make_addplot(plot_df['SMA_50'].astype(float), color='orange', width=1.0))
    if 'SMA_200' in df.columns:
        addplots_sliced.append(mpf.make_addplot(plot_df['SMA_200'].astype(float), color='blue', width=1.0))
    if bbl_col and bbu_col:
        addplots_sliced.append(mpf.make_addplot(plot_df[bbl_col].astype(float), color='gray', linestyle='dotted', width=0.8))
        addplots_sliced.append(mpf.make_addplot(plot_df[bbu_col].astype(float), color='gray', linestyle='dotted', width=0.8))

    mpf.plot(
        plot_df,
        type='candle',
        style=style,
        volume=True,
        addplot=addplots_sliced,
        title=f"{ticker} - Daily Chart",
        savefig=buf,
        tight_layout=True,
        figratio=(12, 8),
        scale_width_adjustment=dict(volume=0.4, candle=1.0) # Adjust candles width
    )
    
    buf.seek(0)
    image_bytes = buf.read()
    
    if output_path:
        with open(output_path, "wb") as f:
            f.write(image_bytes)
            
    return image_bytes
