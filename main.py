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
    prices = pd.DataFrame()
    
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            
            if data is not None and len(data) > 0 and 'Close' in data.columns:
                prices[symbol] = data['Close']
        except Exception:
            continue
    
    prices = prices.dropna(axis=1, thresh=len(prices) * 0.8)
    return prices

@st.cache_data(ttl=3600)
def analyze_sp500(period="2y"):
    """Analyze all S&P 500 stocks."""
    symbols = get_sp500_symbols()
    prices = download_sp500_data(symbols, period)
    
    summary_results = []
    all_drawdown_periods = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, symbol in enumerate(prices.columns):
        returns = prices[symbol].pct_change().dropna()
        
        if len(returns) < 10:
            continue
        
        stats = comprehensive_drawdown_stats(returns, symbol=symbol)
        summary_dict = {k: v for k, v in stats.items() if k not in ['Drawdown Periods', 'Drawdown Series']}
        summary_results.append(summary_dict)
        
        # Collect all drawdown periods for aggregate analysis
        for period_info in stats['Drawdown Periods']:
            period_dict = period_info.copy()
            period_dict['Symbol'] = symbol
            all_drawdown_periods.append(period_dict)
        
        progress_bar.progress((i + 1) / len(prices.columns))
        status_text.text(f"Analyzing {i + 1}/{len(prices.columns)} stocks...")
    
    progress_bar.empty()
    status_text.empty()
    
    summary_df = pd.DataFrame(summary_results)
    periods_df = pd.DataFrame(all_drawdown_periods)
    
    return summary_df, prices, periods_df

# ==================== DATA LOADING ====================

@st.cache_data(ttl=3600)
def load_stock_data(symbol, period="2y"):
    """Load stock data from yfinance"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        
        if data is None or len(data) == 0:
            return None
        
        if 'Close' in data.columns:
            result = data['Close']
            if isinstance(result, pd.Series) and len(result) > 10:
                return result.dropna()
        return None
        
    except Exception:
        return None

@st.cache_data(ttl=3600)
def analyze_stock(symbol, period="2y"):
    """Analyze a single stock"""
    prices = load_stock_data(symbol, period)
    
    if prices is None or not isinstance(prices, pd.Series) or len(prices) < 10:
        return None
    
    returns = prices.pct_change().dropna()
    
    if len(returns) < 10:
        return None
    
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
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1a1d26; padding: 15px; border-radius: 10px; border: 1px solid #262a33; }
    h1, h2, h3 { color: #ffffff; font-weight: 600; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: #1a1d26; border-radius: 10px; padding: 5px; }
    .stTabs [data-baseweb="tab"] { background-color: transparent; color: #8b92a8; border-radius: 8px; padding: 10px 20px; }
    .stTabs [aria-selected="true"] { background-color: #262a33; color: #ffffff; }
</style>
""", unsafe_allow_html=True)

# ==================== COMPREHENSIVE PLOTTING FUNCTIONS ====================

def create_drawdown_timeline(stats):
    """Create comprehensive price and drawdown timeline"""
    drawdowns = stats['Drawdown Series']
    prices = stats['Prices']
    
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.6, 0.4],
        subplot_titles=('Price History & Peak Points', 'Drawdown Timeline'),
        vertical_spacing=0.1
    )
    
    # Calculate peak points
    cummax_prices = prices.cummax()
    
    # Price chart with peaks
    fig.add_trace(go.Scatter(x=prices.index, y=prices.values, name='Price',
                             line=dict(color='#00d4ff', width=2), fill='tonexty',
                             fillcolor='rgba(0, 212, 255, 0.1)'), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=cummax_prices.index, y=cummax_prices.values, name='Peak',
                             line=dict(color='#2ed573', width=1, dash='dash')), row=1, col=1)
    
    # Drawdown chart with colored regions
    fig.add_trace(go.Scatter(x=drawdowns.index, y=drawdowns.values * 100, name='Drawdown',
                             line=dict(color='#ff4757', width=2), fill='tozeroy',
                             fillcolor='rgba(255, 71, 87, 0.3)'), row=2, col=1)
    
    # Highlight each drawdown period
    colors = ['rgba(255, 71, 87, 0.15)', 'rgba(255, 107, 107, 0.15)', 'rgba(255, 159, 67, 0.15)']
    for i, period in enumerate(stats['Drawdown Periods'][:10]):
        color = colors[i % len(colors)]
        fig.add_vrect(x0=period['Start'], x1=period['End'], fillcolor=color,
                     layer='below', line_width=0, row=2, col=1)
    
    fig.update_layout(height=700, showlegend=True, hovermode='x unified',
                     plot_bgcolor='#0e1117', paper_bgcolor='#1a1d26',
                     font=dict(color='#8b92a8'), margin=dict(l=50, r=50, t=50, b=50))
    
    fig.update_xaxes(gridcolor='#262a33', showgrid=True)
    fig.update_yaxes(gridcolor='#262a33', showgrid=True)
    
    return fig

def create_drawdown_magnitude_duration_scatter(stats):
    """Scatter plot of drawdown magnitude vs duration"""
    periods = stats['Drawdown Periods']
    
    if not periods:
        return None
    
    magnitudes = [abs(p['Max Drawdown'] * 100) for p in periods]
    durations = [p['Duration (days)'] for p in periods]
    recovery_times = [p['Recovery Time (days)'] if p['Recovery Time (days)'] else 0 for p in periods]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=durations, y=magnitudes, mode='markers',
        marker=dict(size=12, color=recovery_times, colorscale='Reds',
                   showscale=True, line=dict(color='white', width=1),
                   colorbar=dict(title="Recovery<br>Days")),
        text=[f"Start: {p['Start'].strftime('%Y-%m-%d')}<br>Valley: {p['Valley'].strftime('%Y-%m-%d')}<br>DD: {abs(p['Max Drawdown']*100):.1f}%<br>Duration: {p['Duration (days)']} days" 
              for p in periods],
        hovertemplate='%{text}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Drawdown Magnitude vs Duration",
        xaxis_title="Duration (days)", yaxis_title="Max Drawdown (%)",
        height=500, plot_bgcolor='#0e1117', paper_bgcolor='#1a1d26',
        font=dict(color='#8b92a8'), hovermode='closest'
    )
    
    fig.update_xaxes(gridcolor='#262a33', showgrid=True)
    fig.update_yaxes(gridcolor='#262a33', showgrid=True)
    
    return fig

def create_drawdown_waterfall(stats):
    """Enhanced drawdown visualization with multiple view options"""
    periods = sorted(stats['Drawdown Periods'], key=lambda x: x['Max Drawdown'])[:15]
    
    if not periods:
        return None
    
    # Create subplots - 3 columns x 5 rows for 15 drawdowns
    fig = make_subplots(
        rows=5, cols=3,
        subplot_titles=[f"{p['Start'].strftime('%Y-%m-%d')}<br>{abs(p['Max Drawdown']*100):.1f}%" for p in periods],
        vertical_spacing=0.08,
        horizontal_spacing=0.08
    )
    
    # Plot each drawdown in its own subplot
    for idx, p in enumerate(periods):
        row = idx // 3 + 1
        col = idx % 3 + 1
        
        # Create timeline for this drawdown
        start_date = p['Start']
        valley_date = p['Valley']
        end_date = p['End']
        recovery_date = p['Recovery'] if p['Recovery'] else end_date
        
        dates = [start_date, valley_date, end_date]
        values = [0, p['Max Drawdown'] * 100, 0]
        
        if p['Recovery']:
            dates.append(recovery_date)
            values.append(0)
        
        # Color based on severity
        severity = abs(p['Max Drawdown'] * 100)
        if severity < 10:
            color = '#ffa502'
        elif severity < 20:
            color = '#ff6348'
        else:
            color = '#ff4757'
        
        fig.add_trace(
            go.Scatter(
                x=dates, y=values,
                mode='lines',
                line=dict(color=color, width=2),
                fill='tozeroy',
                fillcolor=color.replace(')', ', 0.3)').replace('rgb', 'rgba'),
                showlegend=False,
                hovertemplate=f"<b>{start_date.strftime('%Y-%m-%d')}</b><br>DD: {abs(p['Max Drawdown']*100):.2f}%<br>Days: {p['Duration (days)']} <extra></extra>"
            ),
            row=row, col=col
        )
        
        # Mark the valley point
        fig.add_trace(
            go.Scatter(
                x=[valley_date],
                y=[p['Max Drawdown'] * 100],
                mode='markers',
                marker=dict(color='white', size=6, line=dict(color=color, width=2)),
                showlegend=False,
                hoverinfo='skip'
            ),
            row=row, col=col
        )
    
    fig.update_layout(
        title="Top 15 Drawdowns - Individual Profiles (Small Multiples)",
        height=1200,
        plot_bgcolor='#0e1117',
        paper_bgcolor='#1a1d26',
        font=dict(color='#8b92a8', size=9),
        showlegend=False
    )
    
    # Update all axes
    for i in range(1, 16):
        row = (i - 1) // 3 + 1
        col = (i - 1) % 3 + 1
        fig.update_xaxes(showgrid=True, gridcolor='#262a33', showticklabels=False, row=row, col=col)
        fig.update_yaxes(showgrid=True, gridcolor='#262a33', zeroline=True, zerolinecolor='#3d4452', row=row, col=col)
    
    return fig

def create_drawdown_timeline_bars(stats):
    """Timeline view with horizontal bars showing drawdown periods"""
    periods = sorted(stats['Drawdown Periods'], key=lambda x: x['Max Drawdown'])[:20]
    
    if not periods:
        return None
    
    fig = go.Figure()
    
    for i, p in enumerate(periods):
        # Calculate bar properties
        start = p['Start']
        end = p['Recovery'] if p['Recovery'] else p['End']
        severity = abs(p['Max Drawdown'] * 100)
        
        # Color based on severity
        if severity < 10:
            color = '#ffa502'
        elif severity < 20:
            color = '#ff6348'
        else:
            color = '#ff4757'
        
        # Add bar for drawdown period
        fig.add_trace(go.Bar(
            x=[end - start],
            y=[i],
            base=start,
            orientation='h',
            marker=dict(
                color=color,
                opacity=0.8,
                line=dict(color='white', width=1)
            ),
            name=f"{start.strftime('%Y-%m-%d')}",
            text=f"{severity:.1f}%",
            textposition='inside',
            hovertemplate=f"<b>{start.strftime('%Y-%m-%d')}</b><br>Max DD: {severity:.2f}%<br>Duration: {p['Duration (days)')} days<br>Recovery: {p['Recovery Time (days)']} days<extra></extra>"
        ))
        
        # Add marker at valley
        valley_x = p['Valley']
        fig.add_trace(go.Scatter(
            x=[valley_x],
            y=[i],
            mode='markers',
            marker=dict(
                symbol='diamond',
                size=10,
                color='white',
                line=dict(color=color, width=2)
            ),
            showlegend=False,
            hoverinfo='skip'
        ))
    
    fig.update_layout(
        title="Drawdown Timeline - Duration & Severity View",
        xaxis_title="Time",
        yaxis_title="Drawdown Events (ranked by severity)",
        height=700,
        plot_bgcolor='#0e1117',
        paper_bgcolor='#1a1d26',
        font=dict(color='#8b92a8'),
        showlegend=False,
        yaxis=dict(showticklabels=False)
    )
    
    fig.update_xaxes(gridcolor='#262a33', showgrid=True)
    fig.update_yaxes(gridcolor='#262a33', showgrid=False)
    
    return fig

def create_drawdown_bubble_chart(stats):
    """Bubble chart: start date vs depth, size = duration"""
    periods = stats['Drawdown Periods']
    
    if not periods:
        return None
    
    start_dates = [p['Start'] for p in periods]
    depths = [abs(p['Max Drawdown'] * 100) for p in periods]
    durations = [p['Duration (days)'] for p in periods]
    recovery_status = ['Recovered' if p['Recovery'] else 'Not Recovered' for p in periods]
    recovery_times = [p['Recovery Time (days)'] if p['Recovery Time (days)'] else 0 for p in periods]
    
    fig = go.Figure()
    
    # Recovered drawdowns
    recovered_mask = [p['Recovery'] is not None for p in periods]
    fig.add_trace(go.Scatter(
        x=[d for d, r in zip(start_dates, recovered_mask) if r],
        y=[depth for depth, r in zip(depths, recovered_mask) if r],
        mode='markers',
        marker=dict(
            size=[dur/5 for dur, r in zip(durations, recovered_mask) if r],
            color=[rt for rt, r in zip(recovery_times, recovered_mask) if r],
            colorscale='Greens',
            showscale=True,
            colorbar=dict(title="Recovery<br>Time (days)", x=1.15),
            line=dict(color='white', width=1),
            sizemode='diameter'
        ),
        name='Recovered',
        text=[f"Start: {d.strftime('%Y-%m-%d')}<br>DD: {depth:.1f}%<br>Duration: {dur} days<br>Recovery: {rt} days" 
              for d, depth, dur, rt, r in zip(start_dates, depths, durations, recovery_times, recovered_mask) if r],
        hovertemplate='%{text}<extra></extra>'
    ))
    
    # Not recovered drawdowns
    fig.add_trace(go.Scatter(
        x=[d for d, r in zip(start_dates, recovered_mask) if not r],
        y=[depth for depth, r in zip(depths, recovered_mask) if not r],
        mode='markers',
        marker=dict(
            size=[dur/5 for dur, r in zip(durations, recovered_mask) if not r],
            color='#ff4757',
            line=dict(color='white', width=1),
            sizemode='diameter'
        ),
        name='Not Recovered',
        text=[f"Start: {d.strftime('%Y-%m-%d')}<br>DD: {depth:.1f}%<br>Duration: {dur} days<br>Status: Ongoing" 
              for d, depth, dur, r in zip(start_dates, depths, durations, recovered_mask) if not r],
        hovertemplate='%{text}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Drawdown Bubble Chart - Timeline vs Severity<br><sub>Bubble size = Duration</sub>",
        xaxis_title="Start Date",
        yaxis_title="Maximum Drawdown (%)",
        height=600,
        plot_bgcolor='#0e1117',
        paper_bgcolor='#1a1d26',
        font=dict(color='#8b92a8'),
        hovermode='closest',
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor='rgba(26, 29, 38, 0.8)'
        )
    )
    
    fig.update_xaxes(gridcolor='#262a33', showgrid=True)
    fig.update_yaxes(gridcolor='#262a33', showgrid=True)
    
    return fig

def create_recovery_analysis(stats):
    """Detailed recovery time analysis"""
    periods = [p for p in stats['Drawdown Periods'] if p['Recovery Time (days)'] is not None]
    
    if not periods:
        return None
    
    recovery_times = [p['Recovery Time (days)'] for p in periods]
    magnitudes = [abs(p['Max Drawdown'] * 100) for p in periods]
    
    fig = make_subplots(rows=1, cols=2, subplot_titles=('Recovery Time Distribution', 'Recovery Efficiency'))
    
    # Histogram of recovery times
    fig.add_trace(go.Histogram(x=recovery_times, nbinsx=20,
                              marker=dict(color='#00d4ff', line=dict(color='white', width=1))),
                 row=1, col=1)
    
    # Recovery efficiency (magnitude / recovery time)
    efficiency = [m / r if r > 0 else 0 for m, r in zip(magnitudes, recovery_times)]
    fig.add_trace(go.Scatter(x=magnitudes, y=recovery_times, mode='markers',
                            marker=dict(size=10, color=efficiency, colorscale='RdYlGn_r',
                                      showscale=True, colorbar=dict(title="DD/Day", x=1.15)),
                            text=[f"DD: {m:.1f}%<br>Recovery: {r} days<br>Efficiency: {e:.2f}" 
                                  for m, r, e in zip(magnitudes, recovery_times, efficiency)],
                            hovertemplate='%{text}<extra></extra>'), row=1, col=2)
    
    fig.update_layout(height=400, plot_bgcolor='#0e1117', paper_bgcolor='#1a1d26',
                     font=dict(color='#8b92a8'), showlegend=False)
    
    fig.update_xaxes(title_text="Recovery Time (days)", gridcolor='#262a33', showgrid=True, row=1, col=1)
    fig.update_xaxes(title_text="Drawdown Magnitude (%)", gridcolor='#262a33', showgrid=True, row=1, col=2)
    fig.update_yaxes(title_text="Frequency", gridcolor='#262a33', showgrid=True, row=1, col=1)
    fig.update_yaxes(title_text="Recovery Time (days)", gridcolor='#262a33', showgrid=True, row=1, col=2)
    
    return fig

def create_drawdown_heatmap(stats):
    """Create a heatmap of drawdowns over time"""
    drawdowns = stats['Drawdown Series']
    
    # Resample to monthly for cleaner visualization
    monthly_dd = drawdowns.resample('M').min() * 100
    
    # Create year and month columns
    years = monthly_dd.index.year.unique()
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    # Create matrix
    matrix = []
    for year in years:
        year_data = monthly_dd[monthly_dd.index.year == year]
        row = [year_data[year_data.index.month == m].values[0] if len(year_data[year_data.index.month == m]) > 0 else 0 
               for m in range(1, 13)]
        matrix.append(row)
    
    fig = go.Figure(data=go.Heatmap(
        z=matrix, x=months, y=years,
        colorscale='RdYlGn', zmid=0, reversescale=True,
        text=[[f"{val:.1f}%" for val in row] for row in matrix],
        texttemplate='%{text}', textfont={"size": 8},
        colorbar=dict(title="DD %")
    ))
    
    fig.update_layout(
        title="Monthly Drawdown Heatmap",
        xaxis_title="Month", yaxis_title="Year",
        height=400, plot_bgcolor='#0e1117', paper_bgcolor='#1a1d26',
        font=dict(color='#8b92a8')
    )
    
    return fig

def create_aggregate_sp500_distributions(periods_df):
    """Create comprehensive distribution plots for all S&P 500 drawdowns"""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Drawdown Magnitude Distribution', 'Duration Distribution',
                       'Recovery Time Distribution', 'Drawdowns by Year'),
        specs=[[{'type': 'histogram'}, {'type': 'histogram'}],
               [{'type': 'histogram'}, {'type': 'bar'}]]
    )
    
    # Magnitude distribution
    magnitudes = periods_df['Max Drawdown'] * 100
    fig.add_trace(go.Histogram(x=magnitudes, nbinsx=50,
                              marker=dict(color='#ff4757', line=dict(color='white', width=0.5)),
                              name='Magnitude'), row=1, col=1)
    
    # Duration distribution
    durations = periods_df['Duration (days)']
    fig.add_trace(go.Histogram(x=durations, nbinsx=50,
                              marker=dict(color='#ffa502', line=dict(color='white', width=0.5)),
                              name='Duration'), row=1, col=2)
    
    # Recovery time distribution
    recovery_data = periods_df[periods_df['Recovery Time (days)'].notna()]['Recovery Time (days)']
    fig.add_trace(go.Histogram(x=recovery_data, nbinsx=50,
                              marker=dict(color='#00d4ff', line=dict(color='white', width=0.5)),
                              name='Recovery'), row=2, col=1)
    
    # Drawdowns by year
    periods_df['Year'] = pd.to_datetime(periods_df['Start']).dt.year
    yearly_counts = periods_df['Year'].value_counts().sort_index()
    fig.add_trace(go.Bar(x=yearly_counts.index, y=yearly_counts.values,
                        marker=dict(color='#2ed573', line=dict(color='white', width=0.5)),
                        name='Count'), row=2, col=2)
    
    fig.update_layout(height=800, showlegend=False, plot_bgcolor='#0e1117',
                     paper_bgcolor='#1a1d26', font=dict(color='#8b92a8'))
    
    fig.update_xaxes(title_text="Drawdown (%)", gridcolor='#262a33', showgrid=True, row=1, col=1)
    fig.update_xaxes(title_text="Duration (days)", gridcolor='#262a33', showgrid=True, row=1, col=2)
    fig.update_xaxes(title_text="Recovery Time (days)", gridcolor='#262a33', showgrid=True, row=2, col=1)
    fig.update_xaxes(title_text="Year", gridcolor='#262a33', showgrid=True, row=2, col=2)
    
    for i in range(1, 3):
        for j in range(1, 3):
            fig.update_yaxes(gridcolor='#262a33', showgrid=True, row=i, col=j)
    
    return fig

def create_sp500_scatter_3d(periods_df):
    """3D scatter of magnitude vs duration vs recovery"""
    filtered = periods_df[periods_df['Recovery Time (days)'].notna()].copy()
    filtered['Magnitude'] = abs(filtered['Max Drawdown'] * 100)
    
    fig = go.Figure(data=[go.Scatter3d(
        x=filtered['Magnitude'],
        y=filtered['Duration (days)'],
        z=filtered['Recovery Time (days)'],
        mode='markers',
        marker=dict(
            size=4,
            color=filtered['Magnitude'],
            colorscale='Reds',
            showscale=True,
            colorbar=dict(title="DD %"),
            line=dict(color='white', width=0.5)
        ),
        text=filtered['Symbol'],
        hovertemplate='<b>%{text}</b><br>DD: %{x:.1f}%<br>Duration: %{y} days<br>Recovery: %{z} days<extra></extra>'
    )])
    
    fig.update_layout(
        title="3D Analysis: Magnitude vs Duration vs Recovery",
        scene=dict(
            xaxis=dict(title='Drawdown Magnitude (%)', gridcolor='#262a33', backgroundcolor='#0e1117'),
            yaxis=dict(title='Duration (days)', gridcolor='#262a33', backgroundcolor='#0e1117'),
            zaxis=dict(title='Recovery Time (days)', gridcolor='#262a33', backgroundcolor='#0e1117'),
            bgcolor='#0e1117'
        ),
        height=600,
        paper_bgcolor='#1a1d26',
        font=dict(color='#8b92a8')
    )
    
    return fig

def create_box_plots_comparison(periods_df):
    """Box plots comparing drawdown metrics"""
    fig = make_subplots(rows=1, cols=3, subplot_titles=('Magnitude', 'Duration', 'Recovery Time'))
    
    fig.add_trace(go.Box(y=periods_df['Max Drawdown'] * 100, name='Magnitude',
                        marker=dict(color='#ff4757'), boxmean='sd'), row=1, col=1)
    
    fig.add_trace(go.Box(y=periods_df['Duration (days)'], name='Duration',
                        marker=dict(color='#ffa502'), boxmean='sd'), row=1, col=2)
    
    recovery_data = periods_df[periods_df['Recovery Time (days)'].notna()]['Recovery Time (days)']
    fig.add_trace(go.Box(y=recovery_data, name='Recovery',
                        marker=dict(color='#00d4ff'), boxmean='sd'), row=1, col=3)
    
    fig.update_layout(height=400, showlegend=False, plot_bgcolor='#0e1117',
                     paper_bgcolor='#1a1d26', font=dict(color='#8b92a8'))
    
    fig.update_yaxes(title_text="Drawdown (%)", gridcolor='#262a33', showgrid=True, row=1, col=1)
    fig.update_yaxes(title_text="Days", gridcolor='#262a33', showgrid=True, row=1, col=2)
    fig.update_yaxes(title_text="Days", gridcolor='#262a33', showgrid=True, row=1, col=3)
    
    return fig

# ==================== MAIN APP ====================

def main():
    st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>📉 S&P 500 Drawdown Analysis</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8b92a8; margin-top: 5px;'>Comprehensive risk analysis for the entire market</p>", unsafe_allow_html=True)
    st.markdown("---")
    
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
    
    if analysis_type == "Individual Stock":
        if analyze_button:
            with st.spinner(f"Analyzing {symbol}..."):
                stats = analyze_stock(symbol, period)
                
                if stats is None:
                    st.error(f"❌ Unable to load data for {symbol}. Please check the symbol and try again.")
                else:
                    st.session_state.last_single_analysis = stats
                    st.session_state.last_symbol = symbol
                    st.session_state.last_period = period
                    display_single_stock_analysis(stats)
        elif 'last_single_analysis' in st.session_state and st.session_state.get('last_symbol') == symbol and st.session_state.get('last_period') == period:
            display_single_stock_analysis(st.session_state.last_single_analysis)
    
    elif analysis_type == "Full S&P 500":
        if analyze_button:
            with st.spinner("Analyzing S&P 500... This may take a few minutes."):
                summary_df, prices, periods_df = analyze_sp500(period)
                st.session_state.last_sp500_analysis = (summary_df, prices, periods_df)
                st.session_state.last_sp500_period = period
                display_sp500_analysis(summary_df, prices, periods_df, period)
        elif 'last_sp500_analysis' in st.session_state and st.session_state.get('last_sp500_period') == period:
            summary_df, prices, periods_df = st.session_state.last_sp500_analysis
            display_sp500_analysis(summary_df, prices, periods_df, period)
    
    else:
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
    """Display comprehensive analysis for a single stock"""
    st.markdown("### Key Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Max Drawdown", f"{stats['Max Drawdown (%)']:.2f}%")
    with col2:
        st.metric("Current Drawdown", f"{stats['Current Drawdown (%)']:.2f}%")
    with col3:
        st.metric("# of Drawdowns", f"{stats['Number of Drawdowns']}")
    with col4:
        st.metric("Avg Duration", f"{stats['Avg DD Duration (days)']:.0f} days")
    with col5:
        st.metric("Recovery Rate", f"{stats['Recovery Rate (%)']:.1f}%")
    
    st.markdown("---")
    
    # Main timeline
    st.markdown("### 📊 Complete Drawdown Timeline")
    fig = create_drawdown_timeline(stats)
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Comprehensive tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔍 Individual Drawdowns", "📈 Magnitude Analysis", "⏱️ Duration & Recovery",
        "🗓️ Temporal Patterns", "📋 Detailed Table"
    ])
    
    with tab1:
        st.markdown("### Individual Drawdown Events")
        
        # Add chart selection
        chart_type = st.radio(
            "Visualization Style",
            options=["Small Multiples (Individual Profiles)", "Timeline Bars", "Bubble Chart"],
            horizontal=True
        )
        
        if chart_type == "Small Multiples (Individual Profiles)":
            st.info("📊 Each drawdown shown in its own chart - best for comparing shapes and profiles")
            fig = create_drawdown_waterfall(stats)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Detailed metrics for each drawdown
        st.markdown("#### All Drawdown Events")
        if stats['Drawdown Periods']:
            periods_data = []
            for i, p in enumerate(stats['Drawdown Periods'], 1):
                periods_data.append({
                    '#': i,
                    'Start': p['Start'].strftime('%Y-%m-%d'),
                    'Valley': p['Valley'].strftime('%Y-%m-%d'),
                    'End': p['End'].strftime('%Y-%m-%d'),
                    'Recovery': p['Recovery'].strftime('%Y-%m-%d') if p['Recovery'] else 'Ongoing',
                    'Max DD (%)': f"{p['Max Drawdown'] * 100:.2f}",
                    'Duration (days)': p['Duration (days)'],
                    'Recovery (days)': p['Recovery Time (days)'] if p['Recovery Time (days)'] else 'N/A'
                })
            df = pd.DataFrame(periods_data)
            st.dataframe(df, use_container_width=True, hide_index=True, height=400)
        
        elif chart_type == "Timeline Bars":
            st.info("📅 Horizontal bars showing when drawdowns occurred, colored by severity, with valley markers")
            fig = create_drawdown_timeline_bars(stats)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        else:  # Bubble Chart
            st.info("🎯 Bubble chart: X=Start Date, Y=Depth, Size=Duration, Color=Recovery Time")
            fig = create_drawdown_bubble_chart(stats)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Additional scatter plot
        col1, col2 = st.columns(2)
        with col1:
            fig = create_drawdown_magnitude_duration_scatter(stats)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Top 10 worst in a simple bar chart
            periods = sorted(stats['Drawdown Periods'], key=lambda x: x['Max Drawdown'])[:10]
            dates = [p['Start'].strftime('%Y-%m-%d') for p in periods]
            values = [abs(p['Max Drawdown'] * 100) for p in periods]
            
            fig = go.Figure(go.Bar(
                x=values, y=dates, orientation='h',
                marker=dict(color=values, colorscale='Reds',
                           line=dict(color='white', width=0.5)),
                text=[f"{v:.2f}%" for v in values],
                textposition='outside'
            ))
            
            fig.update_layout(
                title="Top 10 Worst Drawdowns",
                xaxis_title="Drawdown Depth (%)", yaxis_title="",
                height=400, plot_bgcolor='#0e1117', paper_bgcolor='#1a1d26',
                font=dict(color='#8b92a8'), yaxis=dict(autorange="reversed"),
                showlegend=False
            )
            
            fig.update_xaxes(gridcolor='#262a33', showgrid=True)
            fig.update_yaxes(gridcolor='#262a33', showgrid=False)
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Detailed metrics for each drawdown
        st.markdown("#### All Drawdown Events")
        if stats['Drawdown Periods']:
            periods_data = []
            for i, p in enumerate(stats['Drawdown Periods'], 1):
                periods_data.append({
                    '#': i,
                    'Start': p['Start'].strftime('%Y-%m-%d'),
                    'Valley': p['Valley'].strftime('%Y-%m-%d'),
                    'End': p['End'].strftime('%Y-%m-%d'),
                    'Recovery': p['Recovery'].strftime('%Y-%m-%d') if p['Recovery'] else 'Ongoing',
                    'Max DD (%)': f"{p['Max Drawdown'] * 100:.2f}",
                    'Duration (days)': p['Duration (days)'],
                    'Recovery (days)': p['Recovery Time (days)'] if p['Recovery Time (days)'] else 'N/A'
                })
            df = pd.DataFrame(periods_data)
            st.dataframe(df, use_container_width=True, hide_index=True, height=400)
    
    with tab2:
        st.markdown("### Drawdown Magnitude Analysis")
        
        if stats['Drawdown Periods']:
            magnitudes = [abs(p['Max Drawdown'] * 100) for p in stats['Drawdown Periods']]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Average Magnitude", f"{np.mean(magnitudes):.2f}%")
            with col2:
                st.metric("Median Magnitude", f"{np.median(magnitudes):.2f}%")
            with col3:
                st.metric("Std Deviation", f"{np.std(magnitudes):.2f}%")
            
            # Distribution
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=magnitudes, nbinsx=15,
                                      marker=dict(color='#ff4757', line=dict(color='white', width=1))))
            fig.update_layout(title="Distribution of Drawdown Magnitudes",
                            xaxis_title="Drawdown (%)", yaxis_title="Frequency",
                            height=400, plot_bgcolor='#0e1117', paper_bgcolor='#1a1d26',
                            font=dict(color='#8b92a8'), showlegend=False)
            fig.update_xaxes(gridcolor='#262a33', showgrid=True)
            fig.update_yaxes(gridcolor='#262a33', showgrid=True)
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.markdown("### Duration & Recovery Analysis")
        
        fig = create_recovery_analysis(stats)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Duration Statistics")
            if stats['Drawdown Periods']:
                durations = [p['Duration (days)'] for p in stats['Drawdown Periods']]
                st.metric("Max Duration", f"{max(durations)} days")
                st.metric("Avg Duration", f"{np.mean(durations):.1f} days")
                st.metric("Median Duration", f"{np.median(durations):.0f} days")
        
        with col2:
            st.markdown("#### Recovery Statistics")
            recovery_times = [p['Recovery Time (days)'] for p in stats['Drawdown Periods'] 
                            if p['Recovery Time (days)'] is not None]
            if recovery_times:
                st.metric("Max Recovery", f"{max(recovery_times)} days")
                st.metric("Avg Recovery", f"{np.mean(recovery_times):.1f} days")
                st.metric("Median Recovery", f"{np.median(recovery_times):.0f} days")
            else:
                st.info("No completed recoveries in dataset")
    
    with tab4:
        st.markdown("### Temporal Patterns")
        
        fig = create_drawdown_heatmap(stats)
        st.plotly_chart(fig, use_container_width=True)
        
        # Yearly statistics
        if stats['Drawdown Periods']:
            periods_df = pd.DataFrame(stats['Drawdown Periods'])
            periods_df['Year'] = pd.to_datetime(periods_df['Start']).dt.year
            
            yearly_stats = periods_df.groupby('Year').agg({
                'Max Drawdown': ['count', 'mean', 'min'],
                'Duration (days)': 'mean'
            }).round(2)
            
            st.markdown("#### Yearly Drawdown Statistics")
            st.dataframe(yearly_stats, use_container_width=True)
    
    with tab5:
        st.markdown("### Complete Drawdown Data")
        
        if stats['Drawdown Periods']:
            full_data = []
            for i, p in enumerate(stats['Drawdown Periods'], 1):
                full_data.append({
                    'Event #': i,
                    'Start Date': p['Start'].strftime('%Y-%m-%d'),
                    'Valley Date': p['Valley'].strftime('%Y-%m-%d'),
                    'End Date': p['End'].strftime('%Y-%m-%d'),
                    'Recovery Date': p['Recovery'].strftime('%Y-%m-%d') if p['Recovery'] else 'Ongoing',
                    'Max Drawdown (%)': round(p['Max Drawdown'] * 100, 2),
                    'Duration (days)': p['Duration (days)'],
                    'Recovery Time (days)': p['Recovery Time (days)'] if p['Recovery Time (days)'] else None,
                    'Days to Valley': (p['Valley'] - p['Start']).days
                })
            
            df_full = pd.DataFrame(full_data)
            st.dataframe(df_full, use_container_width=True, height=600, hide_index=True)
            
            # Download button
            csv = df_full.to_csv(index=False)
            st.download_button(
                label="📥 Download Complete Data (CSV)",
                data=csv,
                file_name=f"{stats['Symbol']}_drawdown_analysis.csv",
                mime="text/csv"
            )

def display_sp500_analysis(summary_df, prices, periods_df, period):
    """Display comprehensive aggregate S&P 500 analysis"""
    st.success(f"✅ Analyzed {len(summary_df)} stocks with {len(periods_df)} total drawdown events")
    
    # Aggregate metrics
    st.markdown("### 📊 Market-Wide Aggregate Statistics")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("Total Drawdowns", f"{len(periods_df)}")
    with col2:
        st.metric("Avg Max DD", f"{summary_df['Max Drawdown (%)'].mean():.2f}%")
    with col3:
        st.metric("Worst DD", f"{periods_df['Max Drawdown'].min() * 100:.2f}%")
    with col4:
        avg_duration = periods_df['Duration (days)'].mean()
        st.metric("Avg Duration", f"{avg_duration:.0f} days")
    with col5:
        recovered = periods_df['Recovery Time (days)'].notna().sum()
        recovery_rate = (recovered / len(periods_df)) * 100
        st.metric("Recovery Rate", f"{recovery_rate:.1f}%")
    with col6:
        avg_recovery = periods_df['Recovery Time (days)'].mean()
        st.metric("Avg Recovery", f"{avg_recovery:.0f} days")
    
    st.markdown("---")
    
    # Comprehensive tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Aggregate Distributions", "🎯 3D Analysis", "📊 Statistical Comparisons",
        "🏆 Top Drawdowns", "🔍 Full Dataset"
    ])
    
    with tab1:
        st.markdown("### Complete Distribution Analysis")
        fig = create_aggregate_sp500_distributions(periods_df)
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary statistics
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Magnitude Statistics")
            mag_stats = periods_df['Max Drawdown'].describe() * 100
            st.dataframe(mag_stats.round(2), use_container_width=True)
        
        with col2:
            st.markdown("#### Duration Statistics")
            dur_stats = periods_df['Duration (days)'].describe()
            st.dataframe(dur_stats.round(2), use_container_width=True)
    
    with tab2:
        st.markdown("### 3D Relationship Analysis")
        fig = create_sp500_scatter_3d(periods_df)
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("#### Key Insights")
        col1, col2, col3 = st.columns(3)
        with col1:
            corr_mag_dur = periods_df[['Max Drawdown', 'Duration (days)']].corr().iloc[0, 1]
            st.metric("Magnitude-Duration Correlation", f"{corr_mag_dur:.3f}")
        
        with col2:
            filtered = periods_df[periods_df['Recovery Time (days)'].notna()]
            corr_mag_rec = filtered[['Max Drawdown', 'Recovery Time (days)']].corr().iloc[0, 1]
            st.metric("Magnitude-Recovery Correlation", f"{corr_mag_rec:.3f}")
        
        with col3:
            corr_dur_rec = filtered[['Duration (days)', 'Recovery Time (days)']].corr().iloc[0, 1]
            st.metric("Duration-Recovery Correlation", f"{corr_dur_rec:.3f}")
    
    with tab3:
        st.markdown("### Statistical Comparisons")
        fig = create_box_plots_comparison(periods_df)
        st.plotly_chart(fig, use_container_width=True)
        
        # Percentile analysis
        st.markdown("#### Percentile Analysis")
        percentiles = [10, 25, 50, 75, 90, 95, 99]
        
        perc_data = {
            'Percentile': [f"{p}th" for p in percentiles],
            'Magnitude (%)': [periods_df['Max Drawdown'].quantile(p/100) * 100 for p in percentiles],
            'Duration (days)': [periods_df['Duration (days)'].quantile(p/100) for p in percentiles],
            'Recovery (days)': [periods_df['Recovery Time (days)'].quantile(p/100) for p in percentiles]
        }
        
        perc_df = pd.DataFrame(perc_data)
        st.dataframe(perc_df.style.format({
            'Magnitude (%)': '{:.2f}',
            'Duration (days)': '{:.1f}',
            'Recovery (days)': '{:.1f}'
        }), use_container_width=True, hide_index=True)
    
    with tab4:
        st.markdown("### Worst Drawdown Events Across S&P 500")
        
        # Top 50 worst drawdowns
        worst_50 = periods_df.nsmallest(50, 'Max Drawdown').copy()
        worst_50['Max Drawdown (%)'] = worst_50['Max Drawdown'] * 100
        worst_50['Rank'] = range(1, len(worst_50) + 1)
        
        display_cols = ['Rank', 'Symbol', 'Start', 'Valley', 'Max Drawdown (%)', 
                       'Duration (days)', 'Recovery Time (days)']
        
        worst_50['Start'] = worst_50['Start'].dt.strftime('%Y-%m-%d')
        worst_50['Valley'] = worst_50['Valley'].dt.strftime('%Y-%m-%d')
        
        st.dataframe(
            worst_50[display_cols].style.format({
                'Max Drawdown (%)': '{:.2f}',
                'Duration (days)': '{:.0f}',
                'Recovery Time (days)': '{:.0f}'
            }),
            use_container_width=True,
            height=600,
            hide_index=True
        )
        
        # Download top 50
        csv = worst_50[display_cols].to_csv(index=False)
        st.download_button(
            label="📥 Download Top 50 Worst Drawdowns (CSV)",
            data=csv,
            file_name=f"sp500_top50_drawdowns_{period}.csv",
            mime="text/csv"
        )
    
    with tab5:
        st.markdown("### Complete S&P 500 Drawdown Dataset")
        st.info(f"📊 Total of {len(periods_df)} drawdown events across {len(summary_df)} stocks")
        
        # Add filters
        col1, col2, col3 = st.columns(3)
        with col1:
            min_dd = st.slider("Min Drawdown (%)", 0, 100, 0)
        with col2:
            selected_years = st.multiselect("Filter by Year", 
                                           options=sorted(pd.to_datetime(periods_df['Start']).dt.year.unique()),
                                           default=[])
        with col3:
            sort_by = st.selectbox("Sort by", ['Max Drawdown', 'Duration (days)', 'Recovery Time (days)'])
        
        # Apply filters
        filtered = periods_df.copy()
        filtered = filtered[abs(filtered['Max Drawdown'] * 100) >= min_dd]
        
        if selected_years:
            filtered['Year'] = pd.to_datetime(filtered['Start']).dt.year
            filtered = filtered[filtered['Year'].isin(selected_years)]
        
        filtered = filtered.sort_values(sort_by)
        
        # Format for display
        display_df = filtered.copy()
        display_df['Max Drawdown (%)'] = display_df['Max Drawdown'] * 100
        display_df['Start'] = pd.to_datetime(display_df['Start']).dt.strftime('%Y-%m-%d')
        display_df['Valley'] = pd.to_datetime(display_df['Valley']).dt.strftime('%Y-%m-%d')
        display_df['End'] = pd.to_datetime(display_df['End']).dt.strftime('%Y-%m-%d')
        
        display_cols = ['Symbol', 'Start', 'Valley', 'End', 'Max Drawdown (%)', 
                       'Duration (days)', 'Recovery Time (days)']
        
        st.dataframe(
            display_df[display_cols].style.format({
                'Max Drawdown (%)': '{:.2f}',
                'Duration (days)': '{:.0f}',
                'Recovery Time (days)': '{:.0f}'
            }),
            use_container_width=True,
            height=600,
            hide_index=True
        )
        
        st.metric("Filtered Results", f"{len(filtered)} drawdowns")
        
        # Download full dataset
        csv = display_df[display_cols].to_csv(index=False)
        st.download_button(
            label="📥 Download Filtered Data (CSV)",
            data=csv,
            file_name=f"sp500_all_drawdowns_{period}.csv",
            mime="text/csv"
        )

if __name__ == "__main__":
    main()
