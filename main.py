import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Import your existing functions (assume they're in the same file or imported)
# For this example, I'll include the key functions needed

# ==================== HELPER FUNCTIONS ====================

def validate_input(returns):
    if not isinstance(returns, pd.Series):
        raise ValueError("Input must be a pandas Series")
    if len(returns) == 0:
        raise ValueError("Input series is empty")

def _get_baseline_value(prices):
    if len(prices) > 0:
        return prices.iloc[0]
    return 1.0

def to_drawdown_series(returns):
    validate_input(returns)
    prices = (1 + returns).cumprod()
    
    if len(prices) == 0:
        return pd.Series([], dtype=float, index=returns.index)
    
    try:
        time_delta = prices.index.freq or pd.Timedelta(days=1)
    except Exception:
        time_delta = pd.Timedelta(days=1)
    
    phantom_date = prices.index[0] - time_delta
    baseline_value = _get_baseline_value(prices)
    
    extended_prices = prices.copy()
    extended_prices.loc[phantom_date] = baseline_value
    extended_prices = extended_prices.sort_index()
    
    dd = extended_prices / np.maximum.accumulate(extended_prices) - 1.0
    dd = dd.drop(phantom_date)
    
    return dd.replace([np.inf, -np.inf, -0], 0)

def identify_drawdown_periods(drawdowns, threshold=-0.001):
    in_drawdown = drawdowns < threshold
    drawdown_groups = (in_drawdown != in_drawdown.shift()).cumsum()
    
    periods = []
    
    for group_id in drawdown_groups[in_drawdown].unique():
        mask = (drawdown_groups == group_id) & in_drawdown
        dd_period = drawdowns[mask]
        
        if len(dd_period) == 0:
            continue
        
        start_date = dd_period.index[0]
        end_date = dd_period.index[-1]
        valley_date = dd_period.idxmin()
        max_dd = dd_period.min()
        duration_days = (end_date - start_date).days
        
        future_data = drawdowns[drawdowns.index > end_date]
        if len(future_data) > 0:
            recovered_mask = future_data >= -0.001
            if recovered_mask.any():
                recovery_date = future_data[recovered_mask].index[0]
                recovery_days = (recovery_date - valley_date).days
            else:
                recovery_date = None
                recovery_days = None
        else:
            recovery_date = None
            recovery_days = None
        
        periods.append({
            'Start': start_date,
            'Valley': valley_date,
            'End': end_date,
            'Recovery': recovery_date,
            'Max Drawdown': max_dd,
            'Duration (days)': duration_days,
            'Recovery Time (days)': recovery_days
        })
    
    return periods

def comprehensive_drawdown_stats(returns, symbol=None):
    drawdowns = to_drawdown_series(returns)
    dd_periods = identify_drawdown_periods(drawdowns)
    
    if len(dd_periods) == 0:
        return {
            'Symbol': symbol,
            'Number of Drawdowns': 0,
            'Max Drawdown (%)': 0,
            'Avg Drawdown (%)': 0,
            'Max DD Duration (days)': 0,
            'Avg DD Duration (days)': 0,
            'Max Recovery Time (days)': 0,
            'Avg Recovery Time (days)': 0,
            'Recovery Rate (%)': 0,
            'Current Drawdown (%)': drawdowns.iloc[-1] * 100,
            'Days in DD': (drawdowns < -0.001).sum(),
            'Time in DD (%)': ((drawdowns < -0.001).sum() / len(drawdowns)) * 100,
            'Drawdown Periods': [],
            'Drawdown Series': drawdowns
        }
    
    max_dds = [p['Max Drawdown'] for p in dd_periods]
    durations = [p['Duration (days)'] for p in dd_periods]
    recovery_times = [p['Recovery Time (days)'] for p in dd_periods if p['Recovery Time (days)'] is not None]
    
    recovered = sum(1 for p in dd_periods if p['Recovery'] is not None)
    recovery_rate = (recovered / len(dd_periods)) * 100 if dd_periods else 0
    
    worst_dd_idx = np.argmin(max_dds)
    worst_dd_period = dd_periods[worst_dd_idx]
    
    stats = {
        'Symbol': symbol,
        'Number of Drawdowns': len(dd_periods),
        'Max Drawdown (%)': min(max_dds) * 100,
        'Avg Drawdown (%)': np.mean(max_dds) * 100,
        'Max DD Duration (days)': max(durations),
        'Avg DD Duration (days)': np.mean(durations),
        'Max Recovery Time (days)': max(recovery_times) if recovery_times else None,
        'Avg Recovery Time (days)': np.mean(recovery_times) if recovery_times else None,
        'Recovery Rate (%)': recovery_rate,
        'Current Drawdown (%)': drawdowns.iloc[-1] * 100,
        'Days in DD': (drawdowns < -0.001).sum(),
        'Time in DD (%)': ((drawdowns < -0.001).sum() / len(drawdowns)) * 100,
        'Worst DD Start': worst_dd_period['Start'],
        'Worst DD Valley': worst_dd_period['Valley'],
        'Worst DD End': worst_dd_period['End'],
        'Worst DD Recovery': worst_dd_period['Recovery'],
        'Drawdown Periods': dd_periods,
        'Drawdown Series': drawdowns
    }
    
    return stats

# ==================== PAGE CONFIG ====================

st.set_page_config(
    page_title="Drawdown Analysis",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== DARK MODE STYLING ====================

st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    
    .stMetric {
        background-color: #1a1d26;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #262a33;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #1a1d26 0%, #262a33 100%);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #2d323e;
        margin: 10px 0;
    }
    
    h1, h2, h3 {
        color: #ffffff;
        font-weight: 600;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #1a1d26;
        border-radius: 10px;
        padding: 5px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #8b92a8;
        border-radius: 8px;
        padding: 10px 20px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #262a33;
        color: #ffffff;
    }
    
    div[data-testid="stSidebarNav"] {
        background-color: #0e1117;
    }
    
    .plot-container {
        background-color: #1a1d26;
        border-radius: 12px;
        padding: 15px;
        border: 1px solid #262a33;
    }
</style>
""", unsafe_allow_html=True)

# ==================== DATA LOADING ====================

@st.cache_data(ttl=3600)
def load_stock_data(symbol, period="2y"):
    """Load stock data from yfinance"""
    try:
        data = yf.download(symbol, period=period, progress=False)
        if len(data) > 0:
            return data['Adj Close']
        return None
    except:
        return None

@st.cache_data(ttl=3600)
def analyze_stock(symbol, period="2y"):
    """Analyze a single stock"""
    prices = load_stock_data(symbol, period)
    if prices is None or len(prices) < 10:
        return None
    
    returns = prices.pct_change().dropna()
    stats = comprehensive_drawdown_stats(returns, symbol=symbol)
    stats['Prices'] = prices
    stats['Returns'] = returns
    
    return stats

# ==================== PLOTTING FUNCTIONS ====================

def create_drawdown_chart(stats):
    """Create interactive drawdown chart"""
    drawdowns = stats['Drawdown Series']
    prices = stats['Prices']
    
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.6, 0.4],
        subplot_titles=('Price History', 'Drawdown'),
        vertical_spacing=0.1
    )
    
    # Price chart
    fig.add_trace(
        go.Scatter(
            x=prices.index,
            y=prices.values,
            name='Price',
            line=dict(color='#00d4ff', width=2),
            fill='tonexty',
            fillcolor='rgba(0, 212, 255, 0.1)'
        ),
        row=1, col=1
    )
    
    # Drawdown chart
    fig.add_trace(
        go.Scatter(
            x=drawdowns.index,
            y=drawdowns.values * 100,
            name='Drawdown',
            line=dict(color='#ff4757', width=2),
            fill='tozeroy',
            fillcolor='rgba(255, 71, 87, 0.3)'
        ),
        row=2, col=1
    )
    
    # Mark drawdown periods
    for period in stats['Drawdown Periods'][:5]:  # Top 5 worst
        fig.add_vrect(
            x0=period['Start'],
            x1=period['End'],
            fillcolor='rgba(255, 71, 87, 0.1)',
            layer='below',
            line_width=0,
            row=2, col=1
        )
    
    fig.update_layout(
        height=700,
        showlegend=False,
        hovermode='x unified',
        plot_bgcolor='#0e1117',
        paper_bgcolor='#1a1d26',
        font=dict(color='#8b92a8'),
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    fig.update_xaxes(
        gridcolor='#262a33',
        showgrid=True,
        zeroline=False
    )
    
    fig.update_yaxes(
        gridcolor='#262a33',
        showgrid=True,
        zeroline=True,
        zerolinecolor='#3d4452'
    )
    
    return fig

def create_recovery_chart(stats):
    """Create recovery time distribution"""
    periods = stats['Drawdown Periods']
    
    if not periods:
        return None
    
    recovery_times = [p['Recovery Time (days)'] for p in periods if p['Recovery Time (days)'] is not None]
    max_dds = [p['Max Drawdown'] * 100 for p in periods if p['Recovery Time (days)'] is not None]
    
    if not recovery_times:
        return None
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=max_dds,
        y=recovery_times,
        mode='markers',
        marker=dict(
            size=12,
            color=max_dds,
            colorscale='Reds',
            showscale=True,
            line=dict(color='white', width=1),
            colorbar=dict(title="Max DD %")
        ),
        text=[f"DD: {dd:.1f}%<br>Recovery: {rt} days" for dd, rt in zip(max_dds, recovery_times)],
        hovertemplate='%{text}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Drawdown Magnitude vs Recovery Time",
        xaxis_title="Max Drawdown (%)",
        yaxis_title="Recovery Time (days)",
        height=400,
        plot_bgcolor='#0e1117',
        paper_bgcolor='#1a1d26',
        font=dict(color='#8b92a8'),
        hovermode='closest'
    )
    
    fig.update_xaxes(gridcolor='#262a33', showgrid=True)
    fig.update_yaxes(gridcolor='#262a33', showgrid=True)
    
    return fig

def create_drawdown_distribution(stats):
    """Create drawdown distribution histogram"""
    periods = stats['Drawdown Periods']
    
    if not periods:
        return None
    
    max_dds = [p['Max Drawdown'] * 100 for p in periods]
    
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=max_dds,
        nbinsx=20,
        marker=dict(
            color='#ff4757',
            line=dict(color='white', width=1)
        ),
        name='Frequency'
    ))
    
    fig.update_layout(
        title="Distribution of Drawdowns",
        xaxis_title="Max Drawdown (%)",
        yaxis_title="Frequency",
        height=400,
        plot_bgcolor='#0e1117',
        paper_bgcolor='#1a1d26',
        font=dict(color='#8b92a8'),
        showlegend=False
    )
    
    fig.update_xaxes(gridcolor='#262a33', showgrid=True)
    fig.update_yaxes(gridcolor='#262a33', showgrid=True)
    
    return fig

# ==================== MAIN APP ====================

def main():
    # Header
    st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>📉 Drawdown Analysis</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8b92a8; margin-top: 5px;'>Professional risk analysis for informed investment decisions</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.markdown("### Configuration")
        
        symbol = st.text_input("Stock Symbol", value="AAPL", help="Enter ticker symbol (e.g., AAPL, MSFT, GOOGL)")
        
        period = st.selectbox(
            "Analysis Period",
            options=["1y", "2y", "5y", "max"],
            index=1,
            help="Historical data period"
        )
        
        analyze_button = st.button("🔍 Analyze", type="primary", use_container_width=True)
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        This tool analyzes historical drawdowns to help you understand:
        - Maximum losses experienced
        - Recovery patterns
        - Time spent underwater
        - Risk characteristics
        """)
        
        st.markdown("---")
        st.markdown("### Quick Links")
        popular_stocks = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "SPY", "QQQ"]
        for stock in popular_stocks:
            if st.button(stock, key=f"quick_{stock}", use_container_width=True):
                st.session_state.symbol = stock
                st.rerun()
    
    # Initialize session state
    if 'symbol' in st.session_state:
        symbol = st.session_state.symbol
    
    if analyze_button or 'last_analysis' in st.session_state:
        with st.spinner(f"Analyzing {symbol.upper()}..."):
            stats = analyze_stock(symbol.upper(), period)
            
            if stats is None:
                st.error(f"❌ Unable to load data for {symbol.upper()}. Please check the symbol and try again.")
                return
            
            st.session_state.last_analysis = stats
            
            # Key Metrics Row
            st.markdown("### Key Metrics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Max Drawdown",
                    f"{stats['Max Drawdown (%)']:.2f}%",
                    delta=None,
                    help="Largest peak-to-trough decline"
                )
            
            with col2:
                st.metric(
                    "Current Drawdown",
                    f"{stats['Current Drawdown (%)']:.2f}%",
                    delta=f"{stats['Current Drawdown (%)'] - stats['Max Drawdown (%)']:.2f}%",
                    help="Current distance from peak"
                )
            
            with col3:
                st.metric(
                    "Number of Drawdowns",
                    f"{stats['Number of Drawdowns']}",
                    help="Total drawdown events identified"
                )
            
            with col4:
                st.metric(
                    "Recovery Rate",
                    f"{stats['Recovery Rate (%)']:.1f}%",
                    help="Percentage of drawdowns recovered"
                )
            
            st.markdown("---")
            
            # Main Chart
            st.markdown("### Price & Drawdown Analysis")
            fig = create_drawdown_chart(stats)
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabs for detailed analysis
            tab1, tab2, tab3 = st.tabs(["📊 Statistics", "📋 Drawdown Periods", "📈 Recovery Analysis"])
            
            with tab1:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### Duration Metrics")
                    st.metric("Max DD Duration", f"{stats['Max DD Duration (days)']} days")
                    st.metric("Avg DD Duration", f"{stats['Avg DD Duration (days)']:.1f} days")
                    st.metric("Days in Drawdown", f"{stats['Days in DD']} days")
                    st.metric("Time in Drawdown", f"{stats['Time in DD (%)']:.1f}%")
                
                with col2:
                    st.markdown("#### Recovery Metrics")
                    if stats['Max Recovery Time (days)']:
                        st.metric("Max Recovery Time", f"{stats['Max Recovery Time (days)']} days")
                        st.metric("Avg Recovery Time", f"{stats['Avg Recovery Time (days)']:.1f} days")
                    else:
                        st.info("No completed recoveries in dataset")
                    
                    st.metric("Avg Drawdown", f"{stats['Avg Drawdown (%)']:.2f}%")
                
                # Distribution chart
                st.markdown("---")
                dist_fig = create_drawdown_distribution(stats)
                if dist_fig:
                    st.plotly_chart(dist_fig, use_container_width=True)
            
            with tab2:
                st.markdown("#### Top 10 Drawdown Events")
                
                if stats['Drawdown Periods']:
                    periods_data = []
                    for p in stats['Drawdown Periods']:
                        periods_data.append({
                            'Start': p['Start'].strftime('%Y-%m-%d'),
                            'Valley': p['Valley'].strftime('%Y-%m-%d'),
                            'End': p['End'].strftime('%Y-%m-%d'),
                            'Recovery': p['Recovery'].strftime('%Y-%m-%d') if p['Recovery'] else 'Ongoing',
                            'Max DD (%)': f"{p['Max Drawdown'] * 100:.2f}",
                            'Duration (days)': p['Duration (days)'],
                            'Recovery (days)': p['Recovery Time (days)'] if p['Recovery Time (days)'] else 'N/A'
                        })
                    
                    df = pd.DataFrame(periods_data)
                    df = df.sort_values('Max DD (%)', key=lambda x: x.astype(float)).head(10)
                    
                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No significant drawdown periods detected")
            
            with tab3:
                st.markdown("#### Recovery Analysis")
                
                recovery_fig = create_recovery_chart(stats)
                if recovery_fig:
                    st.plotly_chart(recovery_fig, use_container_width=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Worst Drawdown Details**")
                        st.write(f"**Start:** {stats['Worst DD Start'].strftime('%Y-%m-%d')}")
                        st.write(f"**Valley:** {stats['Worst DD Valley'].strftime('%Y-%m-%d')}")
                        st.write(f"**End:** {stats['Worst DD End'].strftime('%Y-%m-%d')}")
                        if stats['Worst DD Recovery']:
                            st.write(f"**Recovered:** {stats['Worst DD Recovery'].strftime('%Y-%m-%d')}")
                            recovery_time = (stats['Worst DD Recovery'] - stats['Worst DD Valley']).days
                            st.write(f"**Recovery Time:** {recovery_time} days")
                        else:
                            st.write("**Status:** Still in drawdown")
                    
                    with col2:
                        st.markdown("**Risk Assessment**")
                        max_dd = abs(stats['Max Drawdown (%)'])
                        
                        if max_dd < 10:
                            risk_level = "🟢 Low"
                            risk_desc = "Low historical volatility"
                        elif max_dd < 20:
                            risk_level = "🟡 Moderate"
                            risk_desc = "Moderate drawdown risk"
                        elif max_dd < 40:
                            risk_level = "🟠 High"
                            risk_desc = "Significant drawdown risk"
                        else:
                            risk_level = "🔴 Extreme"
                            risk_desc = "Extreme drawdown risk"
                        
                        st.metric("Risk Level", risk_level)
                        st.write(risk_desc)
                        st.write(f"Average recovery time: {stats['Avg Recovery Time (days)']:.0f} days" if stats['Avg Recovery Time (days)'] else "Recovery data incomplete")
                else:
                    st.info("Insufficient recovery data for analysis")
    
    else:
        # Welcome screen
        st.markdown("""
        <div style='text-align: center; padding: 100px 20px;'>
            <h2 style='color: #8b92a8;'>Welcome to Drawdown Analysis</h2>
            <p style='color: #5a6270; font-size: 18px;'>Enter a stock symbol in the sidebar to begin</p>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
