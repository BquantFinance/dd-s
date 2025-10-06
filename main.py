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
    
    df_filtered_copy = df_filtered.copy()
    df_filtered_copy['Year'] = df_filtered_copy.index.year
    years = sorted(df_filtered_copy['Year'].unique())
    
    yearly_max_dd = []
    yearly_avg_dd = []
    
    for year in years:
        year_data = df_filtered_copy[df_filtered_copy['Year'] == year]
        year_dd = {}
        for ticker in valid_tickers[:45]:  # Primeras 45 para mejor visualización
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
            fig6, ax = plt.subplots(figsize=(12, 10))
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
                vmax=0
            )
            
            ax.set_title("Drawdown Máximo Anual (%)", fontsize=16, fontweight='bold', 
                        color='#f0f0f0', pad=20)
            ax.set_xlabel("Año", fontsize=12, color='#a0a6b8', labelpad=10)
            ax.set_ylabel("Ticker", fontsize=12, color='#a0a6b8', labelpad=10)
            plt.xticks(color='#a0a6b8', fontsize=9)
            plt.yticks(color='#a0a6b8', fontsize=9)
            plt.tight_layout()
            st.pyplot(fig6)
        
        with col2:
            fig7, ax = plt.subplots(figsize=(12, 10))
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
                vmax=0
            )
            
            ax.set_title("Drawdown Promedio Anual (%)", fontsize=16, fontweight='bold', 
                        color='#f0f0f0', pad=20)
            ax.set_xlabel("Año", fontsize=12, color='#a0a6b8', labelpad=10)
            ax.set_ylabel("Ticker", fontsize=12, color='#a0a6b8', labelpad=10)
            plt.xticks(color='#a0a6b8', fontsize=9)
            plt.yticks(color='#a0a6b8', fontsize=9)
            plt.tight_layout()
            st.pyplot(fig7)
        
        plt.style.use('default')
    
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
