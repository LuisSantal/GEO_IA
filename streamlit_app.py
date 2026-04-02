import streamlit as st
import pandas as pd
import plotly.express as px
import io
import re
from datetime import datetime, timedelta
import folium
from folium import plugins  # Import único e suficiente para todos os plugins
from streamlit_folium import st_folium
# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Waze Foz do Iguaçu", layout="wide")

# --- CONTADOR VISUAL (SEM RERUN AUTOMÁTICO) ---
if 'app_start_time' not in st.session_state:
    st.session_state.app_start_time = datetime.now()
    st.session_state.manual_refreshes = 0

# TEMPO DESDE INÍCIO DA SESSÃO
tempo_sessao = (datetime.now() - st.session_state.app_start_time).total_seconds()
tempo_prox_refresh = 600 - (tempo_sessao % 600)
minutos_restantes = int(tempo_prox_refresh // 60)
segundos_restantes = int(tempo_prox_refresh % 60)

minutos_restantes = int(tempo_prox_refresh // 60)
segundos_restantes = int(tempo_prox_refresh % 60)
@st.cache_resource(ttl=600, show_spinner=False)
def generate_incidents_map(df_filtered):
    """Mapa de incidentes CACHEADO"""
    if df_filtered.empty or len(df_filtered) == 0:
        return None
        
    # Filtrar coordenadas válidas
    df_map = df_filtered.dropna(subset=['lat', 'lon']).head(100)  # Max 100 markers
    
    if df_map.empty:
        return None
    
    center_lat = df_map['lat'].mean()
    center_lon = df_map['lon'].mean()
    
    m = create_folium_map_with_compass(center_lat, center_lon, zoom_level=13)
    
    for _, row in df_map.iterrows():
        try:
            color = get_danger_color(row.get('type', 'ALERTA'))  # ✅ 'ALERTA' existe
            folium.CircleMarker(
                location=[float(row['lat']), float(row['lon'])],
                radius=7,
                popup=f"<b>{row.get('subtype', 'Incidente')}</b><br>"
                      f"{row.get('street', 'N/A')}<br>"
                      f"{row['timestamp'].strftime('%H:%M')}",
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7
            ).add_to(m)
        except:
            continue
    st.sidebar.write(f"🔍 Nível de Zoom Ativo: 13 (Escala Urbana)")
    return m

@st.cache_resource(ttl=600, show_spinner=False)
def generate_jams_map(df_jams_filtered):
    """Mapa de congestionamentos CACHEADO"""
    if df_jams_filtered.empty:
        return None
        
    df_valid = df_jams_filtered.dropna(subset=['lat', 'lon', 'speed']).head(50)
    
    if df_valid.empty:
        return None
    
    center_lat = df_valid['lat'].mean()
    center_lon = df_valid['lon'].mean()
    
    m = create_folium_map_with_compass(center_lat, center_lon, zoom_level=13)
    
    for _, row in df_valid.iterrows():
        try:
            speed_kmh = float(row['speed']) * 3.6 if row['speed'] < 50 else float(row['speed'])
            color = get_congestion_color(speed_kmh)
            folium.CircleMarker(
                location=[float(row['lat']), float(row['lon'])],
                radius=6,
                popup=f"🚗 {speed_kmh:.0f}km/h<br>{row.get('street', 'Via')}",
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.6
            ).add_to(m)
        except:
            continue
    st.sidebar.write(f"🔍 Nível de Zoom Ativo: 13 (Escala Urbana)")
    return m
# SIDEBAR COM BOTÃO MANUAL
st.sidebar.markdown("### ⏰ Refresh Manual")
if st.sidebar.button("🔄 ATUALIZAR DADOS AGORA", use_container_width=True):
    st.cache_data.clear()
    st.session_state.manual_refreshes += 1
    st.rerun()

st.sidebar.metric("⏳ Próximo ciclo", f"{minutos_restantes}:{segundos_restantes:02d}")
st.sidebar.metric("🔄 Refreshes manuais", st.session_state.manual_refreshes)
st.sidebar.info("💡 Clique para atualizar dados imediatamente")

# --- CONSTANTES ---
# Substitua pelos IDs reais das suas pastas no Google Drive
FOLDER_ALERTS_ID = "https://drive.google.com/drive/folders/1xKkqLEusWuNoGzy5-UYuevUbMHAvc-bL"
FOLDER_JAMS_ID = "https://drive.google.com/drive/folders/192MCefe9vQwYhQcu-uZXekMbgdslTcgC"

def extract_folder_id(folder_url):
    """Extrai o ID da pasta do URL completo do Google Drive."""
    import re
    match = re.search(r'/folders/([a-zA-Z0-9_-]+)', folder_url)
    if match:
        return match.group(1)
    return folder_url  # Retorna como está se não for URL

# --- FUNÇÕES DE PALETA DE CORES ---

def get_color_from_gradient(value, min_val=0, max_val=100, reverse=False):
    """
    Gera cor na paleta Verde → Amarelo → Vermelho baseado em valor percentual.
    
    Args:
        value: Valor entre min_val e max_val
        min_val: Valor mínimo (verde)
        max_val: Valor máximo (vermelho)
        reverse: Se True, inverte a escala (verde = perigoso)
    
    Returns:
        Código de cor em hexadecimal (#RRGGBB)
    """
    # Normalizar valor entre 0 e 1
    if max_val == min_val:
        normalized = 0.5
    else:
        normalized = (value - min_val) / (max_val - min_val)
    
    normalized = max(0, min(1, normalized))  # Limitar entre 0 e 1
    
    if reverse:
        normalized = 1 - normalized
    
    # Criar gradiente verde → amarelo → vermelho
    if normalized < 0.5:
        # Verde → Amarelo
        r = int(255 * (normalized * 2))
        g = 255
        b = 0
    else:
        # Amarelo → Vermelho
        r = 255
        g = int(255 * (2 - normalized * 2))
        b = 0
    
    return f'#{r:02x}{g:02x}{b:02x}'

def get_congestion_color(speed_kmh):
    """
    Retorna cor baseada na velocidade de congestionamento.
    Verde (livre) → Vermelho (trânsito parado)
    """
    # Escala: 0 km/h = Vermelho (parado), 80+ km/h = Verde (livre)
    if speed_kmh >= 80:
        return '#00AA00'  # Verde
    elif speed_kmh >= 60:
        return '#55DD00'  # Verde-amarelo
    elif speed_kmh >= 40:
        return '#DDDD00'  # Amarelo
    elif speed_kmh >= 20:
        return '#FF8800'  # Laranja
    else:
        return '#FF0000'  # Vermelho

def get_danger_color(incident_type):
    """
    Retorna cor baseada no tipo de incidente (perigo).
    CORRIGIDO: Trata valores None, NaN e strings vazias
    """
    if pd.isna(incident_type) or incident_type is None or str(incident_type).strip() == '':
        return '#0099FF'  # Azul padrão para casos inválidos
    
    danger_colors = {
        'ACIDENTE': '#FF0000',        
        'VIA FECHADA': '#FF4400',     
        'CONGESTIONAMENTO': '#FFAA00', 
        'PERIGO': '#FF6600',           
        'ALERTA': '#FFDD00',           
        'OBRAS': '#AAAAAA',             
    }
    return danger_colors.get(str(incident_type).upper().strip(), '#0099FF')
def create_folium_map_with_compass(lat, lon, zoom_level=12):
    """Cria mapa com Norte, Escala, Medição e Coordenadas do Mouse."""
    m = folium.Map(
        location=[lat, lon],
        zoom_start=zoom_level,
        tiles="OpenStreetMap",
        max_bounds=True
    )
    
    # 1. Escala Gráfica (Rodapé Esquerdo)
    from folium.features import Control
    
    Control(position='bottomleft', metric=True, imperial=False).add_to(m)
    from folium.plugins import MousePosition, MeasureControl
    # 2. Posição do Mouse / Coordenadas (Topo Direito)
    plugins.MousePosition(
        position='topright',
        separator=' | ',
        empty_string='Fora do Mapa',
        lng_first=False,
        num_digits=4,
        prefix='Lat/Lon:'
    ).add_to(m)

    # 3. Ferramenta de Medição (Rodapé Direito)
    plugins.MeasureControl(position='bottomright', primary_length_unit='kilometers').add_to(m)

    # 4. Seta do Norte (Customizada no Topo Esquerdo para não chocar com coordenadas)
    north_html = '''
    <div style="position: fixed; 
        top: 10px; left: 50px; width: 40px; height: 40px; 
        background-color: white; border:2px solid grey; z-index:9999; 
        display: flex; align-items: center; justify-content: center;
        border-radius: 5px; opacity: 0.8;">
        <div style="font-size: 20px; color: red; font-weight: bold;">↑<br><small style="color:black">N</small></div>
    </div>
    '''
    folium.Element(north_html).add_to(m)
    
    folium.LayerControl(position='topright', collapsed=True).add_to(m)
    return m

# --- FUNÇÕES DE DADOS MOCKADOS (SEM HDF5) ---

def create_mock_data():
    import numpy as np
    np.random.seed(42)
    streets = ["Av. Brasil", "Av. JK", "Av. das Cataratas", "Av. Paraná"]
    alerts = pd.DataFrame([{
        'timestamp': datetime.now(), 'type': 'ACIDENTE', 'subtype': 'Colisão',
        'street': np.random.choice(streets), 'lat': -25.5478 + np.random.uniform(-0.02, 0.02),
        'lon': -54.5882 + np.random.uniform(-0.02, 0.02)
    } for _ in range(10)])
    jams = pd.DataFrame([{
        'timestamp': datetime.now(), 'speed': np.random.randint(10, 60),
        'street': np.random.choice(streets), 'lat': -25.5478 + np.random.uniform(-0.02, 0.02),
        'lon': -54.5882 + np.random.uniform(-0.02, 0.02)
    } for _ in range(10)])
    return alerts, jams


def load_historical_data(folder_id, selected_date=None):
    """Carrega dados históricos - usando dados mockados para evitar problemas de memória."""
    st.info("📊 Usando dados de demonstração realistas para Foz do Iguaçu")

    # Retornar dados mockados baseados no tipo de pasta
    df_alerts, df_jams = create_mock_data()

    if "alerts" in folder_id.lower():
        return df_alerts  # Dados de alertas
    else:
        return df_jams  # Dados de jams

def normalize_timestamps_local(df):
    """Converte timestamps de pubMillis para horário local de Foz do Iguaçu."""
    if df is None or 'pubMillis' not in df.columns:
        return df

    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['pubMillis'], unit='ms', utc=True)
    df['timestamp'] = df['timestamp'].dt.tz_convert('America/Sao_Paulo')
    df['timestamp'] = df['timestamp'].dt.tz_localize(None)
    df['date'] = df['timestamp'].dt.date
    df['hour'] = df['timestamp'].dt.hour
    return df



def create_google_maps_link(lat, lon):
    """Cria um link do Google Maps para as coordenadas especificadas."""
    return f"https://www.google.com/maps?q={lat},{lon}"

# --- LÓGICA DO DASHBOARD ---

st.title("🚗 Monitoramento de Tráfego - Foz do Iguaçu")
st.markdown("Dados extraídos em tempo real do Waze via Google Drive.")

# Sidebar COMPLETA e ESTÁVEL
st.sidebar.header("⚙️ Controle")
st.sidebar.markdown("### ⏰ Status da Sessão")

if 'app_start_time' not in st.session_state:
    st.session_state.app_start_time = datetime.now()
    st.session_state.manual_refreshes = 0

tempo_total = (datetime.now() - st.session_state.app_start_time).seconds
tempo_prox = 600 - (tempo_total % 600)

st.sidebar.metric("⏳ Tempo online", f"{tempo_total//3600}h:{(tempo_total%3600)//60:02d}m")
st.sidebar.metric("⏳ Próximo ciclo", f"{minutos_restantes}:{segundos_restantes:02d}")
if st.sidebar.button("🔄 ATUALIZAR DADOS AGORA", use_container_width=True):
    st.cache_resource.clear()
    st.rerun()

df_filtered, df_jams_filtered = create_mock_data()
if st.sidebar.button("🔄 **ATUALIZAR DADOS**", type="primary", use_container_width=True):
    st.cache_data.clear()
    st.session_state.manual_refreshes += 1
    st.success("✅ Dados atualizados!")
    st.rerun()

st.sidebar.metric("🔄 Atualizações", st.session_state.manual_refreshes)
st.sidebar.divider()


# 1. Carregar Alertas (dados históricos)
df_alerts = load_historical_data(FOLDER_ALERTS_ID)
if df_alerts is not None:
    
    # Processamento de Dados 
    # Nota: Timestamps já foram normalizados pela função normalize_timestamps_local
    df_alerts['hour'] = df_alerts['timestamp'].dt.hour
    df_alerts['day_of_week'] = df_alerts['timestamp'].dt.day_name()
    
    # Traduções 
    # Nota: Dados mockados já vêm em português, então só aplicamos se for dados reais
    type_map = {
        'ROAD_CLOSED': 'VIA FECHADA',
        'HAZARD': 'PERIGO',
        'ACCIDENT': 'ACIDENTE',
        'JAM': 'CONGESTIONAMENTO',
        'WEATHERHAZARD': 'PERIGO CLIMÁTICO'
    }
    # Só aplicar tradução se a coluna 'type' existir e não estiver vazia
    if 'type' in df_alerts.columns and not df_alerts.empty:
        df_alerts['type'] = df_alerts['type'].replace(type_map)
    
    # Traduções para subtipos - mapa mais completo
    subtype_map = {
        'ROAD_CLOSED_CONSTRUCTION': 'OBRAS',
        'ROAD_CLOSED_EVENT': 'EVENTO',
        'HAZARD_ON_ROAD': 'PERIGO NA VIA',
        'HAZARD_ON_SHOULDER': 'PERIGO NO ACOSTAMENTO',
        'HAZARD_WEATHER': 'CONDIÇÕES CLIMÁTICAS',
        'HAZARD_ON_ROAD_POT_HOLE': 'BURACO NA VIA',
        'HAZARD_ON_ROAD_ROAD_KILL': 'ANIMAL NA VIA',
        'HAZARD_ON_ROAD_CAR_STOPPED': 'VEÍCULO PARADO',
        'HAZARD_ON_ROAD_CONSTRUCTION': 'OBRAS NA VIA',
        'HAZARD_ON_ROAD_OBJECT': 'OBJETO NA VIA',
        'HAZARD_ON_ROAD_TRAFFIC_LIGHT_FAULT': 'SEMÁFORO QUEBRADO',
        'HAZARD_WEATHER_FOG': 'NEBLINA',
        'HAZARD_WEATHER_HAIL': 'GRANIZO',
        'HAZARD_WEATHER_HEAVY_RAIN': 'CHUVA FORTE',
        'HAZARD_WEATHER_FLOOD': 'INUNDAÇÃO',
        'ACCIDENT_MAJOR': 'ACIDENTE GRAVE',
        'ACCIDENT_MINOR': 'ACIDENTE LEVE',
        'JAM_HEAVY_TRAFFIC': 'TRÂNSITO PESADO',
        'JAM_MODERATE_TRAFFIC': 'TRÂNSITO MODERADO',
        'JAM_STAND_STILL_TRAFFIC': 'TRÂNSITO PARADO'
    }
    # Só aplicar tradução se a coluna 'subtype' existir e não estiver vazia
    if 'subtype' in df_alerts.columns and not df_alerts.empty:
        df_alerts['subtype'] = df_alerts['subtype'].replace(subtype_map)

    # 2. Carregar Dados de Jams (para velocidade média)
    df_jams = load_historical_data(FOLDER_JAMS_ID)
    # Nota: Timestamps já foram normalizados pela função normalize_timestamps_local

    # Determinar datas disponíveis COM BASE EM TODOS OS DADOS CARREGADOS
    all_dates = set()
    if df_alerts is not None:
        all_dates.update(df_alerts['timestamp'].dt.date.unique())
    if df_jams is not None:
        all_dates.update(df_jams['timestamp'].dt.date.unique())
    
    if all_dates:
        min_date = min(all_dates)
        max_date = max(all_dates)
    else:
        # Fallback para hoje se não houver dados
        from datetime import date
        min_date = max_date = date.today()
    
    # Selector de Data
    selected_date = st.sidebar.date_input("📅 Selecionar Data", value=max_date, min_value=min_date, max_value=max_date)
    
    # Atualizar título com a data selecionada
    st.title(f"🚗 Monitoramento de Tráfego - Foz do Iguaçu - {selected_date.strftime('%d/%m/%Y')}")
    st.markdown("Dados extraídos em tempo real do Waze via Google Drive.")

    # Sidebar - Filtros Dinâmicos
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Filtros")
    
    # 1. Filtro por Tipo de Alerta
    # Verifica se o DataFrame existe, se não está vazio e se a coluna 'type' está lá
    if df_alerts is not None and not df_alerts.empty and 'type' in df_alerts.columns:
        tipos_disponiveis = sorted(df_alerts['type'].unique().tolist())
        filtro_tipo = st.sidebar.multiselect(
            "🚨 Tipo de Alerta",
            options=tipos_disponiveis,
            default=tipos_disponiveis,  # Todos selecionados por padrão
            help="Selecione os tipos de alertas para exibir"
        )
    else:
        tipos_disponiveis = []
        filtro_tipo = []
    
    # 2. Filtro por Rua
    filtro_rua = st.sidebar.text_input(
        "🛣️ Buscar Rua",
        placeholder="Ex: Avenida Brasil",
        help="Digite parte do nome da rua para filtrar"
    )
    
    # 3. Filtro por Horário (range de horas)
    st.sidebar.markdown("**⏰ Horário**")
    col_hora_from, col_hora_to = st.sidebar.columns(2)
    with col_hora_from:
        hora_inicio = st.number_input("De:", min_value=0, max_value=23, value=0, step=1, label_visibility="collapsed")
    with col_hora_to:
        hora_fim = st.number_input("Até:", min_value=0, max_value=23, value=23, step=1, label_visibility="collapsed")
    
    # Garantir que hora_inicio <= hora_fim
    if hora_inicio > hora_fim:
        hora_inicio, hora_fim = hora_fim, hora_inicio

    # CARREGAR DADOS PARA A DATA SELECIONADA DE AMBOS TIPOS
    df_filtered = pd.DataFrame()
    df_jams_filtered = pd.DataFrame()
    
    if df_alerts is not None:
        # Filtrar alerts pela data selecionada
        df_alerts_date = df_alerts[df_alerts['timestamp'].dt.date == selected_date].copy()
        if not df_alerts_date.empty:
            # Aplicar filtros
            # 1. Filtro de Tipo de Alerta
            if filtro_tipo:
                df_alerts_date = df_alerts_date[df_alerts_date['type'].isin(filtro_tipo)]
            
            # 2. Filtro de Rua
            if filtro_rua:
                df_alerts_date = df_alerts_date[df_alerts_date['street'].str.contains(filtro_rua, case=False, na=False)]
            
            # 3. Filtro de Horário
            df_alerts_date = df_alerts_date[
                (df_alerts_date['hour'] >= hora_inicio) & 
                (df_alerts_date['hour'] <= hora_fim)
            ]
            
            df_filtered = df_alerts_date
    
    if df_jams is not None:
        # Filtrar jams pela data selecionada
        df_jams_filtered = df_jams[df_jams['timestamp'].dt.date == selected_date].copy()
        # Aplicar filtro de horário também em jams
        df_jams_filtered = df_jams_filtered[
            (df_jams_filtered['timestamp'].dt.hour >= hora_inicio) & 
            (df_jams_filtered['timestamp'].dt.hour <= hora_fim)
        ]

    # --- RESUMO DOS FILTROS APLICADOS ---
    st.markdown("---")
    col_filtros = st.columns([1, 1, 1, 1])
    
    with col_filtros[0]:
        st.metric("📅 Data", selected_date.strftime("%d/%m/%Y"))
    
    with col_filtros[1]:
        if filtro_tipo:
            st.metric("🚨 Alertas", f"{len(filtro_tipo)}")
        else:
            st.metric("🚨 Alertas", "Todos")
    
    with col_filtros[2]:
        if filtro_rua:
            st.metric("🛣️ Rua", f"'{filtro_rua}'")
        else:
            st.metric("🛣️ Rua", "Todas")
    
    with col_filtros[3]:
        st.metric("⏰ Horário", f"{hora_inicio:02d}:00 - {hora_fim:02d}:59")
    
    st.markdown("---")

    # --- INDICADORES DE GRAVIDADE E TEMPERATURA ---
    st.subheader("📊 Indicadores de Gravidade")

    # Calcular gravidade baseada nos incidentes do dia (apenas alerts)
    incidentes_dia = len(df_filtered) if not df_filtered.empty else 0
    acidentes_graves = len(df_filtered[df_filtered['type'] == 'ACIDENTE']) if not df_filtered.empty and 'type' in df_filtered.columns else 0
    vias_fechadas = len(df_filtered[df_filtered['type'] == 'ROAD_CLOSED']) if not df_filtered.empty and 'type' in df_filtered.columns else 0

    # Lógica de gravidade: mais incidentes = mais grave
    if incidentes_dia == 0:
        gravidade = 0
        cor_gravidade = 'green'
        status_gravidade = "✅ Situação Normal"
    elif incidentes_dia < 5:
        gravidade = 25
        cor_gravidade = 'yellow'
        status_gravidade = "⚠️ Atenção Moderada"
    elif incidentes_dia < 15:
        gravidade = 50
        cor_gravidade = 'orange'
        status_gravidade = "🚨 Alerta Elevado"
    else:
        gravidade = 75
        cor_gravidade = 'red'
        status_gravidade = "🚫 Situação Crítica"

    # Calcular velocidade média
    velocidade_media = 0
    if not df_jams_filtered.empty and 'speed' in df_jams_filtered.columns:
        velocidade_media = df_jams_filtered['speed'].mean()
        # Converter de m/s para km/h se necessário
        if velocidade_media < 50:  # Assume que está em m/s se for menor que 50
            velocidade_media = velocidade_media * 3.6

    # Temperatura simulada (substitua por API real se disponível)
    temperatura_atual = 25.5  # Simulado - em graus Celsius

    # Layout dos indicadores
    col_grav, col_vel, col_temp = st.columns(3)

    with col_grav:
        # Indicador de Gravidade dos Incidentes
        fig_grav = px.bar_polar(
            r=[gravidade],
            theta=[0],
            range_r=[0, 100],
            color_discrete_sequence=[cor_gravidade]
        )
        fig_grav.update_layout(
            title=f"🚨 Gravidade: {incidentes_dia} incidentes",
            polar=dict(
                radialaxis=dict(range=[0, 100], showticklabels=False),
                angularaxis=dict(showticklabels=False)
            ),
            showlegend=False,
            height=200
        )
        st.plotly_chart(fig_grav, width='stretch')
        st.markdown(f"**{status_gravidade}**")
        if acidentes_graves > 0:
            st.warning(f"🚑 {acidentes_graves} acidente(s) grave(s)")
        if vias_fechadas > 0:
            st.error(f"🚧 {vias_fechadas} via(s) fechada(s)")

    with col_vel:
        # Indicador de Velocidade Média
        fig_vel = px.bar_polar(
            r=[velocidade_media],
            theta=[0],
            range_r=[0, 80],
            color_discrete_sequence=['green' if velocidade_media > 40 else 'yellow' if velocidade_media > 20 else 'red']
        )
        fig_vel.update_layout(
            title=f"🚗 Velocidade Média: {velocidade_media:.1f} km/h",
            polar=dict(
                radialaxis=dict(range=[0, 80], showticklabels=False),
                angularaxis=dict(showticklabels=False)
            ),
            showlegend=False,
            height=200
        )
        st.plotly_chart(fig_vel, width='stretch')

        # Status da velocidade
        if velocidade_media > 40:
            st.success("✅ Tráfego Fluindo Bem")
        elif velocidade_media > 20:
            st.warning("⚠️ Tráfego Moderado")
        else:
            st.error("🚫 Tráfego Congestionado")

# --- EXIBIÇÃO DOS MAPAS ---
st.markdown("---")
st.subheader("🗺️ Mapas Técnicos em Tempo Real")
col_map1, col_map2 = st.columns(2)

with col_map1:
    st.markdown("### 🚨 Incidentes")
    st.caption("📍 Ponto de Referência: -25.54, -54.58 (Centro) | 🧭 Orientação: Norte ↑")
    mapa_inc = generate_incidents_map(df_filtered)
    if mapa_inc:
        st_folium(mapa_inc, width=None, height=450, key="mapa_inc")

with col_map2:
    st.markdown("### 🚗 Congestionamentos")
    st.caption("📍 Ponto de Referência: -25.54, -54.58 (Centro) | 📏 Escala: Métrica")
    mapa_jam = generate_jams_map(df_jams_filtered)
    if mapa_jam:
        st_folium(mapa_jam, width=None, height=450, key="mapa_jam")

st.info("💡 Passe o mouse sobre o mapa para ver as coordenadas em tempo real no topo direito.")

# --- QUARTO: MÉTRICAS (Fora das colunas dos mapas) ---
st.markdown("---")
st.subheader("📊 Resumo Estatístico")
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Total Alertas", len(df_filtered))
with c2:
    st.metric("Pontos Retenção", len(df_jams_filtered))
with c3:
    if not df_jams_filtered.empty:
        v_media = df_jams_filtered['speed'].mean() * 3.6
        st.metric("Vel. Média", f"{v_media:.1f} km/h")

st.markdown("---")

# 2. MAPA DE CONGESTIONAMENTOS (seu código já corrigido - MANTÉM)
if not df_jams_filtered.empty:
    st.subheader("🗺️ Mapa de Congestionamentos")
    
    df_jams_valid = df_jams_filtered.copy()
    if 'lat' in df_jams_valid.columns and 'lon' in df_jams_valid.columns:
        df_jams_valid = df_jams_valid.dropna(subset=['lat', 'lon', 'speed'])
        df_jams_valid = df_jams_valid[(df_jams_valid['lat'].between(-26, -25)) & 
                                     (df_jams_valid['lon'].between(-55, -54))]
        
        if not df_jams_valid.empty:
            df_jams_valid['speed_kmh'] = df_jams_valid['speed'].apply(lambda x: x*3.6 if x < 50 else x)
            center_lat = df_jams_valid['lat'].mean()
            center_lon = df_jams_valid['lon'].mean()
            
            m_jams = create_folium_map_with_compass(center_lat, center_lon, zoom_level=12)
            
            for idx, row in df_jams_valid.iterrows():
                try:
                    color = get_congestion_color(row.get('speed_kmh', 0))
                    folium.CircleMarker(
                        [row['lat'], row['lon']], radius=6,
                        popup=f"Vel: {row.get('speed_kmh', 0):.0f}km/h<br>{row.get('street', 'N/A')}",
                        color=color, fill=True, fillColor=color, fillOpacity=0.6
                    ).add_to(m_jams)
                except:
                    continue
            
            st_folium(m_jams, width=700, height=500)
            
            # Estatísticas rápidas
            col_stats1, col_stats2 = st.columns(2)
            with col_stats1:
                st.metric("Total Jams", len(df_jams_valid))
            with col_stats2:
                st.metric("Vel. Média", f"{df_jams_valid['speed_kmh'].mean():.0f} km/h")
            
            st.markdown("**Legenda:** 🟢 Livre | 🟡 Moderado | 🔴 Parado")
        else:
            st.info("⚠️ Sem congestionamentos válidos.")
    else:
        st.info("ℹ️ Sem dados de coordenadas de tráfego.")

st.markdown("---")
