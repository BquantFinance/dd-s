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

# ==================== CONFIGURACIÓN ====================
st.set_page_config(
    page_title="Laboratorio de Inteligencia de Drawdowns",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== ESTILOS ====================
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

# ==================== FUNCIONES PRINCIPALES ====================

def calculate_drawdowns(prices):
    """Calcular serie de drawdowns desde precios"""
    cummax = prices.expanding().max()
    drawdown = (prices - cummax) / cummax
    return drawdown

def get_drawdown_episodes(prices, threshold=-0.02):
    """Identificar y analizar episodios distintos de drawdown"""
    dd_series = calculate_drawdowns(prices)
    in_drawdown = dd_series < threshold
    
    # Agrupar días consecutivos de drawdown
    dd_groups = (in_drawdown != in_drawdown.shift()).cumsum()
    
    episodes = []
    for group_id in dd_groups[in_drawdown].unique():
        mask = (dd_groups == group_id) & in_drawdown
        episode = dd_series[mask]
        
        if len(episode) < 2:  # Saltar drawdowns muy cortos
            continue
            
        # Obtener fechas clave
        start_idx = episode.index[0]
        start_price = prices.loc[start_idx]
        
        # Encontrar el pico antes del drawdown
        pre_dd = prices[:start_idx]
        if len(pre_dd) > 0:
            peak_idx = pre_dd.index[-1]
            peak_price = pre_dd.iloc[-1]
        else:
            continue
            
        # Encontrar el fondo
        bottom_idx = episode.idxmin()
        bottom_price = prices.loc[bottom_idx]
        
        # Encontrar recuperación (si existe)
        post_dd = prices[prices.index > bottom_idx]
        recovery_mask = post_dd >= peak_price * 0.98  # Dentro del 2% del pico
        
        if recovery_mask.any():
            recovery_idx = post_dd[recovery_mask].index[0]
            recovered = True
            recovery_days = (recovery_idx - bottom_idx).days
        else:
            recovery_idx = None
            recovered = False
            recovery_days = (prices.index[-1] - bottom_idx).days
        
        # Calcular métricas
        max_dd = episode.min()
        duration = (episode.index[-1] - episode.index[0]).days
        
        # Calcular velocidad (qué tan rápido cayó)
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
    """Calcular índice de dolor - drawdown promedio durante el período"""
    return abs(drawdowns[drawdowns < 0].mean()) * 100 if len(drawdowns[drawdowns < 0]) > 0 else 0

def calculate_ulcer_index(drawdowns):
    """Calcular Índice Úlcera - mide profundidad y duración de drawdowns"""
    squared_dd = drawdowns ** 2
    return np.sqrt(squared_dd.mean()) * 100

def get_market_regime(prices, window=50):
    """Identificar régimen de mercado (tendencia alcista/bajista/lateral)"""
    sma_short = prices.rolling(window=20).mean()
    sma_long = prices.rolling(window=window).mean()
    
    regime = pd.Series(index=prices.index, dtype='object')
    regime[sma_short > sma_long] = 'Alcista'
    regime[sma_short < sma_long] = 'Bajista'
    regime[abs(sma_short - sma_long) / sma_long < 0.02] = 'Lateral'
    
    return regime

# ==================== CARGA DE DATOS ====================

@st.cache_data(ttl=3600)
def load_stock_data(symbol, period="2y"):
    """Cargar datos de acciones desde yfinance"""
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
    """Obtener símbolos del S&P 500 desde CSV"""
    try:
        # Leer CSV desde GitHub
        url = "https://raw.githubusercontent.com/BquantFinance/dd-s/main/sp500_companies.csv"
        df = pd.read_csv(url)
        
        # Asumir que hay una columna 'Symbol' o similar
        # Ajustar según la estructura real del CSV
        if 'Symbol' in df.columns:
            symbols = df['Symbol'].tolist()
        elif 'symbol' in df.columns:
            symbols = df['symbol'].tolist()
        else:
            # Usar la primera columna si no encontramos 'Symbol'
            symbols = df.iloc[:, 0].tolist()
        
        # Reemplazar puntos por guiones para compatibilidad con yfinance
        symbols = [str(s).replace('.', '-') for s in symbols]
        return symbols
    except Exception as e:
        st.error(f"Error al cargar símbolos del S&P 500: {e}")
        return []

@st.cache_data(ttl=3600)
def load_index_components(symbols, period="2y"):
    """Cargar datos para múltiples símbolos"""
    prices_dict = {}
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, symbol in enumerate(symbols[:100]):  # Limitar a 100 por velocidad
        try:
            prices = load_stock_data(symbol, period)
            if prices is not None and len(prices) > 50:
                prices_dict[symbol] = prices
        except:
            continue
        
        progress_bar.progress((i + 1) / min(len(symbols), 100))
        status_text.text(f"Cargando {symbol}...")
    
    progress_bar.empty()
    status_text.empty()
    
    return pd.DataFrame(prices_dict)

# ==================== FUNCIONES DE VISUALIZACIÓN ====================

def create_underwater_chart(prices, episodes):
    """Crear visualización de respiración submarina"""
    dd_series = calculate_drawdowns(prices)
    
    fig = go.Figure()
    
    # Área submarina principal
    fig.add_trace(go.Scatter(
        x=dd_series.index,
        y=dd_series.values * 100,
        fill='tozeroy',
        fillcolor='rgba(53, 92, 125, 0.6)',
        line=dict(color='rgb(53, 92, 125)', width=2),
        name='Bajo el agua',
        hovertemplate='Fecha: %{x}<br>Profundidad: %{y:.1f}%<extra></extra>'
    ))
    
    # Agregar "niveles de oxígeno" - más profundo = más crítico
    for episode in episodes[:5]:  # Top 5 peores
        depth = abs(episode['max_drawdown'] * 100)
        if depth > 20:
            color = 'rgba(255, 0, 0, 0.3)'
            label = '🔴 Crítico'
        elif depth > 10:
            color = 'rgba(255, 165, 0, 0.3)'
            label = '🟠 Advertencia'
        else:
            color = 'rgba(255, 255, 0, 0.3)'
            label = '🟡 Precaución'
        
        fig.add_vrect(
            x0=episode['start_date'],
            x1=episode['end_date'],
            fillcolor=color,
            layer='below',
            line_width=0,
            annotation_text=f"{depth:.1f}%",
            annotation_position="top"
        )
    
    # Línea de superficie
    fig.add_hline(y=0, line_dash="dash", line_color="white", line_width=2, opacity=0.5)
    
    fig.update_layout(
        title={
            'text': "🏊 Gráfico de Respiración Submarina<br><sub>¿Cuánto tiempo puedes aguantar la respiración?</sub>",
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title="",
        yaxis_title="Profundidad (%)",
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
    """Crear visualización de velocidad de recuperación estilo velocímetro"""
    if not episodes:
        return None
    
    recent_episode = episodes[0]  # Más reciente/severo
    
    if recent_episode['recovered']:
        # Calcular velocidad de recuperación (% recuperado por día)
        recovery_velocity = abs(recent_episode['max_drawdown']) / recent_episode['recovery_days'] * 100
        max_velocity = 2.0  # 2% por día es muy rápido
        velocity_pct = min(recovery_velocity / max_velocity * 100, 100)
    else:
        velocity_pct = 0
        recovery_velocity = 0
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=velocity_pct,
        title={'text': "Velocidad de Recuperación<br><sub>Velocidad de regreso</sub>"},
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

def create_drawdown_story(episode, symbol):
    """Generar narrativa para un episodio de drawdown"""
    depth = abs(episode['max_drawdown'] * 100)
    duration = episode['duration_days']
    
    # Generar comparaciones relacionables
    if depth > 50:
        comparison = "💀 Como perder la mitad de tus ahorros de vida"
        severity = "catastrófico"
        emoji = "🚨"
    elif depth > 30:
        comparison = "😱 Como si tu casa perdiera un año de valorización"
        severity = "severo"
        emoji = "⚠️"
    elif depth > 20:
        comparison = "😰 Como chocar tu auto"
        severity = "significativo"
        emoji = "⚠️"
    elif depth > 10:
        comparison = "😟 Como una factura médica inesperada"
        severity = "moderado"
        emoji = "📉"
    else:
        comparison = "😐 Como un mal día de compras"
        severity = "leve"
        emoji = "📊"
    
    # Estado de recuperación
    if episode['recovered']:
        recovery_text = f"✅ **Recuperado** en {episode['recovery_days']} días"
        if episode['recovery_days'] < 30:
            recovery_speed = "¡Recuperación ultrarrápida! ⚡"
        elif episode['recovery_days'] < 90:
            recovery_speed = "Recuperación rápida 🏃"
        elif episode['recovery_days'] < 180:
            recovery_speed = "Recuperación constante 🚶"
        else:
            recovery_speed = "Largo camino a la recuperación 🐢"
    else:
        days_underwater = (datetime.now().date() - episode['bottom_date'].date()).days
        recovery_text = f"❌ **Aún bajo el agua** por {days_underwater} días"
        recovery_speed = "Aún esperando recuperación... ⏳"
    
    story = f"""
    ### {emoji} El Drawdown {severity.title()} de {episode['start_date'].strftime('%B %Y')}
    
    **El Daño:** -{depth:.1f}% en {episode['fall_days']} días  
    **Dolor Comparable:** {comparison}  
    **Duración Total:** {duration} días bajo el agua  
    {recovery_text}  
    **Velocidad de Recuperación:** {recovery_speed}  
    
    **$10,000 se convirtieron en:** ${10000 * (1 + episode['max_drawdown']):.0f}  
    **Velocidad:** Cayendo a {episode['velocity']*100:.1f}% por día
    """
    
    return story

def create_decision_helper(current_dd, episodes):
    """Crear un ayudante de decisión '¿Debería preocuparme?'"""
    
    # Contexto histórico
    if episodes:
        worse_episodes = sum(1 for e in episodes if e['max_drawdown'] < current_dd)
        percentile = (worse_episodes / len(episodes)) * 100
    else:
        percentile = 0
    
    # Lógica de decisión
    if current_dd > -2:
        status = "🟢 **Todo Despejado**"
        action = "Ruido normal del mercado. Mantén el rumbo."
        color = "green"
    elif current_dd > -5:
        status = "🟡 **Turbulencia Menor**"
        action = "No se requiere acción. Esto es normal."
        color = "yellow"
    elif current_dd > -10:
        status = "🟠 **Zona de Precaución**"
        action = "Revisa tu tolerancia al riesgo. Considera tu horizonte temporal."
        color = "orange"
    elif current_dd > -20:
        status = "🔴 **Drawdown Significativo**"
        action = "No vendas en pánico. Revisa tu tesis de inversión."
        color = "red"
    else:
        status = "💀 **Drawdown Mayor**"
        action = "Modo crisis. Apégate a tu plan, la historia muestra recuperación."
        color = "darkred"
    
    return {
        'status': status,
        'action': action,
        'percentile': percentile,
        'color': color,
        'current_dd': current_dd
    }

def create_comparison_chart(prices_dict, episodes_dict):
    """Comparar comportamiento de drawdown de múltiples acciones"""
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
            hovertemplate=f'{symbol}<br>Fecha: %{{x}}<br>DD: %{{y:.1f}}%<extra></extra>'
        ))
    
    fig.update_layout(
        title="Comparación de Drawdowns - ¿Quién Maneja Mejor el Dolor?",
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

# ==================== APLICACIÓN PRINCIPAL ====================

def main():
    # Encabezado
    st.markdown("""
    <h1 style='text-align: center; font-size: 3em; margin-bottom: 0;'>
    🌊 Laboratorio de Inteligencia de Drawdowns
    </h1>
    <p style='text-align: center; color: #8b92a8; font-size: 1.2em; margin-top: 0;'>
    Entendiendo el dolor del mercado a través de historias, no solo estadísticas
    </p>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Barra lateral
    with st.sidebar:
        st.markdown("### 🎛️ Panel de Control")
        
        analysis_mode = st.radio(
            "Modo de Análisis",
            ["🎯 Acción Individual", "📊 Comparación de Índices", "🏆 Análisis S&P 500"],
            help="Elige tu tipo de análisis"
        )
        
        period = st.selectbox(
            "Configuración de Máquina del Tiempo",
            ["6mo", "1y", "2y", "5y", "max"],
            index=2,
            help="Qué tan atrás analizar"
        )
        
        if analysis_mode == "🎯 Acción Individual":
            symbol = st.text_input("Símbolo de Acción", "AAPL").upper()
            symbols = [symbol]
        elif analysis_mode == "📊 Comparación de Índices":
            symbols = st.multiselect(
                "Selecciona Acciones para Comparar",
                options=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'V', 'JNJ'],
                default=['AAPL', 'MSFT', 'GOOGL']
            )
        else:
            if st.button("🔄 Cargar S&P 500", type="primary"):
                with st.spinner("Cargando todo el S&P 500..."):
                    st.session_state['sp500_symbols'] = get_sp500_symbols()
            symbols = st.session_state.get('sp500_symbols', [])[:50]  # Limitar para demo
        
        analyze_btn = st.button("🚀 Analizar", type="primary", use_container_width=True)
        
        st.markdown("---")
        
        # Contenido educativo
        with st.expander("📚 ¿Qué es un Drawdown?"):
            st.markdown("""
            Un **drawdown** es la caída pico-valle durante un período específico.
            
            Piénsalo como:
            - 📉 Cuánto estás "bajo el agua" desde tu punto más alto
            - 😰 El dolor que sientes al ver caer tu portafolio
            - ⏳ La prueba de paciencia mientras esperas la recuperación
            
            **Por qué importa:**
            - Revela el riesgo real (la volatilidad no cuenta toda la historia)
            - Prueba tu resistencia emocional
            - Ayuda a dimensionar posiciones apropiadamente
            """)
    
    # Contenido principal
    if analyze_btn and symbols:
        if analysis_mode == "🎯 Acción Individual":
            display_individual_analysis(symbols[0], period)
        elif analysis_mode == "📊 Comparación de Índices":
            display_comparison_analysis(symbols, period)
        else:
            display_sp500_analysis(symbols, period)
    else:
        # Pantalla de bienvenida
        st.markdown("""
        <div style='text-align: center; padding: 50px;'>
            <h2>Bienvenido al Laboratorio de Inteligencia de Drawdowns</h2>
            <p style='font-size: 1.2em; color: #8b92a8;'>
            Donde convertimos el dolor del mercado en insights accionables
            </p>
            
            <div style='margin-top: 50px;'>
                <h3>Elige Tu Aventura:</h3>
                <p>🎯 <b>Acción Individual</b> - Inmersión profunda en los puntos de dolor de una acción</p>
                <p>📊 <b>Comparación de Índices</b> - Compara cómo diferentes acciones manejan los drawdowns</p>
                <p>🏆 <b>Análisis S&P 500</b> - Evaluación de dolor a nivel de mercado</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

def display_individual_analysis(symbol, period):
    """Mostrar análisis para acción individual"""
    
    prices = load_stock_data(symbol, period)
    
    if prices is None or len(prices) < 50:
        st.error(f"No se pudo cargar suficientes datos para {symbol}")
        return
    
    episodes = get_drawdown_episodes(prices)
    current_dd = calculate_drawdowns(prices).iloc[-1] * 100
    
    # Métricas principales
    st.markdown("### 🎯 Situación Actual")
    
    decision = create_decision_helper(current_dd, episodes)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <h3>{decision['status']}</h3>
            <p style='font-size: 2em; margin: 0;'>{current_dd:.1f}%</p>
            <p style='margin: 0;'>Drawdown Actual</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        worst_dd = min(e['max_drawdown'] for e in episodes) * 100 if episodes else 0
        st.markdown(f"""
        <div class='metric-card'>
            <h3>😱 El Peor</h3>
            <p style='font-size: 2em; margin: 0;'>{worst_dd:.1f}%</p>
            <p style='margin: 0;'>Dolor Máximo</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        pain_index = calculate_pain_index(calculate_drawdowns(prices))
        st.markdown(f"""
        <div class='metric-card'>
            <h3>💊 Índice de Dolor</h3>
            <p style='font-size: 2em; margin: 0;'>{pain_index:.1f}</p>
            <p style='margin: 0;'>Dolor Promedio</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        if episodes:
            recovery_rate = sum(1 for e in episodes if e['recovered']) / len(episodes) * 100
        else:
            recovery_rate = 0
        st.markdown(f"""
        <div class='metric-card'>
            <h3>💪 Tasa de Recuperación</h3>
            <p style='font-size: 2em; margin: 0;'>{recovery_rate:.0f}%</p>
            <p style='margin: 0;'>Ratio de Regreso</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Caja de ayuda para decisiones
    st.markdown(f"""
    <div class='insight-box'>
        <h3>🤔 ¿Qué Deberías Hacer?</h3>
        <p><b>{decision['action']}</b></p>
        <p>Este drawdown es peor que el {decision['percentile']:.0f}% de los drawdowns históricos.</p>
        <p>Recuerda: Cada drawdown se siente como el peor cuando estás en él.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Visualizaciones principales
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏊 Vista Submarina", "📖 Historias de Drawdown", "📊 Analítica", "🎯 Herramientas de Decisión"
    ])
    
    with tab1:
        st.plotly_chart(create_underwater_chart(prices, episodes), use_container_width=True)
        
        if episodes and episodes[0]['recovered']:
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(create_recovery_velocity_gauge(episodes), use_container_width=True)
            with col2:
                # Estadísticas de recuperación
                recoveries = [e for e in episodes if e['recovered']]
                if recoveries:
                    avg_recovery = np.mean([e['recovery_days'] for e in recoveries])
                    st.markdown(f"""
                    <div class='metric-card'>
                        <h3>⏱️ Estadísticas de Recuperación</h3>
                        <p>Promedio: {avg_recovery:.0f} días</p>
                        <p>Más rápida: {min(e['recovery_days'] for e in recoveries)} días</p>
                        <p>Más lenta: {max(e['recovery_days'] for e in recoveries)} días</p>
                    </div>
                    """, unsafe_allow_html=True)
    
    with tab2:
        st.markdown("### 📚 Tu Historial de Drawdowns")
        
        if episodes:
            # Mostrar historias para los 3 peores drawdowns
            for i, episode in enumerate(episodes[:3], 1):
                with st.expander(f"Historia #{i}: Drawdown de {episode['start_date'].strftime('%B %Y')}"):
                    st.markdown(create_drawdown_story(episode, symbol))
                    
                    # Mini gráfico para este episodio
                    fig = go.Figure()
                    
                    # Obtener serie de precios para este período de episodio
                    episode_start = episode['peak_date']
                    episode_end = episode['recovery_date'] if episode['recovery_date'] else prices.index[-1]
                    episode_prices = prices[episode_start:episode_end]
                    
                    fig.add_trace(go.Scatter(
                        x=episode_prices.index,
                        y=episode_prices.values,
                        mode='lines',
                        line=dict(color='lightblue', width=2),
                        name='Precio'
                    ))
                    
                    # Marcar puntos clave
                    fig.add_trace(go.Scatter(
                        x=[episode['peak_date'], episode['bottom_date']],
                        y=[episode['peak_price'], episode['bottom_price']],
                        mode='markers+text',
                        marker=dict(size=10, color=['green', 'red']),
                        text=['Pico', 'Fondo'],
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
            st.info("¡No se encontraron drawdowns significativos en este período!")
    
    with tab3:
        # Analítica detallada
        st.markdown("### 📈 Analítica Profunda")
        
        # Análisis de régimen
        regime = get_market_regime(prices)
        regime_counts = regime.value_counts()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico circular de régimen
            fig = go.Figure(data=[go.Pie(
                labels=regime_counts.index,
                values=regime_counts.values,
                marker=dict(colors=['green', 'red', 'gray']),
                hole=0.3
            )])
            
            fig.update_layout(
                title="Distribución de Régimen de Mercado",
                height=300,
                plot_bgcolor='#0e1117',
                paper_bgcolor='#0e1117',
                font=dict(color='white')
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Distribución de drawdown
            if episodes:
                dd_magnitudes = [abs(e['max_drawdown']) * 100 for e in episodes]
                
                fig = go.Figure(data=[go.Histogram(
                    x=dd_magnitudes,
                    nbinsx=20,
                    marker=dict(color='lightcoral')
                )])
                
                fig.update_layout(
                    title="Distribución de Magnitud de Drawdown",
                    xaxis_title="Drawdown (%)",
                    yaxis_title="Frecuencia",
                    height=300,
                    plot_bgcolor='#0e1117',
                    paper_bgcolor='#0e1117',
                    font=dict(color='white')
                )
                
                st.plotly_chart(fig, use_container_width=True)
        
        # Tabla de estadísticas
        if episodes:
            meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
            worst_month = calculate_drawdowns(prices).groupby(pd.Grouper(freq='M')).min().idxmin()
            worst_month_str = f"{meses[worst_month.month-1]} {worst_month.year}"
            
            stats_df = pd.DataFrame({
                'Métrica': [
                    'Número de Drawdowns',
                    'Drawdown Promedio (%)',
                    'Duración Promedio (días)',
                    'Recuperación Promedio (días)',
                    'Peor Mes',
                    'Mejor Mes Después de Drawdown'
                ],
                'Valor': [
                    len(episodes),
                    f"{np.mean([abs(e['max_drawdown']) * 100 for e in episodes]):.1f}%",
                    f"{np.mean([e['duration_days'] for e in episodes]):.0f}",
                    f"{np.mean([e['recovery_days'] for e in episodes if e['recovered']]):.0f}",
                    worst_month_str,
                    "Próximamente"
                ]
            })
            
            st.table(stats_df)
    
    with tab4:
        st.markdown("### 🎯 Herramientas de Apoyo a Decisiones")
        
        # Calculadora de tolerancia al riesgo
        st.markdown("""
        <div class='warning-box'>
            <h3>🎰 Tu Chequeo de Realidad de Riesgo</h3>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            investment = st.number_input("Tu Inversión ($)", value=10000, step=1000)
            tolerance = st.slider("Pérdida Máxima que Puedes Soportar (%)", 0, 50, 20)
        
        with col2:
            if episodes:
                worst = abs(min(e['max_drawdown'] for e in episodes) * 100)
                potential_loss = investment * worst / 100
                
                if worst > tolerance:
                    st.error(f"""
                    ⚠️ **¡Chequeo de Realidad!**  
                    Peor histórico: -{worst:.1f}%  
                    Tu tolerancia: -{tolerance}%  
                    Perderías: ${potential_loss:.0f}  
                    
                    **¡Quizás quieras reconsiderar el tamaño de tu posición!**
                    """)
                else:
                    st.success(f"""
                    ✅ **Dentro de Tolerancia**  
                    Peor histórico: -{worst:.1f}%  
                    Tu tolerancia: -{tolerance}%  
                    Pérdida histórica máxima: ${potential_loss:.0f}
                    """)
        
        # Herramienta de comparación histórica
        st.markdown("### 🕰️ Máquina del Tiempo: ¿Qué Pasaría Si Hubieras Comprado En...")
        
        if episodes and len(episodes) > 0:
            meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
            
            selected_episode = st.selectbox(
                "Selecciona un pico histórico",
                options=range(len(episodes)),
                format_func=lambda i: f"{meses[episodes[i]['peak_date'].month-1]} {episodes[i]['peak_date'].year} (cayó {abs(episodes[i]['max_drawdown']*100):.1f}%)"
            )
            
            episode = episodes[selected_episode]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Estarías abajo", f"{abs(episode['max_drawdown']*100):.1f}%")
            with col2:
                st.metric("Por tantos días", f"{episode['duration_days']}")
            with col3:
                if episode['recovered']:
                    st.metric("La recuperación tomó", f"{episode['recovery_days']} días")
                else:
                    st.metric("Aún esperando", "No recuperado")

def display_comparison_analysis(symbols, period):
    """Mostrar análisis de comparación para múltiples acciones"""
    
    st.markdown("### 🏁 Carrera de Drawdowns: ¿Quién Maneja Mejor el Dolor?")
    
    prices_dict = {}
    episodes_dict = {}
    
    # Cargar datos
    progress = st.progress(0)
    for i, symbol in enumerate(symbols):
        prices = load_stock_data(symbol, period)
        if prices is not None and len(prices) > 50:
            prices_dict[symbol] = prices
            episodes_dict[symbol] = get_drawdown_episodes(prices)
        progress.progress((i + 1) / len(symbols))
    progress.empty()
    
    if not prices_dict:
        st.error("No se pudo cargar datos para los símbolos seleccionados")
        return
    
    # Métricas de comparación
    comparison_data = []
    for symbol, episodes in episodes_dict.items():
        if episodes:
            comparison_data.append({
                'Símbolo': symbol,
                'DD Actual (%)': calculate_drawdowns(prices_dict[symbol]).iloc[-1] * 100,
                'Peor DD (%)': min(e['max_drawdown'] for e in episodes) * 100,
                'DD Promedio (%)': np.mean([e['max_drawdown'] for e in episodes]) * 100,
                'Índice de Dolor': calculate_pain_index(calculate_drawdowns(prices_dict[symbol])),
                'Tasa de Recuperación (%)': sum(1 for e in episodes if e['recovered']) / len(episodes) * 100,
                'Recuperación Promedio (días)': np.mean([e['recovery_days'] for e in episodes if e['recovered']]) if any(e['recovered'] for e in episodes) else 0
            })
    
    comparison_df = pd.DataFrame(comparison_data)
    
    # Mostrar rankings
    st.markdown("### 🏆 Rankings de Desempeño")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🛡️ Más Resiliente** (Menor peor DD)")
        winner = comparison_df.nlargest(1, 'Peor DD (%)').iloc[0]
        st.success(f"👑 {winner['Símbolo']}: {winner['Peor DD (%)']:.1f}%")
    
    with col2:
        st.markdown("**💊 Menos Doloroso** (Menor índice de dolor)")
        winner = comparison_df.nsmallest(1, 'Índice de Dolor').iloc[0]
        st.success(f"👑 {winner['Símbolo']}: {winner['Índice de Dolor']:.1f}")
    
    with col3:
        st.markdown("**⚡ Recuperación Más Rápida** (Días promedio)")
        winner = comparison_df.nsmallest(1, 'Recuperación Promedio (días)').iloc[0]
        st.success(f"👑 {winner['Símbolo']}: {winner['Recuperación Promedio (días)']:.0f} días")
    
    # Gráfico de comparación
    st.plotly_chart(create_comparison_chart(prices_dict, episodes_dict), use_container_width=True)
    
    # Tabla de comparación detallada
    st.markdown("### 📊 Comparación Detallada")
    
    st.dataframe(
        comparison_df.style.format({
            'DD Actual (%)': '{:.1f}',
            'Peor DD (%)': '{:.1f}',
            'DD Promedio (%)': '{:.1f}',
            'Índice de Dolor': '{:.1f}',
            'Tasa de Recuperación (%)': '{:.0f}',
            'Recuperación Promedio (días)': '{:.0f}'
        }).background_gradient(cmap='RdYlGn_r', subset=['DD Actual (%)', 'Peor DD (%)', 'Índice de Dolor'])
          .background_gradient(cmap='RdYlGn', subset=['Tasa de Recuperación (%)']),
        use_container_width=True
    )
    
    # Batallas cara a cara
    st.markdown("### ⚔️ Batallas Cara a Cara")
    
    if len(symbols) >= 2:
        col1, col2 = st.columns(2)
        
        with col1:
            fighter1 = st.selectbox("Luchador 1", symbols, index=0)
        with col2:
            fighter2 = st.selectbox("Luchador 2", symbols, index=1)
        
        if fighter1 != fighter2:
            f1_data = comparison_df[comparison_df['Símbolo'] == fighter1].iloc[0]
            f2_data = comparison_df[comparison_df['Símbolo'] == fighter2].iloc[0]
            
            battles = [
                ('Posición Actual', 'DD Actual (%)', True),  # True significa menor es mejor
                ('Dureza Histórica', 'Peor DD (%)', False),  # False significa mayor es mejor
                ('Tolerancia al Dolor', 'Índice de Dolor', True),
                ('Poder de Recuperación', 'Tasa de Recuperación (%)', False),
                ('Velocidad', 'Recuperación Promedio (días)', True)
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
            
            st.markdown(f"### 🏆 Ganador: {fighter1 if f1_wins > f2_wins else fighter2} ({max(f1_wins, f2_wins)}-{min(f1_wins, f2_wins)})")

def display_sp500_analysis(symbols, period):
    """Mostrar análisis agregado del S&P 500"""
    
    st.markdown("### 🌍 Evaluación de Dolor a Nivel de Mercado")
    
    # Cargar datos para símbolos
    prices_df = load_index_components(symbols, period)
    
    if prices_df.empty:
        st.error("No se pudo cargar datos del S&P 500")
        return
    
    # Calcular métricas agregadas
    all_episodes = []
    current_dds = []
    
    for symbol in prices_df.columns:
        dd = calculate_drawdowns(prices_df[symbol])
        current_dds.append(dd.iloc[-1] * 100)
        
        episodes = get_drawdown_episodes(prices_df[symbol])
        for episode in episodes:
            episode['symbol'] = symbol
            all_episodes.append(episode)
    
    # Panel de salud del mercado
    st.markdown("### 🏥 Estado de Salud del Mercado")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_dd = np.mean(current_dds)
        health_color = "🟢" if avg_dd > -5 else "🟡" if avg_dd > -10 else "🟠" if avg_dd > -20 else "🔴"
        st.markdown(f"""
        <div class='metric-card'>
            <h3>{health_color} Salud del Mercado</h3>
            <p style='font-size: 2em;'>{avg_dd:.1f}%</p>
            <p>DD Promedio</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        stocks_in_dd = sum(1 for dd in current_dds if dd < -10)
        pct_in_dd = (stocks_in_dd / len(current_dds)) * 100
        st.markdown(f"""
        <div class='metric-card'>
            <h3>📊 Acciones Sufriendo</h3>
            <p style='font-size: 2em;'>{pct_in_dd:.0f}%</p>
            <p>En DD de 10%+</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        if all_episodes:
            recent_episodes = [e for e in all_episodes if (datetime.now().date() - e['start_date'].date()).days < 90]
            st.markdown(f"""
            <div class='metric-card'>
                <h3>🌊 Eventos Recientes</h3>
                <p style='font-size: 2em;'>{len(recent_episodes)}</p>
                <p>Últimos 90 días</p>
            </div>
            """, unsafe_allow_html=True)
        
    with col4:
        bear_market = sum(1 for dd in current_dds if dd < -20)
        bear_pct = (bear_market / len(current_dds)) * 100
        st.markdown(f"""
        <div class='metric-card'>
            <h3>🐻 Territorio Bajista</h3>
            <p style='font-size: 2em;'>{bear_pct:.0f}%</p>
            <p>En DD de 20%+</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Evaluación del estado de ánimo del mercado
    if avg_dd > -5:
        mood = "😊 Eufórico - ¡Los mercados se sienten genial!"
        mood_color = "green"
    elif avg_dd > -10:
        mood = "😐 Cauteloso - Algo de nerviosismo apareciendo"
        mood_color = "yellow"
    elif avg_dd > -20:
        mood = "😰 Temeroso - Estrés significativo en el sistema"
        mood_color = "orange"
    else:
        mood = "😱 Pánico - Miedo máximo, ¿oportunidad potencial?"
        mood_color = "red"
    
    st.markdown(f"""
    <div class='insight-box'>
        <h2>Estado de Ánimo del Mercado: {mood}</h2>
        <p>Basado en {len(current_dds)} acciones analizadas</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Peores performers
    st.markdown("### 💀 Heridos Andantes (Peores Drawdowns Actuales)")
    
    worst_current = pd.DataFrame({
        'Símbolo': prices_df.columns,
        'DD Actual (%)': current_dds
    }).nsmallest(10, 'DD Actual (%)')
    
    fig = go.Figure(data=[go.Bar(
        x=worst_current['Símbolo'],
        y=worst_current['DD Actual (%)'],
        marker=dict(color=worst_current['DD Actual (%)'],
                   colorscale='Reds',
                   showscale=False),
        text=[f"{dd:.1f}%" for dd in worst_current['DD Actual (%)']],
        textposition='auto'
    )])
    
    fig.update_layout(
        title="Bottom 10 - Actualmente Sufriendo Más",
        height=400,
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font=dict(color='white')
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Perspectiva histórica
    if all_episodes:
        st.markdown("### 📜 Perspectiva Histórica")
        
        # Agrupar por año
        episodes_df = pd.DataFrame(all_episodes)
        episodes_df['year'] = pd.to_datetime(episodes_df['start_date']).dt.year
        
        yearly_stats = episodes_df.groupby('year').agg({
            'max_drawdown': ['count', 'mean'],
            'recovery_days': 'mean'
        }).round(1)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📅 Drawdowns por Año**")
            st.bar_chart(yearly_stats[('max_drawdown', 'count')])
        
        with col2:
            st.markdown("**😰 Dolor Promedio por Año**")
            st.line_chart(abs(yearly_stats[('max_drawdown', 'mean')] * 100))

if __name__ == "__main__":
    main()
