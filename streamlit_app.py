import streamlit as st
import pandas as pd
import plotly.express as px
import io
import re
import random
from datetime import datetime, timedelta
import folium
from folium import plugins
from streamlit_folium import st_folium

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Waze Foz do Iguaçu - Dashboard", layout="wide", page_icon="🚗")

# --- ESTADO DA SESSÃO ---
if 'app_start_time' not in st.session_state:
    st.session_state.app_start_time = datetime.now()
    st.session_state.manual_refreshes = 0

# --- CÁLCULO DE TEMPO ---
tempo_sessao = (datetime.now() - st.session_state.app_start_time).total_seconds()
tempo_prox_refresh = 600 - (tempo_sessao % 600)
minutos_restantes = int(tempo_prox_refresh // 60)
segundos_restantes = int(tempo_prox_refresh % 60)

# --- FUNÇÕES DE CORES E ESTILO ---
def get_congestion_color(speed_kmh):
    if speed_kmh >= 80: return '#00AA00'
    elif speed_kmh >= 60: return '#55DD00'
    elif speed_kmh >= 40: return '#DDDD00'
    elif speed_kmh >= 20: return '#FF8800'
    else: return '#FF0000'

def get_danger_color(incident_type):
    if pd.isna(incident_type) or not str(incident_type).strip():
        return '#0099FF'
    danger_colors = {
        'ACIDENTE': '#FF0000', 'VIA FECHADA': '#FF4400',
        'CONGESTIONAMENTO': '#FFAA00', 'PERIGO': '#FF6600',
        'ALERTA': '#FFDD00', 'OBRAS': '#AAAAAA',
    }
    return danger_colors.get(str(incident_type).upper().strip(), '#0099FF')

# --- MAPAS ---
def create_folium_map_with_compass(lat, lon, zoom_level=13):
    m = folium.Map(location=[lat, lon], zoom_start=zoom_level, tiles="OpenStreetMap")
    plugins.MousePosition(position='topright', separator=' | ', prefix='Lat/Lon: ').add_to(m)
    plugins.MeasureControl(position='bottomright').add_to(m)
    
    # Seta Norte Fixa
    north_html = '''
    <div style="position: fixed; top: 10px; left: 10px; width: 45px; height: 45px; 
        background: white; border: 2px solid #333; border-radius: 8px; z-index: 1000;
        display: flex; align-items: center; justify-content: center; font-weight: bold;">
        <div style="color: #d32f2f;">↑</div><div style="position: absolute; bottom: 2px; font-size: 9px;">N</div>
    </div>'''
    folium.Element(north_html).add_to(m)
    return m

@st.cache_resource(ttl=600)
def generate_incidents_map(df):
    if df.empty: return None
    df_map = df.dropna(subset=['lat', 'lon']).head(50)
    m = create_folium_map_with_compass(df_map['lat'].mean(), df_map['lon'].mean())
    for _, row in df_map.iterrows():
        color = get_danger_color(row['type'])
        popup_html = f"<b>🚨 {row['type']}</b><br>{row['subtype']}<br>🕒 {row['timestamp'].strftime('%H:%M')}"
        folium.CircleMarker(
            location=[row['lat'], row['lon']], radius=9,
            popup=folium.Popup(popup_html, max_width=250),
            color=color, fill=True, fillColor=color, fillOpacity=0.8
        ).add_to(m)
    return m

@st.cache_resource(ttl=600)
def generate_heatmap(df):
    if df.empty: return None
    m = create_folium_map_with_compass(df['lat'].mean(), df['lon'].mean())
    heat_data = [[row['lat'], row['lon']] for _, row in df.iterrows()]
    plugins.HeatMap(heat_data, radius=15, blur=10).add_to(m)
    return m

# --- DADOS MOCKADOS ---
def create_mock_data():
    foz_streets = [
        ("Av. Brasil", -25.5475, -54.5870), ("Av. JK", -25.5502, -54.5851),
        ("Av. das Cataratas", -25.5531, -54.5792), ("Av. Paraná", -25.5458, -54.5901)
    ]
    alerts, jams = [], []
    for _ in range(20):
        st_info = random.choice(foz_streets)
        alerts.append({
            'timestamp': datetime.now() - timedelta(minutes=random.randint(0, 120)),
            'type': random.choice(['ACIDENTE', 'VIA FECHADA', 'PERIGO', 'OBRAS', 'ALERTA']),
            'subtype': 'Incidente Reportado', 'street': st_info[0],
            'lat': st_info[1] + random.uniform(-0.005, 0.005),
            'lon': st_info[2] + random.uniform(-0.005, 0.005)
        })
    for _ in range(15):
        st_info = random.choice(foz_streets)
        jams.append({
            'timestamp': datetime.now() - timedelta(minutes=random.randint(0, 60)),
            'speed': random.uniform(5, 45), 'street': st_info[0],
            'lat': st_info[1] + random.uniform(-0.003, 0.003),
            'lon': st_info[2] + random.uniform(-0.003, 0.003)
        })
    return pd.DataFrame(alerts), pd.DataFrame(jams)

# --- CARREGAMENTO E FILTROS ---
df_alerts_raw, df_jams_raw = create_mock_data()
df_alerts_raw['hour'] = df_alerts_raw['timestamp'].dt.hour

# SIDEBAR
st.sidebar.header("⚙️ Controles")
if st.sidebar.button("🔄 ATUALIZAR DADOS", use_container_width=True):
    st.cache_resource.clear()
    st.session_state.manual_refreshes += 1
    st.rerun()

st.sidebar.metric("⏳ Próximo Ciclo", f"{minutos_restantes}:{segundos_restantes:02d}")

tipos_filtro = st.sidebar.multiselect("🚨 Tipos de Alerta", 
                                     options=df_alerts_raw['type'].unique(),
                                     default=df_alerts_raw['type'].unique())

hora_range = st.sidebar.slider("⏰ Horário", 0, 23, (0, 23))

# Aplicação de Filtros
df_filtered = df_alerts_raw[
    (df_alerts_raw['type'].isin(tipos_filtro)) & 
    (df_alerts_raw['hour'].between(hora_range[0], hora_range[1]))
]

# --- DASHBOARD UI ---
st.title("🚗 Monitoramento de Tráfego - Foz do Iguaçu")

# KPIs
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Alertas Ativos", len(df_filtered))
with c2:
    v_med = (df_jams_raw['speed'].mean() * 3.6) if not df_jams_raw.empty else 0
    st.metric("Velocidade Média", f"{v_med:.1f} km/h")
with c3:
    status = "Crítico" if len(df_filtered) > 15 else "Normal"
    st.metric("Status da Via", status)

st.markdown("---")

# Abas de Visualização
tab_mapa, tab_calor, tab_analise = st.tabs(["📍 Mapa de Pontos", "🔥 Mapa de Calor", "📋 Dados Detalhados"])

with tab_mapa:
    m_inc = generate_incidents_map(df_filtered)
    if m_inc: st_folium(m_inc, width="100%", height=500, key="map_pts")

with tab_calor:
    st.subheader("Zonas de Concentração de Incidentes")
    m_heat = generate_heatmap(df_filtered)
    if m_heat: st_folium(m_heat, width="100%", height=500, key="map_heat")

with tab_analise:
    st.subheader("Registros Filtrados")
    df_display = df_filtered.copy()
    df_display['Google Maps'] = df_display.apply(lambda x: f"https://www.google.com/maps?q={x['lat']},{x['lon']}", axis=1)
    
    st.dataframe(
        df_display[['timestamp', 'type', 'street', 'Google Maps']],
        column_config={
            "timestamp": st.column_config.DatetimeColumn("Horário", format="HH:mm"),
            "Google Maps": st.column_config.LinkColumn("📍 Ver Local")
        },
        use_container_width=True, hide_index=True
    )

st.markdown("---")
st.caption(f"Última atualização manual: {st.session_state.manual_refreshes} vezes.")
