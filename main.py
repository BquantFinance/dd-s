import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import seaborn as sns
import matplotlib.pyplot as plt

# ==================== CONFIGURACIÓN DE PÁGINA ====================
st.set_page_config(
    page_title="Análisis de Drawdown - S&P 500",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CSS COMPLETO - DARK MODE PROFESIONAL ====================
st.markdown("""
<style>
    /* ============================================
       IMPORTAR FUENTE PROFESIONAL
       ============================================ */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* ============================================
       VARIABLES DE COLOR - PALETA PROFESIONAL
       ============================================ */
    :root {
        --bg-primary: #0a0e1a;
        --bg-secondary: #141824;
        --bg-tertiary: #1e2230;
        --bg-card: #252936;
        
        --text-primary: #f0f0f0;
        --text-secondary: #a0a6b8;
        --text-tertiary: #6b7280;
        
        --accent-red: #ef4444;
        --accent-red-dark: #dc2626;
        --accent-red-light: #f87171;
        
        --accent-green: #10b981;
        --accent-blue: #3b82f6;
        --accent-yellow: #fbbf24;
        --accent-purple: #a855f7;
        
        --border-color: #2d3344;
        --border-light: #374151;
        
        --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.5);
        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
        --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.6);
        --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.7);
    }
    
    /* ============================================
       FONDO PRINCIPAL Y BODY
       ============================================ */
    .stApp {
        background: linear-gradient(135deg, #0a0e1a 0%, #141824 50%, #0a0e1a 100%);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--text-primary);
    }
    
    .main {
        background-color: transparent;
    }
    
    /* ============================================
       TIPOGRAFÍA - TÍTULOS Y TEXTO
       ============================================ */
    h1 {
        color: var(--text-primary) !important;
        font-weight: 800 !important;
        font-size: 3.5rem !important;
        margin-bottom: 0.5rem !important;
        letter-spacing: -2px !important;
        text-align: center;
    }
    
    h2 {
        color: var(--text-primary) !important;
        font-weight: 700 !important;
        font-size: 2.2rem !important;
        margin-top: 3rem !important;
        margin-bottom: 1.5rem !important;
        letter-spacing: -0.5px !important;
    }
    
    h3 {
        color: var(--text-secondary) !important;
        font-weight: 600 !important;
        font-size: 1.5rem !important;
        margin-top: 2rem !important;
        margin-bottom: 1rem !important;
    }
    
    p {
        color: var(--text-secondary) !important;
        line-height: 1.6 !important;
        font-size: 1rem !important;
    }
    
    /* ============================================
       SIDEBAR - MENÚ LATERAL
       ============================================ */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #141824 0%, #0a0e1a 100%) !important;
        border-right: 2px solid var(--border-color) !important;
        box-shadow: var(--shadow-xl);
    }
    
    [data-testid="stSidebar"] > div:first-child {
        background: transparent !important;
    }
    
    [data-testid="stSidebar"] .stRadio > label {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        margin-bottom: 1rem !important;
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: var(--text-primary) !important;
    }
    
    /* ============================================
       MÉTRICAS - TARJETAS DE ESTADÍSTICAS
       ============================================ */
    [data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        color: var(--text-primary) !important;
        letter-spacing: -1px !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.875rem !important;
        color: var(--text-tertiary) !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
    }
    
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-tertiary) 100%);
        padding: 1.5rem 1.2rem;
        border-radius: 16px;
        border: 1px solid var(--border-color);
        box-shadow: var(--shadow-lg);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(10px);
    }
    
    div[data-testid="metric-container"]:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-xl);
        border-color: var(--accent-blue);
        background: linear-gradient(135deg, var(--bg-tertiary) 0%, var(--bg-card) 100%);
    }
    
    /* ============================================
       INPUTS Y SELECTORES
       ============================================ */
    .stSelectbox > div > div,
    .stMultiSelect > div > div,
    .stDateInput > div > div,
    .stTextInput > div > div {
        background-color: var(--bg-card) !important;
        border: 2px solid var(--border-color) !important;
        border-radius: 12px !important;
        color: var(--text-primary) !important;
        font-weight: 500 !important;
        transition: all 0.2s ease;
    }
    
    .stSelectbox > div > div:hover,
    .stMultiSelect > div > div:hover {
        border-color: var(--accent-blue) !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    .stSelectbox label,
    .stMultiSelect label,
    .stDateInput label {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* ============================================
       RADIO BUTTONS
       ============================================ */
    .stRadio > div {
        background-color: var(--bg-secondary);
        padding: 1.2rem;
        border-radius: 14px;
        border: 2px solid var(--border-color);
        box-shadow: var(--shadow-md);
    }
    
    .stRadio > div > label {
        color: var(--text-primary) !important;
        font-weight: 500 !important;
        padding: 0.6rem 1rem;
        border-radius: 8px;
        transition: all 0.2s ease;
        cursor: pointer;
    }
    
    .stRadio > div > label:hover {
        background-color: var(--bg-tertiary);
    }
    
    .stRadio > div > label > div[role="radio"] {
        background-color: var(--bg-card) !important;
        border: 2px solid var(--border-light) !important;
        width: 20px !important;
        height: 20px !important;
    }
    
    .stRadio > div > label > div[role="radio"][data-checked="true"] {
        background-color: var(--accent-blue) !important;
        border-color: var(--accent-blue) !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
    }
    
    /* ============================================
       SLIDER
       ============================================ */
    .stSlider {
        padding: 1rem 0;
    }
    
    .stSlider > div > div > div > div {
        background-color: var(--accent-blue) !important;
    }
    
    .stSlider > div > div > div {
        background-color: var(--border-color) !important;
    }
    
    .stSlider label {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }
    
    /* ============================================
       DATAFRAMES Y TABLAS
       ============================================ */
    [data-testid="stDataFrame"] {
        background-color: var(--bg-secondary) !important;
        border: 2px solid var(--border-color) !important;
        border-radius: 14px !important;
        box-shadow: var(--shadow-lg);
        overflow: hidden;
    }
    
    [data-testid="stDataFrame"] th {
        background: linear-gradient(135deg, var(--bg-tertiary) 0%, var(--bg-card) 100%) !important;
        color: var(--text-primary) !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-size: 0.85rem !important;
        padding: 1rem !important;
        border-bottom: 2px solid var(--border-light) !important;
    }
    
    [data-testid="stDataFrame"] td {
        color: var(--text-secondary) !important;
        padding: 0.8rem 1rem !important;
        font-weight: 500 !important;
        border-bottom: 1px solid var(--border-color) !important;
    }
    
    [data-testid="stDataFrame"] tr:hover {
        background-color: var(--bg-tertiary) !important;
    }
    
    /* ============================================
       MENSAJES - SUCCESS, ERROR, WARNING, INFO
       ============================================ */
    .stSuccess {
        background: linear-gradient(90deg, rgba(16, 185, 129, 0.15) 0%, rgba(16, 185, 129, 0.05) 100%) !important;
        border-left: 4px solid var(--accent-green) !important;
        color: var(--accent-green) !important;
        border-radius: 12px !important;
        padding: 1rem 1.5rem !important;
        font-weight: 600 !important;
        box-shadow: var(--shadow-md);
    }
    
    .stError {
        background: linear-gradient(90deg, rgba(239, 68, 68, 0.15) 0%, rgba(239, 68, 68, 0.05) 100%) !important;
        border-left: 4px solid var(--accent-red) !important;
        color: var(--accent-red-light) !important;
        border-radius: 12px !important;
        padding: 1rem 1.5rem !important;
        font-weight: 600 !important;
        box-shadow: var(--shadow-md);
    }
    
    .stWarning {
        background: linear-gradient(90deg, rgba(251, 191, 36, 0.15) 0%, rgba(251, 191, 36, 0.05) 100%) !important;
        border-left: 4px solid var(--accent-yellow) !important;
        color: var(--accent-yellow) !important;
        border-radius: 12px !important;
        padding: 1rem 1.5rem !important;
        font-weight: 600 !important;
        box-shadow: var(--shadow-md);
    }
    
    .stInfo {
        background: linear-gradient(90deg, rgba(59, 130, 246, 0.15) 0%, rgba(59, 130, 246, 0.05) 100%) !important;
        border-left: 4px solid var(--accent-blue) !important;
        color: var(--accent-blue) !important;
        border-radius: 12px !important;
        padding: 1rem 1.5rem !important;
        font-weight: 600 !important;
        box-shadow: var(--shadow-md);
    }
    
    /* ============================================
       BOTONES
       ============================================ */
    .stButton > button {
        background: linear-gradient(135deg, var(--accent-blue) 0%, #2563eb 100%);
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        letter-spacing: 0.5px !important;
        transition: all 0.3s ease;
        box-shadow: var(--shadow-md);
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #2563eb 0%, var(--accent-blue) 100%);
        transform: translateY(-2px);
        box-shadow: var(--shadow-lg);
    }
    
    /* ============================================
       TABS
       ============================================ */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: var(--bg-secondary);
        padding: 0.8rem;
        border-radius: 14px;
        border: 2px solid var(--border-color);
        box-shadow: var(--shadow-md);
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 10px;
        color: var(--text-secondary);
        font-weight: 600;
        padding: 0.8rem 1.8rem;
        transition: all 0.2s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: var(--bg-tertiary);
        color: var(--text-primary);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--accent-blue) 0%, #2563eb 100%) !important;
        color: white !important;
        box-shadow: var(--shadow-md);
    }
    
    /* ============================================
       SPINNER - LOADING
       ============================================ */
    .stSpinner > div {
        border-top-color: var(--accent-blue) !important;
        border-right-color: var(--accent-blue) !important;
    }
    
    /* ============================================
       SEPARADORES
       ============================================ */
    hr {
        border: none !important;
        border-top: 2px solid var(--border-color) !important;
        margin: 3rem 0 !important;
        opacity: 0.5;
    }
    
    /* ============================================
       SCROLLBAR PERSONALIZADO
       ============================================ */
    ::-webkit-scrollbar {
        width: 12px;
        height: 12px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-secondary);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, var(--border-light) 0%, var(--border-color) 100%);
        border-radius: 10px;
        border: 2px solid var(--bg-secondary);
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, var(--accent-blue) 0%, #2563eb 100%);
    }
    
    /* ============================================
       OCULTAR ELEMENTOS DE STREAMLIT
       ============================================ */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* ============================================
       CONTENEDOR PRINCIPAL
       ============================================ */
    .block-container {
        padding-top: 3rem !important;
        padding-bottom: 3rem !important;
        padding-left: 3rem !important;
        padding-right: 3rem !important;
        max-width: 100% !important;
    }
    
    /* ============================================
       ANIMACIONES
       ============================================ */
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .element-container {
        animation: fadeIn 0.5s ease-out;
    }
    
    /* ============================================
       EXPANDER
       ============================================ */
    .streamlit-expanderHeader {
        background-color: var(--bg-card) !important;
        border-radius: 12px !important;
        border: 2px solid var(--border-color) !important;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }
    
    .streamlit-expanderHeader:hover {
        border-color: var(--accent-blue) !important;
    }
    
    /* ============================================
       MULTISELECT TAGS
       ============================================ */
    .stMultiSelect [data-baseweb="tag"] {
        background-color: var(--accent-blue) !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==================== TÍTULO PRINCIPAL ====================
st.markdown("""
    <div style='text-align: center; padding: 2rem 0 3rem 0;'>
        <h1>📉 ANÁLISIS DE DRAWDOWN</h1>
        <h3 style='color: #a0a6b8; font-weight: 400; margin-top: 0;'>S&P 500 · Análisis Individual y Agregado del Mercado</h3>
    </div>
""", unsafe_allow_html=True)

# ==================== CARGAR DATOS ====================
@st.cache_data
def load_data():
    df = pd.read_csv('sp500_companies.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    return df

try:
    df = load_data()
    st.success(f"✅ Datos cargados exitosamente: {len(df):,} días de trading | {len(df.columns):,} acciones del S&P 500")
except Exception as e:
    st.error(f"❌ Error al cargar 'sp500_companies.csv': {str(e)}")
    st.stop()

# ==================== CONFIGURACIÓN SIDEBAR ====================
st.sidebar.markdown("### ⚙️ CONFIGURACIÓN")
st.sidebar.markdown("---")

analysis_type = st.sidebar.radio(
    "Selecciona el tipo de análisis:",
    ["📊 Análisis Individual", "🌐 Análisis Agregado", "📈 Comparativa Multi-Acción"],
    label_visibility="visible"
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
    <div style='padding: 1.5rem; 
                background: linear-gradient(135deg, #1e2230 0%, #252936 100%); 
                border-radius: 14px; 
                border: 2px solid #2d3344; 
                margin-top: 2rem;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);'>
        <h4 style='color: #f0f0f0; margin-bottom: 0.8rem; font-size: 1.1rem;'>📌 Sobre el Drawdown</h4>
        <p style='color: #a0a6b8; font-size: 0.9rem; line-height: 1.6; margin: 0;'>
            El <strong style='color: #ef4444;'>drawdown</strong> mide la caída porcentual desde el máximo histórico.
            Un valor de <strong style='color: #ef4444;'>-20%</strong> indica que el precio actual está 20% por debajo del pico anterior.
        </p>
    </div>
""", unsafe_allow_html=True)

# ==================== FUNCIONES ====================
def calculate_drawdown(prices):
    """Calcula el drawdown en porcentaje"""
    cummax = prices.cummax()
    drawdown = (prices / cummax - 1) * 100
    return drawdown

def drawdown_metrics(dd):
    """Calcula métricas clave del drawdown"""
    return {
        'Max Drawdown (%)': dd.min(),
        'Drawdown Promedio (%)': dd.mean(),
        'Drawdown Actual (%)': dd.iloc[-1],
        'Días en Drawdown': (dd < 0).sum(),
        'Días en Máximo Histórico': (dd == 0).sum()
    }

def calculate_pain_index(dd):
    """Calcula el Pain Index (Ulcer Index)"""
    return np.sqrt(np.mean(dd**2))

def identify_drawdown_periods(prices, dd, threshold=-1.0):
    """Identifica períodos de drawdown significativos"""
    in_drawdown = dd < threshold
    drawdown_changes = in_drawdown.astype(int).diff()
    
    periods = []
    start_idx = None
    
    for i, (date, in_dd) in enumerate(in_drawdown.items()):
        if drawdown_changes.iloc[i] == 1:  # Start of drawdown
            start_idx = i
        elif drawdown_changes.iloc[i] == -1 and start_idx is not None:  # End of drawdown
            end_idx = i - 1
            period_dd = dd.iloc[start_idx:end_idx+1]
            
            if len(period_dd) > 0:
                max_dd = period_dd.min()
                duration = len(period_dd)
                start_date = dd.index[start_idx]
                end_date = dd.index[end_idx]
                
                # Find recovery date (when price reaches previous high again)
                recovery_idx = None
                peak_price = prices.iloc[start_idx]
                for j in range(end_idx + 1, len(prices)):
                    if prices.iloc[j] >= peak_price:
                        recovery_idx = j
                        break
                
                recovery_date = prices.index[recovery_idx] if recovery_idx else None
                recovery_days = (recovery_idx - start_idx) if recovery_idx else None
                
                periods.append({
                    'start': start_date,
                    'end': end_date,
                    'recovery': recovery_date,
                    'max_dd': max_dd,
                    'duration': duration,
                    'recovery_days': recovery_days,
                    'severity': abs(max_dd) * duration
                })
            
            start_idx = None
    
    return periods

def calculate_underwater_periods(dd):
    """Calcula períodos underwater (tiempo bajo máximo histórico)"""
    underwater = dd < -0.01  # Más del 0.01% bajo el máximo
    
    # Calcular períodos consecutivos
    underwater_changes = underwater.astype(int).diff()
    periods = []
    start_idx = None
    
    for i, is_underwater in enumerate(underwater):
        if underwater_changes.iloc[i] == 1:
            start_idx = i
        elif underwater_changes.iloc[i] == -1 and start_idx is not None:
            periods.append({
                'start': dd.index[start_idx],
                'end': dd.index[i-1],
                'days': i - start_idx
            })
            start_idx = None
    
    # Si todavía está underwater
    if start_idx is not None:
        periods.append({
            'start': dd.index[start_idx],
            'end': dd.index[-1],
            'days': len(dd) - start_idx
        })
    
    return periods

def calculate_time_to_new_high(prices):
    """Calcula el tiempo para alcanzar un nuevo máximo después de cada drawdown"""
    time_to_high = []
    cummax = prices.cummax()
    
    # Encontrar todos los momentos donde alcanza un nuevo máximo
    new_highs = prices >= cummax
    new_high_dates = prices[new_highs].index
    
    if len(new_high_dates) < 2:
        return []
    
    # Calcular días entre nuevos máximos
    for i in range(1, len(new_high_dates)):
        days_between = (new_high_dates[i] - new_high_dates[i-1]).days
        time_to_high.append({
            'previous_high': new_high_dates[i-1],
            'new_high': new_high_dates[i],
            'days': days_between,
            'price': prices[new_high_dates[i]]
        })
    
    return time_to_high

def calculate_drawdown_percentiles(dd_df, percentiles=[10, 25, 50, 75, 90]):
    """Calcula percentiles de drawdown para el mercado"""
    percentile_data = {}
    
    for p in percentiles:
        percentile_data[f'p{p}'] = dd_df.quantile(p/100, axis=1)
    
    return pd.DataFrame(percentile_data, index=dd_df.index)

def get_plotly_layout(**kwargs):
    """Retorna el layout de Plotly con tema oscuro personalizado"""
    base_layout = {
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'plot_bgcolor': 'rgba(20,24,36,0.6)',
        'font': {'color': '#f0f0f0', 'family': 'Inter, sans-serif', 'size': 12},
        'title': {'font': {'size': 22, 'color': '#f0f0f0', 'family': 'Inter'}},
        'xaxis': {
            'gridcolor': '#2d3344',
            'linecolor': '#374151',
            'color': '#a0a6b8',
            'showgrid': True,
            'zeroline': False
        },
        'yaxis': {
            'gridcolor': '#2d3344',
            'linecolor': '#374151',
            'color': '#a0a6b8',
            'showgrid': True,
            'zeroline': False
        },
        'hovermode': 'x unified',
        'hoverlabel': {
            'bgcolor': '#141824',
            'font': {'color': '#f0f0f0', 'size': 13},
            'bordercolor': '#2d3344'
        }
    }
    base_layout.update(kwargs)
    return base_layout

# ==================== ANÁLISIS INDIVIDUAL ====================
if analysis_type == "📊 Análisis Individual":
    st.markdown("## 📊 Análisis Individual por Acción")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        available_tickers = [col for col in df.columns if df[col].notna().sum() > 100]
        selected_ticker = st.selectbox("🎯 Selecciona una acción:", available_tickers, index=0)
    
    with col2:
        date_range = st.selectbox(
            "📅 Rango temporal:",
            ["Todo el historial", "Últimos 5 años", "Últimos 3 años", "Último año", "Personalizado"]
        )
    
    # Filtrar datos según el rango seleccionado
    ticker_data = df[selected_ticker].dropna()
    
    if date_range == "Últimos 5 años":
        ticker_data = ticker_data[ticker_data.index >= (ticker_data.index[-1] - pd.DateOffset(years=5))]
    elif date_range == "Últimos 3 años":
        ticker_data = ticker_data[ticker_data.index >= (ticker_data.index[-1] - pd.DateOffset(years=3))]
    elif date_range == "Último año":
        ticker_data = ticker_data[ticker_data.index >= (ticker_data.index[-1] - pd.DateOffset(years=1))]
    elif date_range == "Personalizado":
        col_a, col_b = st.columns(2)
        with col_a:
            start_date = st.date_input("Fecha inicio:", ticker_data.index[0])
        with col_b:
            end_date = st.date_input("Fecha fin:", ticker_data.index[-1])
        ticker_data = ticker_data[(ticker_data.index >= pd.to_datetime(start_date)) & 
                                  (ticker_data.index <= pd.to_datetime(end_date))]
    
    # Calcular drawdown
    dd = calculate_drawdown(ticker_data)
    metrics = drawdown_metrics(dd)
    
    # Métricas principales
    st.markdown(f"### 📊 Métricas de {selected_ticker}")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    col1.metric("Max Drawdown", f"{metrics['Max Drawdown (%)']:.2f}%")
    col2.metric("DD Promedio", f"{metrics['Drawdown Promedio (%)']:.2f}%")
    col3.metric("DD Actual", f"{metrics['Drawdown Actual (%)']:.2f}%")
    col4.metric("Días en DD", f"{int(metrics['Días en Drawdown']):,}")
    col5.metric("Días en ATH", f"{int(metrics['Días en Máximo Histórico']):,}")
    
    st.markdown("---")
    
    # Gráfico principal de drawdown
    st.markdown("### 📉 Evolución del Drawdown")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dd.index, y=dd.values,
        fill='tozeroy',
        fillcolor='rgba(239, 68, 68, 0.25)',
        line=dict(color='#ef4444', width=2.5),
        name='Drawdown',
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Drawdown: %{y:.2f}%<extra></extra>'
    ))
    
    fig.add_hline(y=dd.min(), line_dash="dash", line_color="#dc2626", 
                  line_width=2.5, annotation_text=f"Máximo DD: {dd.min():.2f}%",
                  annotation_position="right", annotation_font_size=12)
    
    fig.add_hline(y=dd.mean(), line_dash="dot", line_color="#3b82f6", 
                  line_width=2, annotation_text=f"DD Promedio: {dd.mean():.2f}%",
                  annotation_position="right", annotation_font_size=12)
    
    fig.update_layout(**get_plotly_layout(
        title=f"Drawdown Histórico - {selected_ticker}",
        xaxis_title="Fecha",
        yaxis_title="Drawdown (%)",
        height=550,
        showlegend=False
    ))
    st.plotly_chart(fig, use_container_width=True)
    
    # Gráfico de precio con máximos históricos
    st.markdown("### 💰 Precio vs Máximo Histórico")
    
    fig2 = go.Figure()
    
    fig2.add_trace(go.Scatter(
        x=ticker_data.index, y=ticker_data.values,
        name='Precio',
        line=dict(color='#10b981', width=2.5),
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Precio: $%{y:.2f}<extra></extra>'
    ))
    
    fig2.add_trace(go.Scatter(
        x=ticker_data.index, y=ticker_data.cummax().values,
        name='Máximo Histórico',
        line=dict(color='#ef4444', dash='dash', width=2),
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Máximo: $%{y:.2f}<extra></extra>'
    ))
    
    fig2.update_layout(**get_plotly_layout(
        title=f"Evolución del Precio - {selected_ticker}",
        xaxis_title="Fecha",
        yaxis_title="Precio ($)",
        height=500,
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="right", 
            x=1,
            bgcolor="rgba(20,24,36,0.8)",
            bordercolor="#2d3344",
            borderwidth=2
        )
    ))
    st.plotly_chart(fig2, use_container_width=True)
    
    # Análisis estadístico
    st.markdown("### 📊 Distribución Estadística")
    col1, col2 = st.columns(2)
    
    with col1:
        fig3 = go.Figure(data=[go.Histogram(
            x=dd.values, 
            nbinsx=50, 
            marker=dict(
                color='#ef4444',
                line=dict(color='#dc2626', width=1.5)
            ),
            hovertemplate='Rango: %{x:.1f}%<br>Frecuencia: %{y}<extra></extra>'
        )])
        
        fig3.update_layout(**get_plotly_layout(
            title="Histograma de Drawdowns",
            xaxis_title="Drawdown (%)",
            yaxis_title="Frecuencia",
            height=400,
            showlegend=False
        ))
        st.plotly_chart(fig3, use_container_width=True)
    
    with col2:
        fig4 = go.Figure(data=[go.Box(
            y=dd.values, 
            marker=dict(color='#ef4444'),
            line=dict(color='#dc2626', width=2),
            hovertemplate='Valor: %{y:.2f}%<extra></extra>'
        )])
        
        fig4.update_layout(**get_plotly_layout(
            title="Box Plot de Drawdowns",
            yaxis_title="Drawdown (%)",
            height=400,
            showlegend=False
        ))
        st.plotly_chart(fig4, use_container_width=True)
    
    # ==================== NUEVAS CARACTERÍSTICAS AVANZADAS ====================
    st.markdown("---")
    st.markdown("## 🔬 Análisis Avanzado de Drawdown")
    
    # 1. PAIN INDEX / ULCER INDEX
    st.markdown("### 😰 Pain Index (Ulcer Index)")
    
    pain_index = calculate_pain_index(dd)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Pain Index", f"{pain_index:.2f}%", 
                help="Mide el dolor sostenido de estar en drawdown. Valores más altos = mayor dolor.")
    col2.metric("Max Pain Day", f"{dd.min():.2f}%")
    col3.metric("% Tiempo Underwater", f"{(dd < -0.01).sum() / len(dd) * 100:.1f}%")
    
    # 2. IDENTIFICAR PERÍODOS DE DRAWDOWN MAYORES
    st.markdown("### 🎯 Períodos de Drawdown Significativos")
    
    dd_periods = identify_drawdown_periods(ticker_data, dd, threshold=-5.0)
    
    if dd_periods:
        # Ordenar por severidad
        dd_periods_sorted = sorted(dd_periods, key=lambda x: x['severity'], reverse=True)
        
        # Mostrar top 5 drawdowns más severos
        st.markdown("#### Top 5 Drawdowns Más Severos")
        
        top_periods = dd_periods_sorted[:5]
        
        periods_df = pd.DataFrame([{
            'Inicio': p['start'].strftime('%Y-%m-%d'),
            'Fin': p['end'].strftime('%Y-%m-%d'),
            'Recuperación': p['recovery'].strftime('%Y-%m-%d') if p['recovery'] else 'En curso',
            'Max DD (%)': f"{p['max_dd']:.2f}",
            'Duración (días)': p['duration'],
            'Días hasta Recuperación': p['recovery_days'] if p['recovery_days'] else 'N/A',
            'Severity Score': f"{p['severity']:.0f}"
        } for p in top_periods])
        
        st.dataframe(periods_df, use_container_width=True, hide_index=True)
        
    else:
        st.info("No se encontraron períodos de drawdown significativos (>5%) en el rango seleccionado.")

# ==================== ANÁLISIS AGREGADO ====================
elif analysis_type == "🌐 Análisis Agregado":
    st.markdown("## 🌐 Análisis Agregado del Mercado S&P 500")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        agg_period = st.selectbox(
            "📅 Período de análisis:",
            ["Últimos 7 años", "Últimos 5 años", "Últimos 3 años", "Todo el historial"]
        )
    
    with col2:
        min_data_points = st.slider("Mínimo de datos requeridos:", 100, 1000, 500, 50)
    
    # Filtrar datos según período
    if agg_period == "Últimos 7 años":
        df_filtered = df[df.index >= (df.index[-1] - pd.DateOffset(years=7))]
    elif agg_period == "Últimos 5 años":
        df_filtered = df[df.index >= (df.index[-1] - pd.DateOffset(years=5))]
    elif agg_period == "Últimos 3 años":
        df_filtered = df[df.index >= (df.index[-1] - pd.DateOffset(years=3))]
    else:
        df_filtered = df.copy()
    
    # Seleccionar acciones con suficientes datos
    valid_tickers = [col for col in df_filtered.columns 
                     if df_filtered[col].notna().sum() >= min_data_points]
    
    st.info(f"📊 Analizando **{len(valid_tickers)}** acciones con mínimo **{min_data_points:,}** puntos de datos")
    
    # Calcular drawdowns para todas las acciones
    with st.spinner("⏳ Calculando drawdowns para todo el mercado..."):
        all_dd = {}
        for ticker in valid_tickers:
            ticker_data = df_filtered[ticker].dropna()
            all_dd[ticker] = calculate_drawdown(ticker_data)
        
        dd_df = pd.DataFrame(all_dd)
    
    # Métricas agregadas del mercado
    st.markdown("### 📈 Métricas Agregadas del Mercado")
    
    max_dd_all = dd_df.min()
    avg_dd_all = dd_df.mean()
    current_dd_all = dd_df.iloc[-1]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Mediana Max DD", f"{max_dd_all.median():.2f}%")
    col2.metric("Promedio Max DD", f"{max_dd_all.mean():.2f}%")
    col3.metric("Peor Max DD", f"{max_dd_all.min():.2f}%")
    col4.metric("DD Actual Promedio", f"{current_dd_all.mean():.2f}%")
    
    st.markdown("---")
    
    # Top 10 peores drawdowns
    st.markdown("### 🔻 Top 10 Acciones con Mayor Drawdown Máximo")
    
    worst_dd = max_dd_all.nsmallest(10).sort_values()
    
    fig5 = go.Figure(go.Bar(
        x=worst_dd.values,
        y=worst_dd.index,
        orientation='h',
        marker=dict(
            color=worst_dd.values,
            colorscale=[[0, '#dc2626'], [0.5, '#ef4444'], [1, '#f87171']],
            line=dict(color='#991b1b', width=1.5)
        ),
        hovertemplate='<b>%{y}</b><br>Max DD: %{x:.2f}%<extra></extra>'
    ))
    
    fig5.update_layout(**get_plotly_layout(
        title="Top 10 Mayores Drawdowns Máximos del Período",
        xaxis_title="Max Drawdown (%)",
        yaxis_title="",
        height=500,
        showlegend=False
    ))
    st.plotly_chart(fig5, use_container_width=True)
    
    # Heatmaps anuales
    st.markdown("### 🔥 Mapas de Calor - Drawdowns Anuales")
    
    # Selector de acciones para heatmaps
    st.markdown("#### Selecciona acciones para los mapas de calor:")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        heatmap_tickers = st.multiselect(
            "Escoge hasta 50 acciones para visualizar:",
            valid_tickers,
            default=valid_tickers[:min(30, len(valid_tickers))],
            max_selections=50,
            key="heatmap_selector"
        )
    
    with col2:
        st.markdown("**Atajos rápidos:**")
        if st.button("🔴 Top 20 peor Max DD", key="worst20"):
            worst_20 = max_dd_all.nsmallest(20).index.tolist()
            heatmap_tickers = worst_20
        if st.button("🎲 Random 25", key="random25"):
            import random
            heatmap_tickers = random.sample(valid_tickers, min(25, len(valid_tickers)))
    
    if len(heatmap_tickers) >= 2:
        df_filtered_copy = df_filtered.copy()
        df_filtered_copy['Year'] = df_filtered_copy.index.year
        years = sorted(df_filtered_copy['Year'].unique())
        
        yearly_max_dd = []
        yearly_avg_dd = []
        
        with st.spinner(f"⏳ Calculando drawdowns anuales para {len(heatmap_tickers)} acciones..."):
            for year in years:
                year_data = df_filtered_copy[df_filtered_copy['Year'] == year]
                year_dd = {}
                for ticker in heatmap_tickers:
                    ticker_year_data = year_data[ticker].dropna()
                    if len(ticker_year_data) > 0:
                        dd_year = calculate_drawdown(ticker_year_data)
                        year_dd[ticker] = {'max': dd_year.min(), 'avg': dd_year.mean()}
                
                if year_dd:
                    yearly_max_dd.append({ticker: metrics['max'] for ticker, metrics in year_dd.items()})
                    yearly_avg_dd.append({ticker: metrics['avg'] for ticker, metrics in year_dd.items()})
        
        if yearly_max_dd:
            max_dd_matrix = pd.DataFrame(yearly_max_dd, index=years).T
            avg_dd_matrix = pd.DataFrame(yearly_avg_dd, index=years).T
            
            col1, col2 = st.columns(2)
            
            # Configurar matplotlib para modo oscuro
            plt.style.use('dark_background')
            
            with col1:
                fig6, ax = plt.subplots(figsize=(12, max(10, len(heatmap_tickers) * 0.4)))
                fig6.patch.set_facecolor('#141824')
                ax.set_facecolor('#141824')
                
                sns.heatmap(
                    max_dd_matrix, 
                    cmap='RdYlGn', 
                    linewidth=0.5, 
                    annot=True, 
                    fmt='.1f', 
                    ax=ax, 
                    center=0,
                    cbar_kws={'label': 'Drawdown (%)'},
                    vmin=-50,
                    vmax=0,
                    annot_kws={'size': 8}
                )
                
                ax.set_title("Drawdown Máximo Anual (%)", fontsize=16, fontweight='bold', 
                            color='#f0f0f0', pad=20)
                ax.set_xlabel("Año", fontsize=12, color='#a0a6b8', labelpad=10)
                ax.set_ylabel("Ticker", fontsize=12, color='#a0a6b8', labelpad=10)
                plt.xticks(color='#a0a6b8', fontsize=9)
                plt.yticks(color='#a0a6b8', fontsize=8)
                plt.tight_layout()
                st.pyplot(fig6)
            
            with col2:
                fig7, ax = plt.subplots(figsize=(12, max(10, len(heatmap_tickers) * 0.4)))
                fig7.patch.set_facecolor('#141824')
                ax.set_facecolor('#141824')
                
                sns.heatmap(
                    avg_dd_matrix, 
                    cmap='RdYlGn', 
                    linewidth=0.5, 
                    annot=True, 
                    fmt='.1f', 
                    ax=ax, 
                    center=0,
                    cbar_kws={'label': 'Drawdown (%)'},
                    vmin=-25,
                    vmax=0,
                    annot_kws={'size': 8}
                )
                
                ax.set_title("Drawdown Promedio Anual (%)", fontsize=16, fontweight='bold', 
                            color='#f0f0f0', pad=20)
                ax.set_xlabel("Año", fontsize=12, color='#a0a6b8', labelpad=10)
                ax.set_ylabel("Ticker", fontsize=12, color='#a0a6b8', labelpad=10)
                plt.xticks(color='#a0a6b8', fontsize=9)
                plt.yticks(color='#a0a6b8', fontsize=8)
                plt.tight_layout()
                st.pyplot(fig7)
            
            plt.style.use('default')
        else:
            st.warning("No hay suficientes datos para generar los mapas de calor con las acciones seleccionadas.")
    else:
        st.info("Selecciona al menos 2 acciones para generar los mapas de calor.")
    
    # Distribuciones del mercado
    st.markdown("### 📊 Distribución de Drawdowns en el Mercado")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig8 = go.Figure(data=[go.Histogram(
            x=max_dd_all.values, 
            nbinsx=50, 
            marker=dict(
                color='#ef4444',
                line=dict(color='#dc2626', width=1.5)
            ),
            hovertemplate='Rango: %{x:.1f}%<br>Acciones: %{y}<extra></extra>'
        )])
        
        fig8.update_layout(**get_plotly_layout(
            title="Distribución de Max Drawdowns",
            xaxis_title="Max Drawdown (%)",
            yaxis_title="Número de Acciones",
            height=450,
            showlegend=False
        ))
        st.plotly_chart(fig8, use_container_width=True)
    
    with col2:
        fig9 = go.Figure(data=[go.Histogram(
            x=current_dd_all.values, 
            nbinsx=50, 
            marker=dict(
                color='#fbbf24',
                line=dict(color='#d97706', width=1.5)
            ),
            hovertemplate='Rango: %{x:.1f}%<br>Acciones: %{y}<extra></extra>'
        )])
        
        fig9.update_layout(**get_plotly_layout(
            title="Distribución de Drawdowns Actuales",
            xaxis_title="Drawdown Actual (%)",
            yaxis_title="Número de Acciones",
            height=450,
            showlegend=False
        ))
        st.plotly_chart(fig9, use_container_width=True)
    
    # Tabla resumen completa
    st.markdown("### 📋 Tabla de Resumen - Todas las Acciones")
    
    summary_data = pd.DataFrame({
        'Ticker': valid_tickers,
        'Max DD (%)': [max_dd_all[t] for t in valid_tickers],
        'DD Promedio (%)': [avg_dd_all[t] for t in valid_tickers],
        'DD Actual (%)': [current_dd_all[t] for t in valid_tickers]
    }).sort_values('Max DD (%)')
    
    st.dataframe(
        summary_data.style.background_gradient(
            cmap='RdYlGn_r', 
            subset=['Max DD (%)', 'DD Promedio (%)', 'DD Actual (%)']
        ).format({
            'Max DD (%)': '{:.2f}',
            'DD Promedio (%)': '{:.2f}',
            'DD Actual (%)': '{:.2f}'
        }),
        height=450, 
        use_container_width=True
    )
    
    # ==================== ANÁLISIS AGREGADO AVANZADO ====================
    st.markdown("---")
    st.markdown("## 🔬 Análisis Avanzado Agregado")
    
    # 1. PAIN INDEX PARA TODAS LAS ACCIONES
    st.markdown("### 😰 Pain Index del Mercado")
    
    with st.spinner("⏳ Calculando Pain Index para todas las acciones..."):
        pain_indices = {}
        for ticker in valid_tickers:
            ticker_dd = dd_df[ticker].dropna()
            if len(ticker_dd) > 0:
                pain_indices[ticker] = calculate_pain_index(ticker_dd)
        
        pain_df = pd.Series(pain_indices).sort_values(ascending=False)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pain Index Medio", f"{pain_df.mean():.2f}%")
    col2.metric("Pain Index Mediano", f"{pain_df.median():.2f}%")
    col3.metric("Mayor Pain Index", f"{pain_df.max():.2f}%")
    col4.metric("Menor Pain Index", f"{pain_df.min():.2f}%")
    
    # Top 10 acciones con mayor Pain Index
    st.markdown("#### Top 10 Acciones con Mayor Pain Index")
    
    top_pain = pain_df.head(10)
    
    fig_pain = go.Figure(go.Bar(
        x=top_pain.values,
        y=top_pain.index,
        orientation='h',
        marker=dict(
            color=top_pain.values,
            colorscale=[[0, '#fbbf24'], [0.5, '#ef4444'], [1, '#dc2626']],
            line=dict(color='#991b1b', width=1.5)
        ),
        hovertemplate='<b>%{y}</b><br>Pain Index: %{x:.2f}%<extra></extra>'
    ))
    
    fig_pain.update_layout(**get_plotly_layout(
        title="Top 10 Acciones con Mayor Pain Index",
        xaxis_title="Pain Index (%)",
        yaxis_title="",
        height=450,
        showlegend=False
    ))
    
    st.plotly_chart(fig_pain, use_container_width=True)
    
    # 2. DISTRIBUCIÓN DE PAIN INDEX
    st.markdown("### 📊 Distribución del Pain Index en el Mercado")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_pain_dist = go.Figure(data=[go.Histogram(
            x=pain_df.values,
            nbinsx=30,
            marker=dict(
                color='#ef4444',
                line=dict(color='#dc2626', width=1.5)
            ),
            hovertemplate='Rango: %{x:.1f}%<br>Acciones: %{y}<extra></extra>'
        )])
        
        fig_pain_dist.update_layout(**get_plotly_layout(
            title="Distribución del Pain Index",
            xaxis_title="Pain Index (%)",
            yaxis_title="Número de Acciones",
            height=400,
            showlegend=False
        ))
        
        st.plotly_chart(fig_pain_dist, use_container_width=True)
    
    with col2:
        fig_pain_box = go.Figure(data=[go.Box(
            y=pain_df.values,
            marker=dict(color='#ef4444'),
            line=dict(color='#dc2626', width=2),
            hovertemplate='Pain Index: %{y:.2f}%<extra></extra>',
            boxmean='sd'
        )])
        
        fig_pain_box.update_layout(**get_plotly_layout(
            title="Box Plot del Pain Index",
            yaxis_title="Pain Index (%)",
            height=400,
            showlegend=False
        ))
        
        st.plotly_chart(fig_pain_box, use_container_width=True)
    
    # 3. CORRELACIÓN: PAIN INDEX VS MAX DRAWDOWN
    st.markdown("### 🎯 Relación: Pain Index vs Max Drawdown")
    
    correlation_data = pd.DataFrame({
        'ticker': valid_tickers,
        'pain_index': [pain_indices[t] for t in valid_tickers],
        'max_dd': [max_dd_all[t] for t in valid_tickers]
    })
    
    fig_correlation = go.Figure()
    
    fig_correlation.add_trace(go.Scatter(
        x=correlation_data['max_dd'].abs(),
        y=correlation_data['pain_index'],
        mode='markers',
        marker=dict(
            size=8,
            color=correlation_data['pain_index'],
            colorscale=[[0, '#fbbf24'], [0.5, '#ef4444'], [1, '#dc2626']],
            showscale=True,
            colorbar=dict(title="Pain Index"),
            line=dict(color='#2d3344', width=1)
        ),
        text=correlation_data['ticker'],
        hovertemplate='<b>%{text}</b><br>Max DD: %{x:.2f}%<br>Pain Index: %{y:.2f}%<extra></extra>',
        name='Acciones'
    ))
    
    # Línea de tendencia
    x_vals = correlation_data['max_dd'].abs().values
    y_vals = correlation_data['pain_index'].values
    z = np.polyfit(x_vals, y_vals, 1)
    p = np.poly1d(z)
    x_line = np.linspace(x_vals.min(), x_vals.max(), 100)
    
    fig_correlation.add_trace(go.Scatter(
        x=x_line,
        y=p(x_line),
        mode='lines',
        line=dict(color='#3b82f6', dash='dash', width=2),
        name='Tendencia',
        hoverinfo='skip'
    ))
    
    # Calcular correlación
    corr = np.corrcoef(x_vals, y_vals)[0, 1]
    
    fig_correlation.update_layout(**get_plotly_layout(
        title=f"Pain Index vs Max Drawdown (Correlación: {corr:.3f})",
        xaxis_title="Max Drawdown (%)",
        yaxis_title="Pain Index (%)",
        height=500,
        showlegend=True
    ))
    
    st.plotly_chart(fig_correlation, use_container_width=True)
    
    # 4. TIEMPO UNDERWATER AGREGADO
    st.markdown("### 🌊 Análisis de Tiempo Underwater del Mercado")
    
    with st.spinner("⏳ Calculando períodos underwater..."):
        pct_underwater_all = {}
        longest_underwater_all = {}
        
        for ticker in valid_tickers[:50]:  # Primeras 50 para velocidad
            ticker_dd = dd_df[ticker].dropna()
            if len(ticker_dd) > 0:
                underwater_periods = calculate_underwater_periods(ticker_dd)
                if underwater_periods:
                    total_underwater = sum([p['days'] for p in underwater_periods])
                    pct_underwater_all[ticker] = (total_underwater / len(ticker_dd)) * 100
                    longest_underwater_all[ticker] = max([p['days'] for p in underwater_periods])
    
    if pct_underwater_all:
        pct_underwater_series = pd.Series(pct_underwater_all).sort_values(ascending=False)
        longest_underwater_series = pd.Series(longest_underwater_all).sort_values(ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Top 10 % Tiempo Underwater")
            
            top_pct = pct_underwater_series.head(10)
            
            fig_pct_underwater = go.Figure(go.Bar(
                x=top_pct.values,
                y=top_pct.index,
                orientation='h',
                marker=dict(
                    color=top_pct.values,
                    colorscale='Reds',
                    line=dict(color='#991b1b', width=1.5)
                ),
                hovertemplate='<b>%{y}</b><br>% Underwater: %{x:.1f}%<extra></extra>'
            ))
            
            fig_pct_underwater.update_layout(**get_plotly_layout(
                title="% Tiempo Underwater",
                xaxis_title="% del Tiempo",
                yaxis_title="",
                height=400,
                showlegend=False
            ))
            
            st.plotly_chart(fig_pct_underwater, use_container_width=True)
        
        with col2:
            st.markdown("#### Top 10 Período Underwater Más Largo")
            
            top_longest = longest_underwater_series.head(10)
            
            fig_longest_underwater = go.Figure(go.Bar(
                x=top_longest.values,
                y=top_longest.index,
                orientation='h',
                marker=dict(
                    color=top_longest.values,
                    colorscale='Reds',
                    line=dict(color='#991b1b', width=1.5)
                ),
                hovertemplate='<b>%{y}</b><br>Días: %{x:,}<extra></extra>'
            ))
            
            fig_longest_underwater.update_layout(**get_plotly_layout(
                title="Período Más Largo Underwater",
                xaxis_title="Días",
                yaxis_title="",
                height=400,
                showlegend=False
            ))
            
            st.plotly_chart(fig_longest_underwater, use_container_width=True)
        
        # Métricas agregadas
        col1, col2, col3 = st.columns(3)
        col1.metric("% Medio Underwater", f"{pct_underwater_series.mean():.1f}%")
        col2.metric("Período Medio Más Largo", f"{longest_underwater_series.mean():.0f} días")
        col3.metric("Período Máximo Observado", f"{longest_underwater_series.max():,} días")
    
    # ==================== DRAWDOWN PERCENTILE CHARTS ====================
    st.markdown("---")
    st.markdown("### 📉 Gráfico de Percentiles de Drawdown (Fan Chart)")
    
    with st.spinner("⏳ Calculando percentiles..."):
        percentiles_df = calculate_drawdown_percentiles(dd_df, percentiles=[10, 25, 50, 75, 90])
    
    # Fan chart con áreas sombreadas
    fig_percentiles = go.Figure()
    
    # Área entre p10 y p90
    fig_percentiles.add_trace(go.Scatter(
        x=percentiles_df.index,
        y=percentiles_df['p90'],
        mode='lines',
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    fig_percentiles.add_trace(go.Scatter(
        x=percentiles_df.index,
        y=percentiles_df['p10'],
        mode='lines',
        line=dict(width=0),
        fillcolor='rgba(239, 68, 68, 0.1)',
        fill='tonexty',
        name='10-90 Percentil',
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>10th: %{y:.2f}%<extra></extra>'
    ))
    
    # Área entre p25 y p75
    fig_percentiles.add_trace(go.Scatter(
        x=percentiles_df.index,
        y=percentiles_df['p75'],
        mode='lines',
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    fig_percentiles.add_trace(go.Scatter(
        x=percentiles_df.index,
        y=percentiles_df['p25'],
        mode='lines',
        line=dict(width=0),
        fillcolor='rgba(239, 68, 68, 0.2)',
        fill='tonexty',
        name='25-75 Percentil',
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>25th: %{y:.2f}%<extra></extra>'
    ))
    
    # Línea de mediana (p50)
    fig_percentiles.add_trace(go.Scatter(
        x=percentiles_df.index,
        y=percentiles_df['p50'],
        mode='lines',
        line=dict(color='#ef4444', width=3),
        name='Mediana (50th)',
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>Mediana: %{y:.2f}%<extra></extra>'
    ))
    
    # Líneas de percentiles extremos
    fig_percentiles.add_trace(go.Scatter(
        x=percentiles_df.index,
        y=percentiles_df['p10'],
        mode='lines',
        line=dict(color='#fbbf24', width=1.5, dash='dash'),
        name='10th Percentil',
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>10th: %{y:.2f}%<extra></extra>'
    ))
    
    fig_percentiles.add_trace(go.Scatter(
        x=percentiles_df.index,
        y=percentiles_df['p90'],
        mode='lines',
        line=dict(color='#dc2626', width=1.5, dash='dash'),
        name='90th Percentil',
        hovertemplate='<b>%{x|%Y-%m-%d}</b><br>90th: %{y:.2f}%<extra></extra>'
    ))
    
    fig_percentiles.update_layout(**get_plotly_layout(
        title="Percentiles de Drawdown del Mercado - Fan Chart",
        xaxis_title="Fecha",
        yaxis_title="Drawdown (%)",
        height=550,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.98,
            xanchor="right",
            x=0.98,
            bgcolor="rgba(20,24,36,0.9)",
            bordercolor="#2d3344",
            borderwidth=2
        )
    ))
    
    st.plotly_chart(fig_percentiles, use_container_width=True)
    
    # Métricas de percentiles actuales
    st.markdown("#### Percentiles de Drawdown Actual")
    
    current_percentiles = percentiles_df.iloc[-1]
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("10th Percentil", f"{current_percentiles['p10']:.2f}%")
    col2.metric("25th Percentil", f"{current_percentiles['p25']:.2f}%")
    col3.metric("50th (Mediana)", f"{current_percentiles['p50']:.2f}%")
    col4.metric("75th Percentil", f"{current_percentiles['p75']:.2f}%")
    col5.metric("90th Percentil", f"{current_percentiles['p90']:.2f}%")
    
    st.info("💡 **Interpretación**: El 90% de las acciones tienen un drawdown mejor (menos negativo) que el percentil 90.")
    
    # ==================== DRAWDOWN CORRELATION MATRIX ====================
    st.markdown("---")
    st.markdown("### 🔗 Matriz de Correlación de Drawdowns")
    
    st.markdown("""
        Esta matriz muestra cómo los drawdowns de diferentes acciones se correlacionan entre sí.
        **Valores altos** indican que las acciones tienden a caer juntas (riesgo sistémico).
        **Valores bajos** sugieren potencial de diversificación.
    """)
    
    # Seleccionar un subconjunto para la matriz (30 acciones más líquidas/importantes)
    n_stocks_corr = min(30, len(valid_tickers))
    
    correlation_tickers = st.multiselect(
        "Selecciona acciones para la matriz de correlación (máx. 30):",
        valid_tickers,
        default=valid_tickers[:n_stocks_corr],
        max_selections=30
    )
    
    if len(correlation_tickers) >= 2:
        with st.spinner("⏳ Calculando matriz de correlación..."):
            # Calcular correlación de drawdowns
            dd_subset = dd_df[correlation_tickers].dropna()
            
            if len(dd_subset) > 0:
                corr_matrix = dd_subset.corr()
                
                # Crear heatmap con plotly
                fig_corr = go.Figure(data=go.Heatmap(
                    z=corr_matrix.values,
                    x=corr_matrix.columns,
                    y=corr_matrix.columns,
                    colorscale=[
                        [0, '#10b981'],      # Verde (correlación baja)
                        [0.5, '#fbbf24'],    # Amarillo (correlación media)
                        [1, '#ef4444']       # Rojo (correlación alta)
                    ],
                    zmid=0.5,
                    text=corr_matrix.values,
                    texttemplate='%{text:.2f}',
                    textfont={"size": 8},
                    colorbar=dict(
                        title="Correlación",
                        tickvals=[0, 0.25, 0.5, 0.75, 1.0],
                        ticktext=['0.0', '0.25', '0.5', '0.75', '1.0']
                    ),
                    hovertemplate='<b>%{x} vs %{y}</b><br>Correlación: %{z:.3f}<extra></extra>'
                ))
                
                fig_corr.update_layout(**get_plotly_layout(
                    title="Matriz de Correlación de Drawdowns",
                    xaxis_title="",
                    yaxis_title="",
                    height=max(600, len(correlation_tickers) * 20),
                    xaxis=dict(tickangle=-45),
                    yaxis=dict(autorange='reversed')
                ))
                
                st.plotly_chart(fig_corr, use_container_width=True)
                
                # Estadísticas de correlación
                col1, col2, col3, col4 = st.columns(4)
                
                # Obtener solo el triángulo superior (sin diagonal)
                mask = np.triu(np.ones_like(corr_matrix), k=1).astype(bool)
                upper_triangle = corr_matrix.where(mask)
                correlations = upper_triangle.values[mask]
                
                col1.metric("Correlación Media", f"{correlations.mean():.3f}")
                col2.metric("Correlación Mediana", f"{np.median(correlations):.3f}")
                col3.metric("Correlación Mínima", f"{correlations.min():.3f}")
                col4.metric("Correlación Máxima", f"{correlations.max():.3f}")
                
                # Pares más y menos correlacionados
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 🔴 Pares Más Correlacionados (Mayor Riesgo Conjunto)")
                    
                    # Encontrar los 5 pares más correlacionados
                    corr_pairs = []
                    for i in range(len(corr_matrix)):
                        for j in range(i+1, len(corr_matrix)):
                            corr_pairs.append({
                                'Acción 1': corr_matrix.index[i],
                                'Acción 2': corr_matrix.columns[j],
                                'Correlación': corr_matrix.iloc[i, j]
                            })
                    
                    top_corr = pd.DataFrame(corr_pairs).nlargest(5, 'Correlación')
                    st.dataframe(
                        top_corr.style.background_gradient(cmap='Reds', subset=['Correlación']).format({'Correlación': '{:.3f}'}),
                        hide_index=True,
                        use_container_width=True
                    )
                
                with col2:
                    st.markdown("#### 🟢 Pares Menos Correlacionados (Mayor Diversificación)")
                    
                    bottom_corr = pd.DataFrame(corr_pairs).nsmallest(5, 'Correlación')
                    st.dataframe(
                        bottom_corr.style.background_gradient(cmap='RdYlGn', subset=['Correlación']).format({'Correlación': '{:.3f}'}),
                        hide_index=True,
                        use_container_width=True
                    )
            else:
                st.warning("No hay suficientes datos superpuestos para calcular la correlación.")
    else:
        st.info("Selecciona al menos 2 acciones para calcular la matriz de correlación.")

# ==================== COMPARATIVA MULTI-ACCIÓN ====================
else:
    st.markdown("## 📈 Comparativa Multi-Acción")
    
    available_tickers = [col for col in df.columns if df[col].notna().sum() > 100]
    
    selected_tickers = st.multiselect(
        "🎯 Selecciona hasta 10 acciones para comparar:",
        available_tickers,
        default=available_tickers[:3] if len(available_tickers) >= 3 else available_tickers,
        max_selections=10
    )
    
    if len(selected_tickers) > 0:
        date_range = st.selectbox(
            "📅 Rango temporal:", 
            ["Todo el historial", "Últimos 5 años", "Últimos 3 años", "Último año"]
        )
        
        # Calcular drawdowns para cada acción seleccionada
        comparison_dd = {}
        
        for ticker in selected_tickers:
            ticker_data = df[ticker].dropna()
            
            if date_range == "Últimos 5 años":
                ticker_data = ticker_data[ticker_data.index >= (ticker_data.index[-1] - pd.DateOffset(years=5))]
            elif date_range == "Últimos 3 años":
                ticker_data = ticker_data[ticker_data.index >= (ticker_data.index[-1] - pd.DateOffset(years=3))]
            elif date_range == "Último año":
                ticker_data = ticker_data[ticker_data.index >= (ticker_data.index[-1] - pd.DateOffset(years=1))]
            
            comparison_dd[ticker] = calculate_drawdown(ticker_data)
        
        # Gráfico comparativo de drawdowns
        st.markdown("### 📉 Evolución Comparativa de Drawdowns")
        
        colors = ['#ef4444', '#10b981', '#3b82f6', '#fbbf24', '#a855f7', 
                  '#06b6d4', '#f97316', '#8b5cf6', '#22c55e', '#ec4899']
        
        fig10 = go.Figure()
        
        for i, (ticker, dd) in enumerate(comparison_dd.items()):
            fig10.add_trace(go.Scatter(
                x=dd.index, 
                y=dd.values,
                name=ticker,
                mode='lines',
                line=dict(color=colors[i % len(colors)], width=2.5),
                hovertemplate=f'<b>{ticker}</b><br>%{{x|%Y-%m-%d}}<br>DD: %{{y:.2f}}%<extra></extra>'
            ))
        
        fig10.update_layout(**get_plotly_layout(
            title="Comparación de Drawdowns Históricos",
            xaxis_title="Fecha",
            yaxis_title="Drawdown (%)",
            height=600,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=0.98,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(20,24,36,0.9)",
                bordercolor="#2d3344",
                borderwidth=2,
                font=dict(size=11)
            )
        ))
        st.plotly_chart(fig10, use_container_width=True)
        
        # Tabla comparativa de métricas
        st.markdown("### 📊 Tabla Comparativa de Métricas")
        
        comparison_metrics = []
        for ticker, dd in comparison_dd.items():
            metrics = drawdown_metrics(dd)
            metrics['Ticker'] = ticker
            comparison_metrics.append(metrics)
        
        comparison_df = pd.DataFrame(comparison_metrics)
        comparison_df = comparison_df[[
            'Ticker', 'Max Drawdown (%)', 'Drawdown Promedio (%)', 
            'Drawdown Actual (%)', 'Días en Drawdown', 'Días en Máximo Histórico'
        ]]
        
        st.dataframe(
            comparison_df.set_index('Ticker').style.background_gradient(
                cmap='RdYlGn_r', 
                subset=['Max Drawdown (%)', 'Drawdown Promedio (%)', 'Drawdown Actual (%)']
            ).format({
                'Max Drawdown (%)': '{:.2f}',
                'Drawdown Promedio (%)': '{:.2f}',
                'Drawdown Actual (%)': '{:.2f}',
                'Días en Drawdown': '{:,.0f}',
                'Días en Máximo Histórico': '{:,.0f}'
            }),
            use_container_width=True
        )
        
        # Gráficos de barras comparativos
        st.markdown("### 📊 Visualización Comparativa")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig11 = go.Figure(data=[
                go.Bar(
                    x=comparison_df['Ticker'], 
                    y=comparison_df['Max Drawdown (%)'], 
                    marker=dict(
                        color=comparison_df['Max Drawdown (%)'],
                        colorscale=[[0, '#dc2626'], [0.5, '#ef4444'], [1, '#f87171']],
                        line=dict(color='#991b1b', width=1.5)
                    ),
                    hovertemplate='<b>%{x}</b><br>Max DD: %{y:.2f}%<extra></extra>'
                )
            ])
            
            fig11.update_layout(**get_plotly_layout(
                title="Max Drawdown por Acción",
                xaxis_title="",
                yaxis_title="Max Drawdown (%)",
                height=450,
                showlegend=False
            ))
            st.plotly_chart(fig11, use_container_width=True)
        
        with col2:
            fig12 = go.Figure(data=[
                go.Bar(
                    x=comparison_df['Ticker'], 
                    y=comparison_df['Drawdown Actual (%)'], 
                    marker=dict(
                        color=comparison_df['Drawdown Actual (%)'],
                        colorscale=[[0, '#d97706'], [0.5, '#fbbf24'], [1, '#fde047']],
                        line=dict(color='#b45309', width=1.5)
                    ),
                    hovertemplate='<b>%{x}</b><br>DD Actual: %{y:.2f}%<extra></extra>'
                )
            ])
            
            fig12.update_layout(**get_plotly_layout(
                title="Drawdown Actual por Acción",
                xaxis_title="",
                yaxis_title="Drawdown Actual (%)",
                height=450,
                showlegend=False
            ))
            st.plotly_chart(fig12, use_container_width=True)
    else:
        st.warning("⚠️ Por favor, selecciona al menos una acción para realizar la comparativa")
    
    # ==================== ANÁLISIS COMPARATIVO AVANZADO ====================
    if len(selected_tickers) > 0:
        st.markdown("---")
        st.markdown("## 🔬 Análisis Comparativo Avanzado")
        
        # 1. COMPARACIÓN DE PAIN INDEX
        st.markdown("### 😰 Comparación de Pain Index")
        
        pain_comparison = {}
        for ticker, dd in comparison_dd.items():
            pain_comparison[ticker] = calculate_pain_index(dd)
        
        pain_comp_df = pd.Series(pain_comparison).sort_values(ascending=False)
        
        fig_pain_comp = go.Figure(go.Bar(
            x=pain_comp_df.index,
            y=pain_comp_df.values,
            marker=dict(
                color=pain_comp_df.values,
                colorscale=[[0, '#fbbf24'], [0.5, '#ef4444'], [1, '#dc2626']],
                line=dict(color='#991b1b', width=1.5)
            ),
            hovertemplate='<b>%{x}</b><br>Pain Index: %{y:.2f}%<extra></extra>'
        ))
        
        fig_pain_comp.update_layout(**get_plotly_layout(
            title="Comparación de Pain Index",
            xaxis_title="",
            yaxis_title="Pain Index (%)",
            height=400,
            showlegend=False
        ))
        
        st.plotly_chart(fig_pain_comp, use_container_width=True)
        
        # 2. UNDERWATER COMPARISON - LÍNEAS TEMPORALES
        st.markdown("### 🌊 Comparación de Períodos Underwater")
        
        fig_underwater_comp = go.Figure()
        
        for i, (ticker, dd) in enumerate(comparison_dd.items()):
            underwater = (dd < -0.01).astype(int) * 100  # Convertir a 0/100 para visualización
            
            fig_underwater_comp.add_trace(go.Scatter(
                x=dd.index,
                y=underwater.values,
                mode='lines',
                line=dict(color=colors[i % len(colors)], width=2),
                fill='tozeroy',
                fillcolor=f'rgba{tuple(list(int(colors[i % len(colors)][j:j+2], 16) for j in (1, 3, 5)) + [0.2])}',
                name=ticker,
                hovertemplate=f'<b>{ticker}</b><br>%{{x|%Y-%m-%d}}<br>Underwater: %{{y:.0f}}%<extra></extra>'
            ))
        
        fig_underwater_comp.update_layout(**get_plotly_layout(
            title="Períodos Underwater Comparados (100 = Underwater, 0 = At High)",
            xaxis_title="Fecha",
            yaxis_title="Estado",
            height=500,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=0.98,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(20,24,36,0.9)",
                bordercolor="#2d3344",
                borderwidth=2,
                font=dict(size=11)
            )
        ))
        
        st.plotly_chart(fig_underwater_comp, use_container_width=True)
        
        # 3. ESTADÍSTICAS UNDERWATER COMPARATIVAS
        st.markdown("### 📊 Estadísticas de Tiempo Underwater")
        
        underwater_stats = []
        for ticker, dd in comparison_dd.items():
            periods = calculate_underwater_periods(dd)
            if periods:
                total_days = sum([p['days'] for p in periods])
                longest = max([p['days'] for p in periods])
                pct_underwater = (total_days / len(dd)) * 100
            else:
                total_days = 0
                longest = 0
                pct_underwater = 0
            
            underwater_stats.append({
                'Ticker': ticker,
                'Días Totales Underwater': total_days,
                'Período Más Largo (días)': longest,
                '% Tiempo Underwater': f"{pct_underwater:.1f}%"
            })
        
        underwater_stats_df = pd.DataFrame(underwater_stats)
        
        st.dataframe(
            underwater_stats_df.set_index('Ticker').style.background_gradient(
                cmap='Reds',
                subset=['Días Totales Underwater', 'Período Más Largo (días)']
            ),
            use_container_width=True
        )
        
        # 4. ANÁLISIS DE RECUPERACIÓN COMPARATIVO
        st.markdown("### 📈 Análisis de Recuperación Comparativo")
        
        recovery_comparison = []
        
        for ticker, dd in comparison_dd.items():
            ticker_prices = df[ticker].dropna()
            if date_range == "Últimos 5 años":
                ticker_prices = ticker_prices[ticker_prices.index >= (ticker_prices.index[-1] - pd.DateOffset(years=5))]
            elif date_range == "Últimos 3 años":
                ticker_prices = ticker_prices[ticker_prices.index >= (ticker_prices.index[-1] - pd.DateOffset(years=3))]
            elif date_range == "Último año":
                ticker_prices = ticker_prices[ticker_prices.index >= (ticker_prices.index[-1] - pd.DateOffset(years=1))]
            
            periods = identify_drawdown_periods(ticker_prices, dd, threshold=-5.0)
            
            if periods:
                recoveries = [p['recovery_days'] for p in periods if p['recovery_days'] is not None]
                if recoveries:
                    recovery_comparison.append({
                        'ticker': ticker,
                        'avg_recovery': np.mean(recoveries),
                        'median_recovery': np.median(recoveries),
                        'max_recovery': max(recoveries),
                        'count': len(recoveries)
                    })
        
        if recovery_comparison:
            recovery_comp_df = pd.DataFrame(recovery_comparison)
            
            # Gráfico de barras agrupadas
            fig_recovery_comp = go.Figure()
            
            fig_recovery_comp.add_trace(go.Bar(
                name='Media',
                x=recovery_comp_df['ticker'],
                y=recovery_comp_df['avg_recovery'],
                marker_color='#3b82f6',
                hovertemplate='<b>%{x}</b><br>Media: %{y:.0f} días<extra></extra>'
            ))
            
            fig_recovery_comp.add_trace(go.Bar(
                name='Mediana',
                x=recovery_comp_df['ticker'],
                y=recovery_comp_df['median_recovery'],
                marker_color='#10b981',
                hovertemplate='<b>%{x}</b><br>Mediana: %{y:.0f} días<extra></extra>'
            ))
            
            fig_recovery_comp.add_trace(go.Bar(
                name='Máximo',
                x=recovery_comp_df['ticker'],
                y=recovery_comp_df['max_recovery'],
                marker_color='#ef4444',
                hovertemplate='<b>%{x}</b><br>Máximo: %{y:.0f} días<extra></extra>'
            ))
            
            fig_recovery_comp.update_layout(**get_plotly_layout(
                title="Tiempos de Recuperación Comparados",
                xaxis_title="",
                yaxis_title="Días hasta Recuperación",
                height=450,
                barmode='group',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    bgcolor="rgba(20,24,36,0.8)",
                    bordercolor="#2d3344",
                    borderwidth=2
                )
            ))
            
            st.plotly_chart(fig_recovery_comp, use_container_width=True)
            
            # Tabla de estadísticas
            recovery_table = pd.DataFrame([{
                'Ticker': r['ticker'],
                'Recuperación Media (días)': f"{r['avg_recovery']:.0f}",
                'Recuperación Mediana (días)': f"{r['median_recovery']:.0f}",
                'Recuperación Máxima (días)': f"{r['max_recovery']:,}",
                'Nº Drawdowns Analizados': r['count']
            } for r in recovery_comparison])
            
            st.dataframe(recovery_table.set_index('Ticker'), use_container_width=True)
        else:
            st.info("No hay suficientes períodos de drawdown con recuperación completa para la comparación.")
        
        # 5. RESUMEN COMPARATIVO FINAL
        st.markdown("### 📊 Tabla Resumen Completa")
        
        final_comparison = []
        for ticker, dd in comparison_dd.items():
            metrics = drawdown_metrics(dd)
            pain = calculate_pain_index(dd)
            
            periods = calculate_underwater_periods(dd)
            if periods:
                pct_underwater = (sum([p['days'] for p in periods]) / len(dd)) * 100
            else:
                pct_underwater = 0
            
            final_comparison.append({
                'Ticker': ticker,
                'Max DD (%)': metrics['Max Drawdown (%)'],
                'DD Actual (%)': metrics['Drawdown Actual (%)'],
                'Pain Index (%)': pain,
                '% Tiempo Underwater': pct_underwater,
                'Días en DD': metrics['Días en Drawdown'],
                'Días en ATH': metrics['Días en Máximo Histórico']
            })
        
        final_comp_df = pd.DataFrame(final_comparison)
        
        st.dataframe(
            final_comp_df.set_index('Ticker').style.background_gradient(
                cmap='RdYlGn_r',
                subset=['Max DD (%)', 'DD Actual (%)', 'Pain Index (%)', '% Tiempo Underwater']
            ).format({
                'Max DD (%)': '{:.2f}',
                'DD Actual (%)': '{:.2f}',
                'Pain Index (%)': '{:.2f}',
                '% Tiempo Underwater': '{:.1f}',
                'Días en DD': '{:,.0f}',
                'Días en ATH': '{:,.0f}'
            }),
            use_container_width=True
        )

# ==================== FOOTER ====================
st.markdown("---")
st.markdown(f"""
    <div style='text-align: center; 
                padding: 2rem; 
                background: linear-gradient(135deg, #141824 0%, #1e2230 100%);
                border-radius: 14px;
                border: 2px solid #2d3344;
                margin-top: 2rem;'>
        <h4 style='color: #f0f0f0; margin-bottom: 1rem;'>💡 Información sobre Drawdown</h4>
        <p style='color: #a0a6b8; font-size: 1rem; line-height: 1.6; margin-bottom: 0.5rem;'>
            El <strong style='color: #ef4444;'>drawdown</strong> representa la caída porcentual desde el máximo histórico del precio.
        </p>
        <p style='color: #a0a6b8; font-size: 0.95rem; line-height: 1.6; margin-bottom: 1.5rem;'>
            📅 Datos actualizados hasta: <strong style='color: #3b82f6;'>{df.index[-1].strftime('%d de %B de %Y')}</strong>
        </p>
        <div style='padding-top: 1.5rem; border-top: 1px solid #2d3344;'>
            <p style='color: #6b7280; font-size: 0.9rem; margin: 0;'>
                Made by <a href='https://bquantfinance.com' target='_blank' style='color: #3b82f6; text-decoration: none; font-weight: 600;'>@Gsnchez</a> | 
                <a href='https://bquantfinance.com' target='_blank' style='color: #3b82f6; text-decoration: none; font-weight: 600;'>bquantfinance.com</a>
            </p>
        </div>
    </div>
""", unsafe_allow_html=True)
