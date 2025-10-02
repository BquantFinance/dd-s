import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import yfinance as yf
import requests
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

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

# ==================== S&P 500 FUNCTIONS ====================

@st.cache_data(ttl=86400)
def get_sp500_symbols():
    """Scrape S&P 500 symbols from Wikipedia."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    tables = pd.read_html(response.text)
    sp500_table = tables[0]
    symbols = sp500_table['Symbol'].tolist()
    symbols = [s.replace('.', '-') for s in symbols]
    
    return symbols

@st.cache_data(ttl=3600)
def download_sp500_data(symbols, period="2y"):
    """Download historical data for S&P 500 stocks."""
    data = yf.download(symbols, period=period, progress=False, group_by='ticker', threads=True)
    
    prices = pd.DataFrame()
    for symbol in symbols:
        try:
            if len(symbols) == 1:
                prices[symbol] = data['Adj Close']
            else:
                prices[symbol] = data[symbol]['Adj Close']
        except (KeyError, TypeError):
            continue
    
    prices = prices.dropna(axis=1, thresh=len(prices) * 0.8)
    return prices

@st.cache_data(ttl=3600)
def analyze_sp500(period="2y"):
    """Analyze all S&P 500 stocks."""
    symbols = get_sp500_symbols()
    prices = download_sp500_data(symbols, period)
    
    summary_results = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, symbol in enumerate(prices.columns):
        returns = prices[symbol].pct_change().dropna()
        
        if len(returns) < 10:
            continue
        
        stats = comprehensive_drawdown_stats(returns, symbol=symbol)
        summary_dict = {k: v for k, v in stats.items() if k not in ['Drawdown Periods', 'Drawdown Series']}
        summary_results.append(summary_dict)
        
        progress_bar.progress((i + 1) / len(prices.columns))
        status_text.text(f"Analyzing {i + 1}/{len(prices.columns)} stocks...")
    
    progress_bar.empty()
    status_text.empty()
    
    summary_df = pd.DataFrame(summary_results)
    return summary_df, prices

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

# ==================== PAGE CONFIG ====================

st.set_page_config(
    page_title="S&P 500 Drawdown Analysis",
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
    
    for period in stats['Drawdown Periods'][:5]:
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
    
    fig.update_xaxes(gridcolor='#262a33', showgrid=True, zeroline=False)
    fig.update_yaxes(gridcolor='#262a33', showgrid=True, zeroline=True, zerolinecolor='#3d4452')
    
    return fig

def create_sp500_distribution(summary_df):
    """Create distribution of max drawdowns across S&P 500"""
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=summary_df['Max Drawdown (%)'],
        nbinsx=30,
        marker=dict(
            color='#ff4757',
            line=dict(color='white', width=1)
        ),
        name='Frequency'
    ))
    
    fig.update_layout(
        title="Distribution of Max Drawdowns - S&P 500",
        xaxis_title="Max Drawdown (%)",
        yaxis_title="Number of Stocks",
        height=400,
        plot_bgcolor='#0e1117',
        paper_bgcolor='#1a1d26',
        font=dict(color='#8b92a8'),
        showlegend=False
    )
    
    fig.update_xaxes(gridcolor='#262a33', showgrid=True)
    fig.update_yaxes(gridcolor='#262a33', showgrid=True)
    
    return fig

def create_scatter_matrix(summary_df):
    """Create scatter plot of drawdown metrics"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=summary_df['Max Drawdown (%)'],
        y=summary_df['Avg Recovery Time (days)'],
        mode='markers',
        marker=dict(
            size=8,
            color=summary_df['Current Drawdown (%)'],
            colorscale='RdYlGn_r',
            showscale=True,
            line=dict(color='white', width=0.5),
            colorbar=dict(title="Current DD %")
        ),
        text=summary_df['Symbol'],
        hovertemplate='<b>%{text}</b><br>Max DD: %{x:.1f}%<br>Avg Recovery: %{y:.0f} days<extra></extra>'
    ))
    
    fig.update_layout(
        title="Max Drawdown vs Average Recovery Time",
        xaxis_title="Max Drawdown (%)",
        yaxis_title="Average Recovery Time (days)",
        height=500,
        plot_bgcolor='#0e1117',
        paper_bgcolor='#1a1d26',
        font=dict(color='#8b92a8'),
        hovermode='closest'
    )
    
    fig.update_xaxes(gridcolor='#262a33', showgrid=True)
    fig.update_yaxes(gridcolor='#262a33', showgrid=True)
    
    return fig

def create_top_performers_chart(summary_df, metric='Max Drawdown (%)', n=20, ascending=True):
    """Create bar chart for top/bottom performers"""
    sorted_df = summary_df.sort_values(metric, ascending=ascending).head(n)
    
    colors = ['#ff4757' if x < 0 else '#2ed573' for x in sorted_df[metric]]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=sorted_df['Symbol'],
        x=sorted_df[metric],
        orientation='h',
        marker=dict(color=colors, line=dict(color='white', width=0.5)),
        text=sorted_df[metric].round(2),
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>' + metric + ': %{x:.2f}<extra></extra>'
    ))
    
    title = f"{'Worst' if not ascending else 'Best'} {n} Stocks by {metric}"
    
    fig.update_layout(
        title=title,
        xaxis_title=metric,
        yaxis_title="",
        height=max(400, n * 25),
        plot_bgcolor='#0e1117',
        paper_bgcolor='#1a1d26',
        font=dict(color='#8b92a8'),
        showlegend=False,
        yaxis=dict(autorange="reversed")
    )
    
    fig.update_xaxes(gridcolor='#262a33', showgrid=True)
    fig.update_yaxes(gridcolor='#262a33', showgrid=False)
    
    return fig

# ==================== MAIN APP ====================

def main():
    # Header
    st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>📉 S&P 500 Drawdown Analysis</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8b92a8; margin-top: 5px;'>Comprehensive risk analysis for the entire market</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.markdown("### Configuration")
        
        analysis_type = st.radio(
            "Analysis Type",
            options=["Individual Stock", "Full S&P 500"],
            help="Choose to analyze a single stock or the entire S&P 500"
        )
        
        period = st.selectbox(
            "Analysis Period",
            options=["1y", "2y", "5y", "max"],
            index=1,
            help="Historical data period"
        )
        
        if analysis_type == "Individual Stock":
            symbol = st.text_input("Stock Symbol", value="AAPL", help="Enter ticker symbol").upper()
            analyze_button = st.button("🔍 Analyze Stock", type="primary", use_container_width=True)
        else:
            analyze_button = st.button("🔍 Analyze S&P 500", type="primary", use_container_width=True)
        
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
        st.markdown("""
        <div style='text-align: center; padding: 20px 0;'>
            <p style='color: #5a6270; font-size: 12px; margin: 0;'>Made by</p>
            <p style='color: #00d4ff; font-size: 16px; font-weight: 600; margin: 5px 0;'>@Gsnchez</p>
            <a href='https://bquantfinance.com' target='_blank' style='color: #8b92a8; font-size: 13px; text-decoration: none;'>
                🌐 bquantfinance.com
            </a>
        </div>
        """, unsafe_allow_html=True)
    
    # Main content
    if analysis_type == "Individual Stock" and (analyze_button or 'last_single_analysis' in st.session_state):
        if analyze_button or st.session_state.get('last_symbol') == symbol:
            with st.spinner(f"Analyzing {symbol}..."):
                stats = analyze_stock(symbol, period)
                
                if stats is None:
                    st.error(f"❌ Unable to load data for {symbol}. Please check the symbol and try again.")
                    return
                
                st.session_state.last_single_analysis = stats
                st.session_state.last_symbol = symbol
                
                # Display single stock analysis
                display_single_stock_analysis(stats)
    
    elif analysis_type == "Full S&P 500" and (analyze_button or 'last_sp500_analysis' in st.session_state):
        with st.spinner("Analyzing S&P 500... This may take a few minutes."):
            summary_df, prices = analyze_sp500(period)
            st.session_state.last_sp500_analysis = (summary_df, prices)
            
            # Display S&P 500 aggregate analysis
            display_sp500_analysis(summary_df, prices, period)
    
    else:
        # Welcome screen
        st.markdown("""
        <div style='text-align: center; padding: 100px 20px;'>
            <h2 style='color: #8b92a8;'>Welcome to S&P 500 Drawdown Analysis</h2>
            <p style='color: #5a6270; font-size: 18px;'>Select your analysis type in the sidebar to begin</p>
            <div style='margin-top: 60px;'>
                <p style='color: #5a6270; font-size: 14px;'>Made by <span style='color: #00d4ff; font-weight: 600;'>@Gsnchez</span></p>
                <a href='https://bquantfinance.com' target='_blank' style='color: #8b92a8; text-decoration: none;'>
                    🌐 bquantfinance.com
                </a>
            </div>
        </div>
        """, unsafe_allow_html=True)

def display_single_stock_analysis(stats):
    """Display analysis for a single stock"""
    st.markdown("### Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Max Drawdown", f"{stats['Max Drawdown (%)']:.2f}%", help="Largest peak-to-trough decline")
    with col2:
        st.metric("Current Drawdown", f"{stats['Current Drawdown (%)']:.2f}%", 
                 delta=f"{stats['Current Drawdown (%)'] - stats['Max Drawdown (%)']:.2f}%")
    with col3:
        st.metric("Number of Drawdowns", f"{stats['Number of Drawdowns']}")
    with col4:
        st.metric("Recovery Rate", f"{stats['Recovery Rate (%)']:.1f}%")
    
    st.markdown("---")
    st.markdown("### Price & Drawdown Analysis")
    fig = create_drawdown_chart(stats)
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabs
    tab1, tab2 = st.tabs(["📊 Statistics", "📋 Drawdown Periods"])
    
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
            st.dataframe(df, use_container_width=True, hide_index=True)

def display_sp500_analysis(summary_df, prices, period):
    """Display aggregate S&P 500 analysis"""
    st.success(f"✅ Successfully analyzed {len(summary_df)} stocks from the S&P 500")
    
    # Key Market Metrics
    st.markdown("### Market-Wide Statistics")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Avg Max Drawdown", f"{summary_df['Max Drawdown (%)'].mean():.2f}%")
    with col2:
        st.metric("Median Max Drawdown", f"{summary_df['Max Drawdown (%)'].median():.2f}%")
    with col3:
        st.metric("Worst Drawdown", f"{summary_df['Max Drawdown (%)'].min():.2f}%")
    with col4:
        st.metric("Avg Recovery Rate", f"{summary_df['Recovery Rate (%)'].mean():.1f}%")
    with col5:
        stocks_in_dd = (summary_df['Current Drawdown (%)'] < -10).sum()
        st.metric("Stocks in DD (>10%)", f"{stocks_in_dd}")
    
    st.markdown("---")
    
    # Tabs for different analyses
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🏆 Rankings", "📈 Correlations", "🔍 Detailed Table"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = create_sp500_distribution(summary_df)
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("#### Market Statistics")
            stats_df = pd.DataFrame({
                'Metric': ['Mean', 'Median', 'Std Dev', 'Min', 'Max', '25th Percentile', '75th Percentile'],
                'Max Drawdown (%)': [
                    summary_df['Max Drawdown (%)'].mean(),
                    summary_df['Max Drawdown (%)'].median(),
                    summary_df['Max Drawdown (%)'].std(),
                    summary_df['Max Drawdown (%)'].min(),
                    summary_df['Max Drawdown (%)'].max(),
                    summary_df['Max Drawdown (%)'].quantile(0.25),
                    summary_df['Max Drawdown (%)'].quantile(0.75)
                ]
            })
            stats_df['Max Drawdown (%)'] = stats_df['Max Drawdown (%)'].round(2)
            st.dataframe(stats_df, use_container_width=True, hide_index=True)
        
        with col2:
            fig = create_scatter_matrix(summary_df)
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("#### Current Market Status")
            in_dd = summary_df[summary_df['Current Drawdown (%)'] < -5].sort_values('Current Drawdown (%)')
            if len(in_dd) > 0:
                st.dataframe(
                    in_dd[['Symbol', 'Current Drawdown (%)', 'Max Drawdown (%)']].head(10),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No stocks currently in significant drawdown (< -5%)")
    
    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Worst Performers")
            fig = create_top_performers_chart(summary_df, 'Max Drawdown (%)', n=15, ascending=True)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### Best Performers")
            fig = create_top_performers_chart(summary_df, 'Max Drawdown (%)', n=15, ascending=False)
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Longest Recovery Times")
            recovery_sorted = summary_df[summary_df['Avg Recovery Time (days)'].notna()].sort_values(
                'Avg Recovery Time (days)', ascending=False
            ).head(15)
            fig = create_top_performers_chart(recovery_sorted, 'Avg Recovery Time (days)', n=15, ascending=False)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### Most Volatile (# of Drawdowns)")
            fig = create_top_performers_chart(summary_df, 'Number of Drawdowns', n=15, ascending=False)
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.markdown("### Drawdown Metrics Relationships")
        
        # Correlation heatmap
        corr_cols = ['Max Drawdown (%)', 'Avg Drawdown (%)', 'Number of Drawdowns', 
                     'Avg DD Duration (days)', 'Recovery Rate (%)', 'Time in DD (%)']
        corr_matrix = summary_df[corr_cols].corr()
        
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_cols,
            y=corr_cols,
            colorscale='RdBu',
            zmid=0,
            text=corr_matrix.values.round(2),
            texttemplate='%{text}',
            textfont={"size": 10},
            colorbar=dict(title="Correlation")
        ))
        
        fig.update_layout(
            title="Correlation Matrix of Drawdown Metrics",
            height=600,
            plot_bgcolor='#0e1117',
            paper_bgcolor='#1a1d26',
            font=dict(color='#8b92a8')
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.markdown("### Complete S&P 500 Data")
        
        # Add filters
        col1, col2, col3 = st.columns(3)
        with col1:
            sort_by = st.selectbox("Sort by", options=['Max Drawdown (%)', 'Current Drawdown (%)', 
                                                       'Recovery Rate (%)', 'Number of Drawdowns'])
        with col2:
            sort_order = st.radio("Order", options=['Ascending', 'Descending'], horizontal=True)
        with col3:
            filter_dd = st.slider("Filter: Max DD % (absolute)", 0, 100, (0, 100))
        
        # Apply filters and sorting
        filtered_df = summary_df[
            (summary_df['Max Drawdown (%)'].abs() >= filter_dd[0]) & 
            (summary_df['Max Drawdown (%)'].abs() <= filter_dd[1])
        ].sort_values(sort_by, ascending=(sort_order=='Ascending'))
        
        display_cols = ['Symbol', 'Max Drawdown (%)', 'Current Drawdown (%)', 'Number of Drawdowns',
                       'Avg DD Duration (days)', 'Recovery Rate (%)', 'Time in DD (%)']
        
        st.dataframe(
            filtered_df[display_cols].style.format({
                'Max Drawdown (%)': '{:.2f}',
                'Current Drawdown (%)': '{:.2f}',
                'Avg DD Duration (days)': '{:.1f}',
                'Recovery Rate (%)': '{:.1f}',
                'Time in DD (%)': '{:.1f}'
            }),
            use_container_width=True,
            hide_index=True,
            height=600
        )
        
        # Download button
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"sp500_drawdown_analysis_{period}.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()
