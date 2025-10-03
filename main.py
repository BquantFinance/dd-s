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

# ==================== CONFIGURATION ====================
st.set_page_config(
    page_title="Drawdown Intelligence Lab",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== STYLING ====================
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stMetric { 
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        margin: 10px;
    }
    .insight-box {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 20px;
        border-radius: 15px;
        margin: 20px 0;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    .warning-box {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        padding: 20px;
        border-radius: 15px;
        margin: 20px 0;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    h1, h2, h3 { 
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
</style>
""", unsafe_allow_html=True)

# ==================== CORE FUNCTIONS ====================

def calculate_drawdowns(prices):
    """Calculate drawdown series from prices"""
    cummax = prices.expanding().max()
    drawdown = (prices - cummax) / cummax
    return drawdown

def get_drawdown_episodes(prices, threshold=-0.02):
    """Identify and analyze distinct drawdown episodes"""
    dd_series = calculate_drawdowns(prices)
    in_drawdown = dd_series < threshold
    
    # Group consecutive drawdown days
    dd_groups = (in_drawdown != in_drawdown.shift()).cumsum()
    
    episodes = []
    for group_id in dd_groups[in_drawdown].unique():
        mask = (dd_groups == group_id) & in_drawdown
        episode = dd_series[mask]
        
        if len(episode) < 2:  # Skip very short drawdowns
            continue
            
        # Get key dates
        start_idx = episode.index[0]
        start_price = prices.loc[start_idx]
        
        # Find the peak before drawdown
        pre_dd = prices[:start_idx]
        if len(pre_dd) > 0:
            peak_idx = pre_dd.index[-1]
            peak_price = pre_dd.iloc[-1]
        else:
            continue
            
        # Find the bottom
        bottom_idx = episode.idxmin()
        bottom_price = prices.loc[bottom_idx]
        
        # Find recovery (if any)
        post_dd = prices[prices.index > bottom_idx]
        recovery_mask = post_dd >= peak_price * 0.98  # Within 2% of peak
        
        if recovery_mask.any():
            recovery_idx = post_dd[recovery_mask].index[0]
            recovered = True
            recovery_days = (recovery_idx - bottom_idx).days
        else:
            recovery_idx = None
            recovered = False
            recovery_days = (prices.index[-1] - bottom_idx).days
        
        # Calculate metrics
        max_dd = episode.min()
        duration = (episode.index[-1] - episode.index[0]).days
        
        # Calculate velocity (how fast it fell)
        fall_days = (bottom_idx - start_idx).days
        velocity = abs(max_dd) / max(fall_days, 1)
        
        episodes.append({
            'start_date': start_idx,
            'peak_date': peak_idx,
            'bottom_date': bottom_idx,
            'end_date': episode.index[-1],
            'recovery_date': recovery_idx,
            'peak_price': peak_price,
            'bottom_price': bottom_price,
            'max_drawdown': max_dd,
            'duration_days': duration,
            'fall_days': fall_days,
            'recovery_days': recovery_days,
            'recovered': recovered,
            'velocity': velocity,
            'drawdown_series': episode
        })
    
    return sorted(episodes, key=lambda x: x['max_drawdown'])

def calculate_pain_index(drawdowns):
    """Calculate pain index - average drawdown over period"""
    return abs(drawdowns[drawdowns < 0].mean()) * 100 if len(drawdowns[drawdowns < 0]) > 0 else 0

def calculate_ulcer_index(drawdowns):
    """Calculate Ulcer Index - measures both depth and duration of drawdowns"""
    squared_dd = drawdowns ** 2
    return np.sqrt(squared_dd.mean()) * 100

def get_market_regime(prices, window=50):
    """Identify market regime (trending up/down/sideways)"""
    sma_short = prices.rolling(window=20).mean()
    sma_long = prices.rolling(window=window).mean()
    
    regime = pd.Series(index=prices.index, dtype='object')
    regime[sma_short > sma_long] = 'Bull'
    regime[sma_short < sma_long] = 'Bear'
    regime[abs(sma_short - sma_long) / sma_long < 0.02] = 'Sideways'
    
    return regime

# ==================== DATA LOADING ====================

@st.cache_data(ttl=3600)
def load_stock_data(symbol, period="2y"):
    """Load stock data from yfinance"""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        if data is not None and len(data) > 0 and 'Close' in data.columns:
            return data['Close'].dropna()
        return None
    except Exception as e:
        return None

@st.cache_data(ttl=86400)
def get_sp500_symbols():
    """Get S&P 500 symbols"""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    tables = pd.read_html(response.text)
    sp500_table = tables[0]
    symbols = sp500_table['Symbol'].str.replace('.', '-').tolist()
    return symbols

@st.cache_data(ttl=3600)
def load_index_components(symbols, period="2y"):
    """Load data for multiple symbols"""
    prices_dict = {}
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, symbol in enumerate(symbols[:100]):  # Limit to 100 for speed
        try:
            prices = load_stock_data(symbol, period)
            if prices is not None and len(prices) > 50:
                prices_dict[symbol] = prices
        except:
            continue
        
        progress_bar.progress((i + 1) / min(len(symbols), 100))
        status_text.text(f"Loading {symbol}...")
    
    progress_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(prices_dict)

# ==================== VISUALIZATION FUNCTIONS ====================

def create_underwater_chart(prices, episodes):
    """Create underwater breathing visualization"""
    dd_series = calculate_drawdowns(prices)
    
    fig = go.Figure()
    
    # Main underwater area
    fig.add_trace(go.Scatter(
        x=dd_series.index,
        y=dd_series.values * 100,
        fill='tozeroy',
        fillcolor='rgba(53, 92, 125, 0.6)',
        line=dict(color='rgb(53, 92, 125)', width=2),
        name='Underwater',
        hovertemplate='Date: %{x}<br>Depth: %{y:.1f}%<extra></extra>'
    ))
    
    # Add "oxygen levels" - deeper = more critical
    for episode in episodes[:5]:  # Top 5 worst
        depth = abs(episode['max_drawdown'] * 100)
        if depth > 20:
            color = 'rgba(255, 0, 0, 0.3)'
            label = '🔴 Critical'
        elif depth > 10:
            color = 'rgba(255, 165, 0, 0.3)'
            label = '🟠 Warning'
        else:
            color = 'rgba(255, 255, 0, 0.3)'
            label = '🟡 Caution'
        
        fig.add_vrect(
            x0=episode['start_date'],
            x1=episode['end_date'],
            fillcolor=color,
            layer='below',
            line_width=0,
            annotation_text=f"{depth:.1f}%",
            annotation_position="top"
        )
    
    # Surface line
    fig.add_hline(y=0, line_dash="dash", line_color="white", line_width=2, opacity=0.5)
    
    fig.update_layout(
        title={
            'text': "🏊 Underwater Breathing Chart<br><sub>How long can you hold your breath?</sub>",
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title="",
        yaxis_title="Depth (%)",
        height=400,
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font=dict(color='white'),
        hovermode='x unified',
        showlegend=False
    )
    
    fig.update_yaxis(gridcolor='#1e3a5f', zeroline=True, zerolinecolor='#4a90e2')
    fig.update_xaxis(gridcolor='#1e3a5f')
    
    return fig

def create_recovery_velocity_gauge(episodes):
    """Create speedometer-style recovery velocity visualization"""
    if not episodes:
        return None
    
    recent_episode = episodes[0]  # Most recent/severe
    
    if recent_episode['recovered']:
        # Calculate recovery velocity (% recovered per day)
        recovery_velocity = abs(recent_episode['max_drawdown']) / recent_episode['recovery_days'] * 100
        max_velocity = 2.0  # 2% per day is very fast
        velocity_pct = min(recovery_velocity / max_velocity * 100, 100)
    else:
        velocity_pct = 0
        recovery_velocity = 0
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=velocity_pct,
        title={'text': "Recovery Velocity<br><sub>Speed of comeback</sub>"},
        domain={'x': [0, 1], 'y': [0, 1]},
        number={'suffix': "%", 'valueformat': ".1f"},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "white"},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 25], 'color': "red"},
                {'range': [25, 50], 'color': "orange"},
                {'range': [50, 75], 'color': "yellow"},
                {'range': [75, 100], 'color': "lightgreen"}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(
        height=300,
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font=dict(color='white')
    )
    
    return fig

def create_pain_calendar(prices):
    """Create calendar heatmap of daily pain"""
    dd_series = calculate_drawdowns(prices) * 100
    
    # Prepare data for calendar
    df = pd.DataFrame({
        'date': dd_series.index,
        'drawdown': dd_series.values,
        'year': dd_series.index.year,
        'month': dd_series.index.month,
        'day': dd_series.index.day,
        'weekday': dd_series.index.weekday,
        'week': dd_series.index.isocalendar().week
    })
    
    # Create color scale
    colors = ['green', 'yellow', 'orange', 'red', 'darkred']
    boundaries = [0, -5, -10, -20, -30, -100]
    
    fig = px.density_heatmap(
        df, 
        x='week', 
        y='weekday',
        z='drawdown',
        color_continuous_scale=colors,
        labels={'weekday': 'Day', 'week': 'Week', 'drawdown': 'DD%'},
        title="📅 Pain Calendar - When It Hurts Most",
        height=400
    )
    
    fig.update_layout(
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font=dict(color='white')
    )
    
    return fig

def create_drawdown_story(episode, symbol):
    """Generate narrative for a drawdown episode"""
    depth = abs(episode['max_drawdown'] * 100)
    duration = episode['duration_days']
    
    # Generate relatable comparisons
    if depth > 50:
        comparison = "💀 Like losing half your life savings"
        severity = "catastrophic"
        emoji = "🚨"
    elif depth > 30:
        comparison = "😱 Like your house losing a year's worth of appreciation"
        severity = "severe"
        emoji = "⚠️"
    elif depth > 20:
        comparison = "😰 Like totaling your car"
        severity = "significant"
        emoji = "⚠️"
    elif depth > 10:
        comparison = "😟 Like an unexpected medical bill"
        severity = "moderate"
        emoji = "📉"
    else:
        comparison = "😐 Like a bad shopping spree"
        severity = "mild"
        emoji = "📊"
    
    # Recovery status
    if episode['recovered']:
        recovery_text = f"✅ **Recovered** in {episode['recovery_days']} days"
        if episode['recovery_days'] < 30:
            recovery_speed = "Lightning fast recovery! ⚡"
        elif episode['recovery_days'] < 90:
            recovery_speed = "Quick recovery 🏃"
        elif episode['recovery_days'] < 180:
            recovery_speed = "Steady recovery 🚶"
        else:
            recovery_speed = "Long road to recovery 🐢"
    else:
        days_underwater = (datetime.now().date() - episode['bottom_date'].date()).days
        recovery_text = f"❌ **Still underwater** for {days_underwater} days"
        recovery_speed = "Still waiting for recovery... ⏳"
    
    story = f"""
    ### {emoji} The {episode['start_date'].strftime('%B %Y')} {severity.title()} Drawdown
    
    **The Damage:** -{depth:.1f}% in {episode['fall_days']} days  
    **Relatable Pain:** {comparison}  
    **Total Duration:** {duration} days underwater  
    {recovery_text}  
    **Recovery Speed:** {recovery_speed}  
    
    **What $10,000 became:** ${10000 * (1 + episode['max_drawdown']):.0f}  
    **Velocity:** Falling at {episode['velocity']*100:.1f}% per day
    """
    
    return story

def create_decision_helper(current_dd, episodes):
    """Create a 'Should I Worry?' decision helper"""
    
    # Historical context
    if episodes:
        worse_episodes = sum(1 for e in episodes if e['max_drawdown'] < current_dd)
        percentile = (worse_episodes / len(episodes)) * 100
    else:
        percentile = 0
    
    # Decision logic
    if current_dd > -2:
        status = "🟢 **All Clear**"
        action = "Normal market noise. Stay the course."
        color = "green"
    elif current_dd > -5:
        status = "🟡 **Minor Turbulence**"
        action = "No action needed. This is normal."
        color = "yellow"
    elif current_dd > -10:
        status = "🟠 **Caution Zone**"
        action = "Review your risk tolerance. Consider your timeline."
        color = "orange"
    elif current_dd > -20:
        status = "🔴 **Significant Drawdown**"
        action = "Don't panic sell. Review your investment thesis."
        color = "red"
    else:
        status = "💀 **Major Drawdown**"
        action = "Crisis mode. Stick to your plan, history shows recovery."
        color = "darkred"
    
    return {
        'status': status,
        'action': action,
        'percentile': percentile,
        'color': color,
        'current_dd': current_dd
    }

def create_comparison_chart(prices_dict, episodes_dict):
    """Compare multiple stocks' drawdown behavior"""
    fig = go.Figure()
    
    colors = px.colors.qualitative.Set1
    
    for i, (symbol, prices) in enumerate(prices_dict.items()):
        dd = calculate_drawdowns(prices) * 100
        
        fig.add_trace(go.Scatter(
            x=dd.index,
            y=dd.values,
            name=symbol,
            line=dict(color=colors[i % len(colors)], width=2),
            opacity=0.7,
            hovertemplate=f'{symbol}<br>Date: %{{x}}<br>DD: %{{y:.1f}}%<extra></extra>'
        ))
    
    fig.update_layout(
        title="Drawdown Comparison - Who Handles Pain Better?",
        xaxis_title="",
        yaxis_title="Drawdown (%)",
        height=500,
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font=dict(color='white'),
        hovermode='x unified',
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor='rgba(0,0,0,0.5)'
        )
    )
    
    fig.update_yaxis(gridcolor='#1e3a5f', zeroline=True, zerolinecolor='#4a90e2')
    fig.update_xaxis(gridcolor='#1e3a5f')
    
    return fig

# ==================== MAIN APP ====================

def main():
    # Header
    st.markdown("""
    <h1 style='text-align: center; font-size: 3em; margin-bottom: 0;'>
    🌊 Drawdown Intelligence Lab
    </h1>
    <p style='text-align: center; color: #8b92a8; font-size: 1.2em; margin-top: 0;'>
    Understanding market pain through stories, not just statistics
    </p>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 🎛️ Control Panel")
        
        analysis_mode = st.radio(
            "Analysis Mode",
            ["🎯 Individual Stock", "📊 Index Comparison", "🏆 S&P 500 Analysis"],
            help="Choose your analysis type"
        )
        
        period = st.selectbox(
            "Time Machine Setting",
            ["6mo", "1y", "2y", "5y", "max"],
            index=2,
            help="How far back to analyze"
        )
        
        if analysis_mode == "🎯 Individual Stock":
            symbol = st.text_input("Stock Symbol", "AAPL").upper()
            symbols = [symbol]
        elif analysis_mode == "📊 Index Comparison":
            symbols = st.multiselect(
                "Select Stocks to Compare",
                options=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'V', 'JNJ'],
                default=['AAPL', 'MSFT', 'GOOGL']
            )
        else:
            if st.button("🔄 Load S&P 500", type="primary"):
                with st.spinner("Loading the entire S&P 500..."):
                    st.session_state['sp500_symbols'] = get_sp500_symbols()
            symbols = st.session_state.get('sp500_symbols', [])[:50]  # Limit for demo
        
        analyze_btn = st.button("🚀 Analyze", type="primary", use_container_width=True)
        
        st.markdown("---")
        
        # Educational content
        with st.expander("📚 What is a Drawdown?"):
            st.markdown("""
            A **drawdown** is the peak-to-trough decline during a specific period.
            
            Think of it as:
            - 📉 How much you're "underwater" from your highest point
            - 😰 The pain you feel watching your portfolio drop
            - ⏳ The patience test while waiting for recovery
            
            **Why it matters:**
            - Reveals true risk (volatility doesn't tell the whole story)
            - Tests your emotional resilience
            - Helps size positions appropriately
            """)
    
    # Main content
    if analyze_btn and symbols:
        if analysis_mode == "🎯 Individual Stock":
            display_individual_analysis(symbols[0], period)
        elif analysis_mode == "📊 Index Comparison":
            display_comparison_analysis(symbols, period)
        else:
            display_sp500_analysis(symbols, period)
    else:
        # Welcome screen
        st.markdown("""
        <div style='text-align: center; padding: 50px;'>
            <h2>Welcome to the Drawdown Intelligence Lab</h2>
            <p style='font-size: 1.2em; color: #8b92a8;'>
            Where we turn market pain into actionable insights
            </p>
            
            <div style='margin-top: 50px;'>
                <h3>Choose Your Adventure:</h3>
                <p>🎯 <b>Individual Stock</b> - Deep dive into one stock's pain points</p>
                <p>📊 <b>Index Comparison</b> - Compare how different stocks handle drawdowns</p>
                <p>🏆 <b>S&P 500 Analysis</b> - Market-wide pain assessment</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

def display_individual_analysis(symbol, period):
    """Display analysis for individual stock"""
    
    prices = load_stock_data(symbol, period)
    
    if prices is None or len(prices) < 50:
        st.error(f"Unable to load sufficient data for {symbol}")
        return
    
    episodes = get_drawdown_episodes(prices)
    current_dd = calculate_drawdowns(prices).iloc[-1] * 100
    
    # Hero metrics
    st.markdown("### 🎯 Current Situation")
    
    decision = create_decision_helper(current_dd, episodes)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <h3>{decision['status']}</h3>
            <p style='font-size: 2em; margin: 0;'>{current_dd:.1f}%</p>
            <p style='margin: 0;'>Current Drawdown</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        worst_dd = min(e['max_drawdown'] for e in episodes) * 100 if episodes else 0
        st.markdown(f"""
        <div class='metric-card'>
            <h3>😱 Worst Ever</h3>
            <p style='font-size: 2em; margin: 0;'>{worst_dd:.1f}%</p>
            <p style='margin: 0;'>Maximum Pain</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        pain_index = calculate_pain_index(calculate_drawdowns(prices))
        st.markdown(f"""
        <div class='metric-card'>
            <h3>💊 Pain Index</h3>
            <p style='font-size: 2em; margin: 0;'>{pain_index:.1f}</p>
            <p style='margin: 0;'>Average Pain</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        if episodes:
            recovery_rate = sum(1 for e in episodes if e['recovered']) / len(episodes) * 100
        else:
            recovery_rate = 0
        st.markdown(f"""
        <div class='metric-card'>
            <h3>💪 Recovery Rate</h3>
            <p style='font-size: 2em; margin: 0;'>{recovery_rate:.0f}%</p>
            <p style='margin: 0;'>Comeback Ratio</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Decision helper box
    st.markdown(f"""
    <div class='insight-box'>
        <h3>🤔 What Should You Do?</h3>
        <p><b>{decision['action']}</b></p>
        <p>This drawdown is worse than {decision['percentile']:.0f}% of historical drawdowns.</p>
        <p>Remember: Every drawdown feels like the worst one when you're in it.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Main visualizations
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏊 Underwater View", "📖 Drawdown Stories", "📊 Analytics", "🎯 Decision Tools"
    ])
    
    with tab1:
        st.plotly_chart(create_underwater_chart(prices, episodes), use_container_width=True)
        
        if episodes and episodes[0]['recovered']:
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(create_recovery_velocity_gauge(episodes), use_container_width=True)
            with col2:
                # Recovery stats
                recoveries = [e for e in episodes if e['recovered']]
                if recoveries:
                    avg_recovery = np.mean([e['recovery_days'] for e in recoveries])
                    st.markdown(f"""
                    <div class='metric-card'>
                        <h3>⏱️ Recovery Stats</h3>
                        <p>Average: {avg_recovery:.0f} days</p>
                        <p>Fastest: {min(e['recovery_days'] for e in recoveries)} days</p>
                        <p>Slowest: {max(e['recovery_days'] for e in recoveries)} days</p>
                    </div>
                    """, unsafe_allow_html=True)
    
    with tab2:
        st.markdown("### 📚 Your Drawdown History")
        
        if episodes:
            # Show stories for top 3 worst drawdowns
            for i, episode in enumerate(episodes[:3], 1):
                with st.expander(f"Story #{i}: {episode['start_date'].strftime('%B %Y')} Drawdown"):
                    st.markdown(create_drawdown_story(episode, symbol))
                    
                    # Mini chart for this episode
                    fig = go.Figure()
                    
                    # Get price series for this episode period
                    episode_start = episode['peak_date']
                    episode_end = episode['recovery_date'] if episode['recovery_date'] else prices.index[-1]
                    episode_prices = prices[episode_start:episode_end]
                    
                    fig.add_trace(go.Scatter(
                        x=episode_prices.index,
                        y=episode_prices.values,
                        mode='lines',
                        line=dict(color='lightblue', width=2),
                        name='Price'
                    ))
                    
                    # Mark key points
                    fig.add_trace(go.Scatter(
                        x=[episode['peak_date'], episode['bottom_date']],
                        y=[episode['peak_price'], episode['bottom_price']],
                        mode='markers+text',
                        marker=dict(size=10, color=['green', 'red']),
                        text=['Peak', 'Bottom'],
                        textposition='top center',
                        showlegend=False
                    ))
                    
                    fig.update_layout(
                        height=300,
                        plot_bgcolor='#0e1117',
                        paper_bgcolor='#0e1117',
                        font=dict(color='white'),
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No significant drawdowns found in this period!")
    
    with tab3:
        # Detailed analytics
        st.markdown("### 📈 Deep Analytics")
        
        # Regime analysis
        regime = get_market_regime(prices)
        regime_counts = regime.value_counts()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Regime pie chart
            fig = go.Figure(data=[go.Pie(
                labels=regime_counts.index,
                values=regime_counts.values,
                marker=dict(colors=['green', 'red', 'gray']),
                hole=0.3
            )])
            
            fig.update_layout(
                title="Market Regime Distribution",
                height=300,
                plot_bgcolor='#0e1117',
                paper_bgcolor='#0e1117',
                font=dict(color='white')
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Drawdown distribution
            if episodes:
                dd_magnitudes = [abs(e['max_drawdown']) * 100 for e in episodes]
                
                fig = go.Figure(data=[go.Histogram(
                    x=dd_magnitudes,
                    nbinsx=20,
                    marker=dict(color='lightcoral')
                )])
                
                fig.update_layout(
                    title="Drawdown Magnitude Distribution",
                    xaxis_title="Drawdown (%)",
                    yaxis_title="Frequency",
                    height=300,
                    plot_bgcolor='#0e1117',
                    paper_bgcolor='#0e1117',
                    font=dict(color='white')
                )
                
                st.plotly_chart(fig, use_container_width=True)
        
        # Statistics table
        if episodes:
            stats_df = pd.DataFrame({
                'Metric': [
                    'Number of Drawdowns',
                    'Average Drawdown (%)',
                    'Average Duration (days)',
                    'Average Recovery (days)',
                    'Worst Month',
                    'Best Month After Drawdown'
                ],
                'Value': [
                    len(episodes),
                    f"{np.mean([abs(e['max_drawdown']) * 100 for e in episodes]):.1f}%",
                    f"{np.mean([e['duration_days'] for e in episodes]):.0f}",
                    f"{np.mean([e['recovery_days'] for e in episodes if e['recovered']]):.0f}",
                    calculate_drawdowns(prices).groupby(pd.Grouper(freq='M')).min().idxmin().strftime('%B %Y'),
                    "Coming soon"
                ]
            })
            
            st.table(stats_df)
    
    with tab4:
        st.markdown("### 🎯 Decision Support Tools")
        
        # Risk tolerance calculator
        st.markdown("""
        <div class='warning-box'>
            <h3>🎰 Your Risk Reality Check</h3>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            investment = st.number_input("Your Investment ($)", value=10000, step=1000)
            tolerance = st.slider("Max Loss You Can Stomach (%)", 0, 50, 20)
        
        with col2:
            if episodes:
                worst = abs(min(e['max_drawdown'] for e in episodes) * 100)
                potential_loss = investment * worst / 100
                
                if worst > tolerance:
                    st.error(f"""
                    ⚠️ **Reality Check!**  
                    Historical worst: -{worst:.1f}%  
                    Your tolerance: -{tolerance}%  
                    You'd lose: ${potential_loss:.0f}  
                    
                    **You might want to reconsider your position size!**
                    """)
                else:
                    st.success(f"""
                    ✅ **Within Tolerance**  
                    Historical worst: -{worst:.1f}%  
                    Your tolerance: -{tolerance}%  
                    Max historical loss: ${potential_loss:.0f}
                    """)
        
        # Historical comparison tool
        st.markdown("### 🕰️ Time Machine: What If You Bought At...")
        
        if episodes and len(episodes) > 0:
            selected_episode = st.selectbox(
                "Select a historical peak",
                options=range(len(episodes)),
                format_func=lambda i: f"{episodes[i]['peak_date'].strftime('%B %Y')} (fell {abs(episodes[i]['max_drawdown']*100):.1f}%)"
            )
            
            episode = episodes[selected_episode]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("You'd be down", f"{abs(episode['max_drawdown']*100):.1f}%")
            with col2:
                st.metric("For this many days", f"{episode['duration_days']}")
            with col3:
                if episode['recovered']:
                    st.metric("Recovery took", f"{episode['recovery_days']} days")
                else:
                    st.metric("Still waiting", "Not recovered")

def display_comparison_analysis(symbols, period):
    """Display comparison analysis for multiple stocks"""
    
    st.markdown("### 🏁 Drawdown Race: Who Handles Pain Better?")
    
    prices_dict = {}
    episodes_dict = {}
    
    # Load data
    progress = st.progress(0)
    for i, symbol in enumerate(symbols):
        prices = load_stock_data(symbol, period)
        if prices is not None and len(prices) > 50:
            prices_dict[symbol] = prices
            episodes_dict[symbol] = get_drawdown_episodes(prices)
        progress.progress((i + 1) / len(symbols))
    progress.empty()
    
    if not prices_dict:
        st.error("Unable to load data for selected symbols")
        return
    
    # Comparison metrics
    comparison_data = []
    for symbol, episodes in episodes_dict.items():
        if episodes:
            comparison_data.append({
                'Symbol': symbol,
                'Current DD (%)': calculate_drawdowns(prices_dict[symbol]).iloc[-1] * 100,
                'Worst DD (%)': min(e['max_drawdown'] for e in episodes) * 100,
                'Avg DD (%)': np.mean([e['max_drawdown'] for e in episodes]) * 100,
                'Pain Index': calculate_pain_index(calculate_drawdowns(prices_dict[symbol])),
                'Recovery Rate (%)': sum(1 for e in episodes if e['recovered']) / len(episodes) * 100,
                'Avg Recovery (days)': np.mean([e['recovery_days'] for e in episodes if e['recovered']]) if any(e['recovered'] for e in episodes) else 0
            })
    
    comparison_df = pd.DataFrame(comparison_data)
    
    # Display rankings
    st.markdown("### 🏆 Performance Rankings")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🛡️ Most Resilient** (Smallest worst DD)")
        winner = comparison_df.nlargest(1, 'Worst DD (%)').iloc[0]
        st.success(f"👑 {winner['Symbol']}: {winner['Worst DD (%)']:.1f}%")
    
    with col2:
        st.markdown("**💊 Least Painful** (Lowest pain index)")
        winner = comparison_df.nsmallest(1, 'Pain Index').iloc[0]
        st.success(f"👑 {winner['Symbol']}: {winner['Pain Index']:.1f}")
    
    with col3:
        st.markdown("**⚡ Fastest Recovery** (Avg days)")
        winner = comparison_df.nsmallest(1, 'Avg Recovery (days)').iloc[0]
        st.success(f"👑 {winner['Symbol']}: {winner['Avg Recovery (days)']:.0f} days")
    
    # Comparison chart
    st.plotly_chart(create_comparison_chart(prices_dict, episodes_dict), use_container_width=True)
    
    # Detailed comparison table
    st.markdown("### 📊 Detailed Comparison")
    
    st.dataframe(
        comparison_df.style.format({
            'Current DD (%)': '{:.1f}',
            'Worst DD (%)': '{:.1f}',
            'Avg DD (%)': '{:.1f}',
            'Pain Index': '{:.1f}',
            'Recovery Rate (%)': '{:.0f}',
            'Avg Recovery (days)': '{:.0f}'
        }).background_gradient(cmap='RdYlGn_r', subset=['Current DD (%)', 'Worst DD (%)', 'Pain Index'])
          .background_gradient(cmap='RdYlGn', subset=['Recovery Rate (%)']),
        use_container_width=True
    )
    
    # Head-to-head battles
    st.markdown("### ⚔️ Head-to-Head Battles")
    
    if len(symbols) >= 2:
        col1, col2 = st.columns(2)
        
        with col1:
            fighter1 = st.selectbox("Fighter 1", symbols, index=0)
        with col2:
            fighter2 = st.selectbox("Fighter 2", symbols, index=1)
        
        if fighter1 != fighter2:
            f1_data = comparison_df[comparison_df['Symbol'] == fighter1].iloc[0]
            f2_data = comparison_df[comparison_df['Symbol'] == fighter2].iloc[0]
            
            battles = [
                ('Current Position', 'Current DD (%)', True),  # True means lower is better
                ('Historical Toughness', 'Worst DD (%)', False),  # False means higher is better
                ('Pain Tolerance', 'Pain Index', True),
                ('Recovery Power', 'Recovery Rate (%)', False),
                ('Speed', 'Avg Recovery (days)', True)
            ]
            
            f1_wins = 0
            f2_wins = 0
            
            for battle_name, metric, lower_better in battles:
                if lower_better:
                    winner = fighter1 if f1_data[metric] < f2_data[metric] else fighter2
                    if winner == fighter1:
                        f1_wins += 1
                    else:
                        f2_wins += 1
                else:
                    winner = fighter1 if f1_data[metric] > f2_data[metric] else fighter2
                    if winner == fighter1:
                        f1_wins += 1
                    else:
                        f2_wins += 1
                
                col1, col2, col3 = st.columns([2, 1, 2])
                with col1:
                    if winner == fighter1:
                        st.success(f"{fighter1}: {f1_data[metric]:.1f}")
                    else:
                        st.error(f"{fighter1}: {f1_data[metric]:.1f}")
                with col2:
                    st.markdown(f"**{battle_name}**")
                with col3:
                    if winner == fighter2:
                        st.success(f"{fighter2}: {f2_data[metric]:.1f}")
                    else:
                        st.error(f"{fighter2}: {f2_data[metric]:.1f}")
            
            st.markdown(f"### 🏆 Winner: {fighter1 if f1_wins > f2_wins else fighter2} ({max(f1_wins, f2_wins)}-{min(f1_wins, f2_wins)})")

def display_sp500_analysis(symbols, period):
    """Display S&P 500 aggregate analysis"""
    
    st.markdown("### 🌍 Market-Wide Pain Assessment")
    
    # Load data for symbols
    prices_df = load_index_components(symbols, period)
    
    if prices_df.empty:
        st.error("Unable to load S&P 500 data")
        return
    
    # Calculate aggregate metrics
    all_episodes = []
    current_dds = []
    
    for symbol in prices_df.columns:
        dd = calculate_drawdowns(prices_df[symbol])
        current_dds.append(dd.iloc[-1] * 100)
        
        episodes = get_drawdown_episodes(prices_df[symbol])
        for episode in episodes:
            episode['symbol'] = symbol
            all_episodes.append(episode)
    
    # Market health dashboard
    st.markdown("### 🏥 Market Health Status")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_dd = np.mean(current_dds)
        health_color = "🟢" if avg_dd > -5 else "🟡" if avg_dd > -10 else "🟠" if avg_dd > -20 else "🔴"
        st.markdown(f"""
        <div class='metric-card'>
            <h3>{health_color} Market Health</h3>
            <p style='font-size: 2em;'>{avg_dd:.1f}%</p>
            <p>Average DD</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        stocks_in_dd = sum(1 for dd in current_dds if dd < -10)
        pct_in_dd = (stocks_in_dd / len(current_dds)) * 100
        st.markdown(f"""
        <div class='metric-card'>
            <h3>📊 Stocks Hurting</h3>
            <p style='font-size: 2em;'>{pct_in_dd:.0f}%</p>
            <p>In 10%+ DD</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        if all_episodes:
            recent_episodes = [e for e in all_episodes if (datetime.now().date() - e['start_date'].date()).days < 90]
            st.markdown(f"""
            <div class='metric-card'>
                <h3>🌊 Recent Events</h3>
                <p style='font-size: 2em;'>{len(recent_episodes)}</p>
                <p>Last 90 days</p>
            </div>
            """, unsafe_allow_html=True)
        
    with col4:
        bear_market = sum(1 for dd in current_dds if dd < -20)
        bear_pct = (bear_market / len(current_dds)) * 100
        st.markdown(f"""
        <div class='metric-card'>
            <h3>🐻 Bear Territory</h3>
            <p style='font-size: 2em;'>{bear_pct:.0f}%</p>
            <p>In 20%+ DD</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Market mood assessment
    if avg_dd > -5:
        mood = "😊 Euphoric - Markets feeling great!"
        mood_color = "green"
    elif avg_dd > -10:
        mood = "😐 Cautious - Some nervousness creeping in"
        mood_color = "yellow"
    elif avg_dd > -20:
        mood = "😰 Fearful - Significant stress in the system"
        mood_color = "orange"
    else:
        mood = "😱 Panic - Maximum fear, potential opportunity?"
        mood_color = "red"
    
    st.markdown(f"""
    <div class='insight-box'>
        <h2>Market Mood: {mood}</h2>
        <p>Based on {len(current_dds)} stocks analyzed</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Worst performers
    st.markdown("### 💀 Walking Wounded (Worst Current Drawdowns)")
    
    worst_current = pd.DataFrame({
        'Symbol': prices_df.columns,
        'Current DD (%)': current_dds
    }).nsmallest(10, 'Current DD (%)')
    
    fig = go.Figure(data=[go.Bar(
        x=worst_current['Symbol'],
        y=worst_current['Current DD (%)'],
        marker=dict(color=worst_current['Current DD (%)'],
                   colorscale='Reds',
                   showscale=False),
        text=[f"{dd:.1f}%" for dd in worst_current['Current DD (%)']],
        textposition='auto'
    )])
    
    fig.update_layout(
        title="Bottom 10 - Currently Suffering Most",
        height=400,
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font=dict(color='white')
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Historical perspective
    if all_episodes:
        st.markdown("### 📜 Historical Perspective")
        
        # Group by year
        episodes_df = pd.DataFrame(all_episodes)
        episodes_df['year'] = pd.to_datetime(episodes_df['start_date']).dt.year
        
        yearly_stats = episodes_df.groupby('year').agg({
            'max_drawdown': ['count', 'mean'],
            'recovery_days': 'mean'
        }).round(1)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📅 Drawdowns by Year**")
            st.bar_chart(yearly_stats[('max_drawdown', 'count')])
        
        with col2:
            st.markdown("**😰 Average Pain by Year**")
            st.line_chart(abs(yearly_stats[('max_drawdown', 'mean')] * 100))

if __name__ == "__main__":
    main()
