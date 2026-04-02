import streamlit as st
import pandas as pd
import plotly.express as px
import re
import random
from datetime import datetime, timedelta, date
import folium
from folium import plugins
from streamlit_folium import st_folium

# =============================================
# 1. CONFIGURAÇÃO DA PÁGINA (ÚNICO)
# =============================================
st.set_page_config(
    page_title="Waze Foz do Iguaçu",
    layout="wide",
    page_icon="🚗"
)

# =============================================
# 2. ESTADO DA SESSÃO (ÚNICO)
# =============================================
if 'app_start_time' not in st.session_state:
    st.session_state.app_start_time = datetime.now()
    st.session_state.manual_refreshes = 0

tempo_sessao = (datetime.now() - st.session_state.app_start_time).total_seconds()
tempo_prox_refresh = 600 - (tempo_sessao % 600)
minutos_restantes = int(tempo_prox_refresh // 60)
segundos_restantes = int(tempo_prox_refresh % 60)
tempo_total = int(tempo_sessao)

# =============================================
# 3. FUNÇÕES DE CORES
# =============================================
def get_congestion_color(speed_kmh):
    if speed_kmh >= 80:   return '#00AA00'
    elif speed_kmh >= 60: return '#55DD00'
    elif speed_kmh >= 40: return '#DDDD00'
    elif speed_kmh >= 20: return '#FF8800'
    else:                  return '#FF0000'

def get_danger_color(incident_type):
    if pd.isna(incident_type) or str(incident_type).strip() == '':
        return '#0099FF'
    danger_colors = {
        'ACIDENTE': '#FF0000', 'VIA FECHADA': '#FF4400',
        'CONGESTIONAMENTO': '#FFAA00', 'PERIGO': '#FF6600',
        'ALERTA': '#FFDD00', 'OBRAS': '#AAAAAA',
    }
    return danger_colors.get(str(incident_type).upper().strip(), '#0099FF')

# =============================================
# 4. FUNÇÕES DE MAPA (BASE)
# =============================================
def create_folium_map_with_compass(lat, lon, zoom_level=13):
    m = folium.Map(
        location=[lat, lon],
        zoom_start=zoom_level,
        tiles="OpenStreetMap",
        max_bounds=True
    )
    plugins.MousePosition(
        position='topright', separator=' | ',
        prefix='Lat/Lon: ', num_digits=5
    ).add_to(m)
    plugins.MeasureControl(position='bottomright').add_to(m)

    north_html = '''
    <div style="position: fixed; top: 10px; left: 10px; width: 45px; height: 45px;
        background: linear-gradient(145deg, #f0f0f0, #e6e6e6);
        border: 2px solid #333; border-radius: 8px; z-index: 1000;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px;">
        <div style="color: #d32f2f; text-shadow: 1px 1px 1px white;">↑</div>
        <div style="position: absolute; bottom: 2px; font-size: 9px; color: #333; font-weight: bold;">N</div>
    </div>'''
    folium.Element(north_html).add_to(m)
    folium.LayerControl(position='topright', collapsed=True).add_to(m)
    return m

# =============================================
# 5. MAPAS CACHEADOS
# =============================================
@st.cache_resource(ttl=600, show_spinner=False)
def generate_incidents_map(df_filtered):
    """Mapa de incidentes com popups detalhados."""
    if df_filtered.empty:
        return None
    df_map = df_filtered.dropna(subset=['lat', 'lon']).head(50)
    df_map = df_map[
        (df_map['lat'].between(-25.60, -25.52)) &
        (df_map['lon'].between(-54.65, -54.55))
    ]
    if df_map.empty:
        return None

    m = create_folium_map_with_compass(df_map['lat'].mean(), df_map['lon'].mean(), zoom_level=13)
    for _, row in df_map.iterrows():
        try:
            color = get_danger_color(row.get('type', 'ALERTA'))
            popup_html = f"""
            <div style="min-width: 200px; font-family: Arial;">
                <b style="color: {color}; font-size: 16px;">🚨 {row.get('type','?')}</b><br>
                <b>{row.get('subtype','')}</b><br>
                🛣️ <i>{row.get('street','N/A')}</i><br>
                🕒 {row['timestamp'].strftime('%H:%M')}<br>
                📍 {row['lat']:.4f}, {row['lon']:.4f}
            </div>"""
            folium.CircleMarker(
                location=[float(row['lat']), float(row['lon'])],
                radius=9,
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{row.get('type','?')}: {row.get('street','N/A')}",
                color=color, fill=True, fillColor=color, fillOpacity=0.8, weight=2
            ).add_to(m)
        except:
            continue
    return m

@st.cache_resource(ttl=600, show_spinner=False)
def generate_jams_map(df_jams_filtered):
    """Mapa de congestionamentos com velocidade em cores."""
    if df_jams_filtered.empty:
        return None
    df_valid = df_jams_filtered.dropna(subset=['lat', 'lon', 'speed']).head(40)
    df_valid = df_valid[
        (df_valid['lat'].between(-25.60, -25.52)) &
        (df_valid['lon'].between(-54.65, -54.55))
    ]
    if df_valid.empty:
        return None

    m = create_folium_map_with_compass(df_valid['lat'].mean(), df_valid['lon'].mean(), zoom_level=13)
    for _, row in df_valid.iterrows():
        try:
            speed_kmh = float(row['speed']) * 3.6
            color = get_congestion_color(speed_kmh)
            popup_html = f"""
            <div style="min-width: 180px;">
                <b style="color: {color}">🚗 {speed_kmh:.0f} km/h</b><br>
                🛣️ <i>{row.get('street','Via')}</i><br>
                🕒 {row['timestamp'].strftime('%H:%M')}
            </div>"""
            folium.CircleMarker(
                location=[float(row['lat']), float(row['lon'])],
                radius=7,
                popup=folium.Popup(popup_html, max_width=220),
                tooltip=f"{speed_kmh:.0f}km/h - {row.get('street','Via')}",
                color=color, fill=True, fillColor=color, fillOpacity=0.7
            ).add_to(m)
        except:
            continue
    return m

@st.cache_resource(ttl=600, show_spinner=False)
def generate_heatmap(df_filtered):
    """Mapa de calor de concentração de incidentes."""
    if df_filtered.empty:
        return None
    df_map = df_filtered.dropna(subset=['lat', 'lon'])
    if df_map.empty:
        return None
    m = create_folium_map_with_compass(df_map['lat'].mean(), df_map['lon'].mean(), zoom_level=13)
    heat_data = [[row['lat'], row['lon']] for _, row in df_map.iterrows()]
    plugins.HeatMap(heat_data, radius=15, blur=10).add_to(m)
    return m

# =============================================
# 6. DADOS MOCKADOS
# =============================================
def create_mock_data():
    """Dados mockados realistas de Foz do Iguaçu."""
    foz_streets = [
        ("Av. Brasil",          -25.5475, -54.5870),
        ("Av. JK",              -25.5502, -54.5851),
        ("Av. das Cataratas",   -25.5531, -54.5792),
        ("Av. Paraná",          -25.5458, -54.5901),
        ("Ponte Tancredo Neves",-25.5412, -54.5955),
        ("Rod. BR-277",         -25.5600, -54.5800),
        ("Av. Costa e Silva",   -25.5480, -54.5820),
        ("R. Edmundo de Barros",-25.5460, -54.5890),
    ]
    subtipos = [
        'Colisão frontal','Carro parado','Buraco na pista',
        'Obras na via','Semáforo quebrado','Animal na pista',
        'Acidente grave','Acidente leve','Inundação'
    ]
    tipos = ['ACIDENTE','VIA FECHADA','PERIGO','OBRAS','ALERTA']

    alerts_data, jams_data = [], []

    for _ in range(20):
        street, base_lat, base_lon = random.choice(foz_streets)
        alerts_data.append({
            'timestamp': datetime.now() - timedelta(minutes=random.randint(0, 120)),
            'type':    random.choice(tipos),
            'subtype': random.choice(subtipos),
            'street':  street,
            'lat':     round(base_lat + random.uniform(-0.005, 0.005), 6),
            'lon':     round(base_lon + random.uniform(-0.005, 0.005), 6),
        })

    for _ in range(15):
        street, base_lat, base_lon = random.choice(foz_streets)
        jams_data.append({
            'timestamp': datetime.now() - timedelta(minutes=random.randint(0, 60)),
            'speed':  round(random.uniform(5, 45), 1),
            'street': street,
            'lat':    round(base_lat + random.uniform(-0.003, 0.003), 6),
            'lon':    round(base_lon + random.uniform(-0.003, 0.003), 6),
        })

    return pd.DataFrame(alerts_data), pd.DataFrame(jams_data)

# =============================================
# 7. SIDEBAR UNIFICADA
# =============================================
st.sidebar.header("⚙️ Controles")
st.sidebar.markdown("### ⏰ Status da Sessão")
st.sidebar.metric("⏳ Tempo online",   f"{tempo_total//3600}h:{(tempo_total%3600)//60:02d}m")
st.sidebar.metric("⏳ Próximo ciclo",  f"{minutos_restantes}:{segundos_restantes:02d}")
st.sidebar.metric("🔄 Atualizações",  st.session_state.manual_refreshes)

if st.sidebar.button("🔄 ATUALIZAR DADOS AGORA", use_container_width=True, type="primary"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.session_state.manual_refreshes += 1
    st.rerun()

st.sidebar.divider()

# =============================================
# 8. CARREGAMENTO DE DADOS
# =============================================
df_alerts_raw, df_jams_raw = create_mock_data()
df_alerts_raw['hour'] = df_alerts_raw['timestamp'].dt.hour

# Determinar range de datas disponíveis
all_dates = set(df_alerts_raw['timestamp'].dt.date.tolist()) | set(df_jams_raw['timestamp'].dt.date.tolist())
min_date = min(all_dates)
max_date = max(all_dates)

# =============================================
# 9. FILTROS NA SIDEBAR
# =============================================
st.sidebar.subheader("🔍 Filtros")

selected_date = st.sidebar.date_input(
    "📅 Data", value=max_date, min_value=min_date, max_value=max_date
)

tipos_disponiveis = sorted(df_alerts_raw['type'].dropna().unique().tolist())
filtro_tipo = st.sidebar.multiselect(
    "🚨 Tipo de Alerta",
    options=tipos_disponiveis,
    default=tipos_disponiveis,
)

filtro_rua = st.sidebar.text_input(
    "🛣️ Buscar Rua", placeholder="Ex: Av. Brasil"
)

hora_range = st.sidebar.slider("⏰ Horário", 0, 23, (0, 23))

# =============================================
# 10. APLICAÇÃO DOS FILTROS
# =============================================
df_filtered = df_alerts_raw[
    (df_alerts_raw['timestamp'].dt.date == selected_date) &
    (df_alerts_raw['type'].isin(filtro_tipo)) &
    (df_alerts_raw['hour'].between(hora_range[0], hora_range[1]))
].copy()

if filtro_rua:
    df_filtered = df_filtered[
        df_filtered['street'].str.contains(filtro_rua, case=False, na=False)
    ]

df_jams_filtered = df_jams_raw[
    (df_jams_raw['timestamp'].dt.date == selected_date) &
    (df_jams_raw['timestamp'].dt.hour.between(hora_range[0], hora_range[1]))
].copy()

# =============================================
# 11. CABEÇALHO
# =============================================
st.title(f"🚗 Monitoramento de Tráfego - Foz do Iguaçu — {selected_date.strftime('%d/%m/%Y')}")
st.caption("Dados extraídos em tempo real do Waze via Google Drive.")
st.markdown("---")

# =============================================
# 12. RESUMO DOS FILTROS ATIVOS
# =============================================
col_f1, col_f2, col_f3, col_f4 = st.columns(4)
col_f1.metric("📅 Data",     selected_date.strftime("%d/%m/%Y"))
col_f2.metric("🚨 Alertas",  f"{len(filtro_tipo)} tipos")
col_f3.metric("🛣️ Rua",      f"'{filtro_rua}'" if filtro_rua else "Todas")
col_f4.metric("⏰ Horário",  f"{hora_range[0]:02d}:00–{hora_range[1]:02d}:59")
st.markdown("---")

# =============================================
# 13. KPIs PRINCIPAIS
# =============================================
st.subheader("📊 Resumo Estatístico")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

incidentes_dia   = len(df_filtered)
acidentes_graves = len(df_filtered[df_filtered['type'] == 'ACIDENTE']) if not df_filtered.empty else 0
v_media_kmh      = (df_jams_filtered['speed'].mean() * 3.6) if not df_jams_filtered.empty else 0
status_via       = "🚫 Crítico" if incidentes_dia > 15 else ("⚠️ Moderado" if incidentes_dia > 5 else "✅ Normal")

kpi1.metric("Total Alertas",    incidentes_dia)
kpi2.metric("Acidentes",        acidentes_graves)
kpi3.metric("Vel. Média",       f"{v_media_kmh:.1f} km/h")
kpi4.metric("Status da Via",    status_via)

st.markdown("---")

# =============================================
# 14. INDICADORES VISUAIS DE GRAVIDADE
# =============================================
st.subheader("📈 Indicadores de Gravidade")
col_grav, col_vel = st.columns(2)

# Gravidade
gravidade = min(75, incidentes_dia * 5)
cor_gravidade = '#FF0000' if gravidade >= 75 else ('#FF8800' if gravidade >= 50 else ('#FFDD00' if gravidade >= 25 else '#00AA00'))
with col_grav:
    fig_grav = px.bar_polar(r=[gravidade], theta=[0], range_r=[0, 100],
                             color_discrete_sequence=[cor_gravidade])
    fig_grav.update_layout(
        title=f"🚨 Gravidade: {incidentes_dia} incidentes",
        polar=dict(radialaxis=dict(range=[0,100], showticklabels=False),
                   angularaxis=dict(showticklabels=False)),
        showlegend=False, height=220
    )
    st.plotly_chart(fig_grav, use_container_width=True)

# Velocidade
cor_vel = 'green' if v_media_kmh > 40 else ('yellow' if v_media_kmh > 20 else 'red')
with col_vel:
    fig_vel = px.bar_polar(r=[v_media_kmh], theta=[0], range_r=[0, 80],
                            color_discrete_sequence=[cor_vel])
    fig_vel.update_layout(
        title=f"🚗 Velocidade Média: {v_media_kmh:.1f} km/h",
        polar=dict(radialaxis=dict(range=[0,80], showticklabels=False),
                   angularaxis=dict(showticklabels=False)),
        showlegend=False, height=220
    )
    st.plotly_chart(fig_vel, use_container_width=True)

st.markdown("---")

# =============================================
# 15. ABAS DE VISUALIZAÇÃO (NOVO - do código 2)
# =============================================
st.subheader("🗺️ Visualizações de Mapa")
tab_inc, tab_jams, tab_calor, tab_dados = st.tabs([
    "📍 Incidentes", "🚗 Congestionamentos", "🔥 Mapa de Calor", "📋 Dados Detalhados"
])

with tab_inc:
    st.caption("📍 Centro: -25.54, -54.58 | 🧭 Norte ↑")
    mapa_inc = generate_incidents_map(df_filtered)
    if mapa_inc:
        st_folium(mapa_inc, width="100%", height=480, key="mapa_inc")
    else:
        st.info("Nenhum incidente no filtro selecionado.")

with tab_jams:
    st.caption("📏 Escala métrica | 🟢 Livre → 🔴 Parado")
    mapa_jam = generate_jams_map(df_jams_filtered)
    if mapa_jam:
        st_folium(mapa_jam, width="100%", height=480, key="mapa_jam")
        st.markdown("**Legenda:** 🟢 >80 km/h | 🟡 40–80 km/h | 🟠 20–40 km/h | 🔴 <20 km/h")
    else:
        st.info("Nenhum congestionamento para exibir.")

with tab_calor:
    st.subheader("Zonas de Concentração de Incidentes")
    mapa_calor = generate_heatmap(df_filtered)
    if mapa_calor:
        st_folium(mapa_calor, width="100%", height=480, key="mapa_calor")
    else:
        st.info("Sem dados suficientes para mapa de calor.")

with tab_dados:
    st.subheader("Registros Filtrados")
    if not df_filtered.empty:
        df_display = df_filtered.copy()
        df_display['Google Maps'] = df_display.apply(
            lambda x: f"https://www.google.com/maps?q={x['lat']},{x['lon']}", axis=1
        )
        st.dataframe(
            df_display[['timestamp', 'type', 'subtype', 'street', 'Google Maps']],
            column_config={
                "timestamp":   st.column_config.DatetimeColumn("Horário", format="HH:mm"),
                "type":        "Tipo",
                "subtype":     "Subtipo",
                "street":      "Rua",
                "Google Maps": st.column_config.LinkColumn("📍 Ver no Maps"),
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Nenhum registro encontrado com os filtros aplicados.")

st.markdown("---")
st.info("💡 Passe o mouse sobre o mapa para ver coordenadas em tempo real no topo direito.")
st.caption(f"Última atualização manual: {st.session_state.manual_refreshes} vez(es). App online há {tempo_total//60} min.")
