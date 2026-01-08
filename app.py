import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from main import run_session
from src.execution.manager import TradeManager
import sys
import os

# Fix path
sys.path.append(os.getcwd())

st.set_page_config(
    page_title="Gemini-Sniper Terminal",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Bloomberg Terminal Look
st.markdown("""
<style>
    .stApp {
        background-color: #000000;
        color: #00FF00;
        font-family: 'Courier New', Courier, monospace;
    }
    .metric-card {
        background-color: #111;
        padding: 10px;
        border: 1px solid #333;
        margin-bottom: 10px;
    }
    .tape-container {
        font-size: 14px;
        color: #00FF00;
        height: 400px;
        overflow-y: auto;
        background-color: #050505;
        padding: 10px;
        border: 1px solid #333;
        font-family: 'Courier New', Courier, monospace;
    }
    .tape-row {
        border-bottom: 1px solid #111;
        padding: 2px 0;
    }
    .stButton>button {
        background-color: #333;
        color: #00FF00;
        border: 1px solid #00FF00;
    }
    .stButton>button:hover {
        background-color: #00FF00;
        color: #000;
    }
    /* Hide Streamlit Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

def main():
    st.title("🦅 GEMINI-SNIPER TERMINAL v2.1")

    # Initialize Manager for manual actions
    trader = TradeManager()

    # --- SIDEBAR ---
    with st.sidebar:
        st.header("SYSTEM CONTROL")
        
        mode = st.radio("MODE", ["REAL-TIME", "SIMULATION"])
        
        sim_date = None
        if mode == "SIMULATION":
            sim_date = st.date_input("Sim Date", datetime.now() - timedelta(days=1))
            st.warning(f"Replaying Market Data for {sim_date}")
        
        st.divider()
        
        risk_per_trade = st.slider("RISK %", 0.5, 5.0, 2.0)
        
        if st.button("INITIATE SESSION", type="primary"):
            st.session_state['running'] = True
            st.session_state['logs'] = []
            st.session_state['trades'] = []
            st.session_state['trades_history'] = [] # Clear Tape History
            
        st.divider()
        if st.button("EMERGENCY LIQUIDATE"):
            trader.liquidate_all()
            st.error("ALL POSITIONS LIQUIDATED")
            
        st.divider()
        st.subheader("LAST ANALYSIS")
        analysis_placeholder = st.empty()

    # --- MAIN LAYOUT ---
    # Col 1: Tape (Main Focus - 60%)
    # Col 2: Watchlist & Portfolio (40%)
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("📼 LIVE TAPE (EXECUTIONS)")
        tape_placeholder = st.empty()
        
    with col2:
        # Top: Clock & Portfolio
        st.subheader("⏰ MARKET CLOCK")
        clock_placeholder = st.empty()
        
        st.subheader("💼 PORTFOLIO")
        metrics_placeholder = st.empty()
        
        # Middle: Watchlist / Positions
        st.subheader("🔭 WATCHLIST")
        watchlist_placeholder = st.empty()

    # --- SYSTEM CONSOLE (Bottom) ---
    with st.expander("SYSTEM CONSOLE", expanded=False):
        console_placeholder = st.empty()

    # --- SESSION LOGIC ---
    if 'running' in st.session_state and st.session_state['running']:
        
        # Convert date to datetime if sim
        sim_dt = datetime.combine(sim_date, datetime.min.time()) if sim_date else None
        
        step_count = 0
        if 'trades_history' not in st.session_state:
            st.session_state['trades_history'] = []
        
        # Initial Render of Tape
        tape_placeholder.markdown(
            f'<div class="tape-container">{"".join(st.session_state["trades_history"])}</div>', 
            unsafe_allow_html=True
        )
        
        for step_type, data in run_session(sim_dt):
            step_count += 1
            
            # Update Console (Logs)
            if step_type == "STATUS":
                console_placeholder.text(f"> {data}")
            
            # Update Analysis View (Sidebar)
            elif step_type == "ANALYSIS":
                # Update Clock
                if 'time' in data:
                    current_time = data['time']
                    # Convert UTC to US/Eastern for display
                    import pytz
                    utc = pytz.utc
                    eastern = pytz.timezone('US/Eastern')
                    
                    if current_time.tzinfo is None:
                        current_time = utc.localize(current_time)
                    
                    et_time = current_time.astimezone(eastern)
                    clock_placeholder.metric("MARKET TIME (ET)", et_time.strftime("%H:%M:%S"))

                with analysis_placeholder.container():
                    if data.get('chart'):
                        try:
                            st.image(data['chart'], width='stretch')
                        except Exception:
                            st.error("Chart Image Corrupted")
                    else:
                        st.warning("Chart Unavailable")
                        
                    if 'result' in data:
                        res = data['result']
                        st.markdown(f"""
                        **{data['ticker']}**  
                        {res['action']} ({res['confidence']}%)  
                        """)
            
            # Update Portfolio Metrics
            elif step_type == "PORTFOLIO_UPDATE":
                account = data
                with metrics_placeholder.container():
                    c1, c2, c3 = st.columns(3)
                    c1.metric("EQUITY", f"${account['equity']:,.2f}")
                    c2.metric("CASH", f"${account['cash']:,.2f}")
                    c3.metric("BP", f"${account['buying_power']:,.2f}")

                # Update Watchlist (Positions)
                positions = trader.broker.get_positions()
                if positions:
                    # Visual Trade Monitor (Cards)
                    cards_html = ""
                    for pos in positions:
                        symbol = pos['symbol']
                        entry = pos['avg_entry_price']
                        current = pos['current_price']
                        pnl = pos['unrealized_pl']
                        pnl_pc = pos['unrealized_plpc']
                        tp = pos.get('tp', 0)
                        sl = pos.get('sl', 0)
                        
                        # Calculate Progress
                        # Range: SL (0%) -> TP (100%)
                        # If no TP/SL, default to centered
                        progress = 50
                        if tp and sl and tp != sl:
                            total_range = tp - sl
                            dist_from_sl = current - sl
                            progress = (dist_from_sl / total_range) * 100
                            progress = max(0, min(100, progress)) # Clamp
                        
                        pnl_color = "#00FF00" if pnl >= 0 else "#FF0000"
                        
                        cards_html += f"""
                        <div style="background-color: #111; padding: 10px; border-radius: 5px; margin-bottom: 10px; border: 1px solid #333;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                <span style="font-weight: bold; font-size: 1.1em;">{symbol}</span>
                                <span style="color: {pnl_color}; font-weight: bold;">${pnl:,.2f} ({pnl_pc:.2f}%)</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 0.8em; color: #888;">
                                <span>Entry: ${entry:.2f}</span>
                                <span>Current: ${current:.2f}</span>
                            </div>
                            <!-- Progress Bar -->
                            <div style="margin-top: 8px; position: relative; height: 20px; background-color: #333; border-radius: 10px;">
                                <!-- SL Marker -->
                                <div style="position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background-color: #FF0000; border-radius: 2px;" title="SL: {sl}"></div>
                                <!-- TP Marker -->
                                <div style="position: absolute; right: 0; top: 0; bottom: 0; width: 4px; background-color: #00FF00; border-radius: 2px;" title="TP: {tp}"></div>
                                <!-- Current Price Indicator -->
                                <div style="position: absolute; left: {progress}%; top: -5px; width: 0; height: 0; 
                                            border-left: 6px solid transparent; border-right: 6px solid transparent; 
                                            border-top: 8px solid #FFF; transform: translateX(-6px);"></div>
                                <div style="position: absolute; left: {progress}%; top: 0; bottom: 0; width: 2px; background-color: #FFF; transform: translateX(-1px);"></div>
                            </div>
                            <div style="display: flex; justify-content: space-between; font-size: 0.7em; color: #666; margin-top: 2px;">
                                <span>SL: ${sl:.2f}</span>
                                <span>TP: ${tp:.2f}</span>
                            </div>
                        </div>
                        """
                    
                    # Update Placeholder ONCE with all cards
                    watchlist_placeholder.markdown(cards_html, unsafe_allow_html=True)
                    
                else:
                    watchlist_placeholder.info("NO ACTIVE POSITIONS")

            # Update Tape
            elif step_type == "TRADE_ALERT":
                order = data
                
                # Use order timestamp if available, else now
                ts_str = order.get('filled_at', datetime.now().isoformat())
                try:
                    # Try parsing isoformat
                    ts_dt = datetime.fromisoformat(ts_str)
                    # Convert to ET for display if it's aware, or assume it's the right time
                    # For simplicity, just show HH:MM:SS
                    timestamp = ts_dt.strftime('%H:%M:%S')
                except:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                
                # Handle Rejections or Missing Side
                side = order.get('side', 'UNKNOWN').upper()
                status = order.get('status', 'unknown')
                symbol = order.get('symbol', 'N/A')
                qty = order.get('qty', 0)
                price = order.get('filled_avg_price', 0.0)
                reason = order.get('reason', '')
                
                if status == 'rejected':
                    color = "#FF0000" # Red for rejection
                    row_html = f'<div class="tape-row" style="color: {color};"><span style="width: 80px; display: inline-block;">{timestamp}</span><span style="width: 60px; display: inline-block; font-weight: bold;">{symbol}</span><span style="width: 50px; display: inline-block;">REJECT</span><span style="width: 200px; display: inline-block;">{reason}</span></div>'
                else:
                    color = "#00FF00" if side == 'BUY' else "#FF5555"
                    row_html = f'<div class="tape-row" style="color: {color};"><span style="width: 80px; display: inline-block;">{timestamp}</span><span style="width: 60px; display: inline-block; font-weight: bold;">{symbol}</span><span style="width: 50px; display: inline-block;">{side}</span><span style="width: 60px; display: inline-block;">{qty}</span><span style="width: 80px; display: inline-block;">@ {price:.2f}</span><span>{reason}</span></div>'
                
                st.session_state['trades_history'].insert(0, row_html)
                # Keep last 50
                st.session_state['trades_history'] = st.session_state['trades_history'][:50]
                
                tape_placeholder.markdown(
                    f'<div class="tape-container">{"".join(st.session_state["trades_history"])}</div>', 
                    unsafe_allow_html=True
                )
                st.toast(f"EXECUTED: {order['symbol']}", icon="⚡")
            
            elif step_type == "EOD_DECISION":
                decision = data
                st.toast(f"EOD: {decision['ticker']} -> {decision['action']}")

            elif step_type == "ERROR":
                st.error(data)
                
            # Speed control for simulation
            if mode == "SIMULATION":
                time.sleep(0.01) # Ultra Fast replay
            else:
                time.sleep(0.5)

        st.session_state['running'] = False
        st.success("SESSION COMPLETED")

if __name__ == "__main__":
    main()
