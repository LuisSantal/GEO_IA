import streamlit as st
import pandas as pd
import plotly.express as px
import io
import re
import tempfile
import random
from datetime import datetime, timedelta, date
import folium
from folium import plugins
from streamlit_folium import st_folium

# =============================================
# 1. CONFIGURAÇÃO DA PÁGINA
# =============================================
st.set_page_config(
    page_title="Waze Foz do Iguaçu",
    layout="wide",
    page_icon="🚗"
)

# =============================================
# 2. ESTADO DA SESSÃO
# =============================================
if 'app_start_time' not in st.session_state:
    st.session_state.app_start_time = datetime.now()
    st.session_state.manual_refreshes = 0
if 'use_mock_data' not in st.session_state:
    st.session_state.use_mock_data = False

tempo_sessao = (datetime.now() - st.session_state.app_start_time).total_seconds()
tempo_prox_refresh = 600 - (tempo_sessao % 600)
minutos_restantes = int(tempo_prox_refresh // 60)
segundos_restantes = int(tempo_prox_refresh % 60)
tempo_total = int(tempo_sessao)

# =============================================
# 3. IDs DAS PASTAS DO GOOGLE DRIVE
# =============================================
FOLDER_ALERTS_ID = "1xKkqLEusWuNoGzy5-UYuevUbMHAvc-bL"
FOLDER_JAMS_ID   = "192MCefe9vQwYhQcu-uZXekMbgdslTcgC"

# =============================================
# 4. FUNÇÕES DE CORES
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
        'ACIDENTE': '#FF0000',
        'VIA FECHADA': '#FF4400',
        'CONGESTIONAMENTO': '#FFAA00',
        'PERIGO': '#FF6600',
        'ALERTA': '#FFDD00',
        'OBRAS': '#AAAAAA',
    }
    return danger_colors.get(str(incident_type).upper().strip(), '#0099FF')

# =============================================
# 5. CONEXÃO COM GOOGLE DRIVE (SERVICE ACCOUNT)
# =============================================
@st.cache_resource(show_spinner=False)
def get_drive_service():
    """
    Autentica via Service Account usando st.secrets.
    Configure em .streamlit/secrets.toml:
      [gcp_service_account]
      type = "service_account"
      project_id = "..."
      private_key_id = "..."
      private_key = "-----BEGIN RSA PRIVATE KEY-----\\n..."
      client_email = "..."
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds_info = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(
            creds_info,
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        return build('drive', 'v3', credentials=creds)
    except Exception:
        st.session_state.use_mock_data = True
        return None

def get_latest_h5_id(folder_id):
    """
    Encontra o arquivo .h5 mais recente na pasta do Drive
    baseando-se no timestamp numérico no nome. Ex: alerts1774879588.h5
    """
    service = get_drive_service()
    if service is None:
        return None
    try:
        query = f"'{folder_id}' in parents and name contains '.h5' and trashed=false"
        results = service.files().list(
            q=query,
            fields="files(id, name, modifiedTime)",
            orderBy="modifiedTime desc",
            pageSize=20
        ).execute()
        files = results.get('files', [])
        if not files:
            return None

        latest_id  = None
        latest_ts  = -1
        for f in files:
            match = re.search(r'(\d{8,})', f['name'])
            if match:
                ts = int(match.group(1))
                if ts > latest_ts:
                    latest_ts = ts
                    latest_id = f['id']

        # Fallback: primeiro arquivo (ordenado por modifiedTime desc)
        if latest_id is None and files:
            latest_id = files[0]['id']

        return latest_id
    except Exception as e:
        st.warning(f"⚠️ Erro ao listar arquivos do Drive: {e}")
        st.session_state.use_mock_data = True
        return None

@st.cache_data(ttl=600, show_spinner="📥 Baixando dados do Drive...")
def load_hdf_from_drive(file_id):
    """
    Baixa o arquivo .h5 do Google Drive e carrega como DataFrame.
    Retorna None em caso de falha.
    """
    if not file_id:
        return None
    try:
        from googleapiclient.http import MediaIoBaseDownload

        service = get_drive_service()
        if service is None:
            return None

        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.h5') as tmp:
            tmp.write(fh.getvalue())
            tmp_path = tmp.name

        df = pd.read_hdf(tmp_path, key='s')
        return df
    except Exception as e:
        st.warning(f"⚠️ Falha ao carregar HDF5: {e}")
        st.session_state.use_mock_data = True
        return None

# =============================================
# 6. NORMALIZAÇÃO DE TIMESTAMPS
# =============================================
def normalize_timestamps(df):
    """
    Converte pubMillis (epoch ms UTC) → horário local Foz do Iguaçu.
    Adiciona colunas: timestamp, date, hour, day_of_week.
    """
    if df is None or df.empty:
        return df
    df = df.copy()

    if 'pubMillis' in df.columns:
        df['timestamp'] = pd.to_datetime(df['pubMillis'], unit='ms', utc=True)
        df['timestamp'] = df['timestamp'].dt.tz_convert('America/Sao_Paulo').dt.tz_localize(None)
    elif 'timestamp' not in df.columns:
        df['timestamp'] = datetime.now()

    df['date']        = df['timestamp'].dt.date
    df['hour']        = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.day_name()
    return df

# =============================================
# 7. EXTRAÇÃO DE COORDENADAS
# =============================================
def extract_coordinates(df):
    """
    Extrai lat/lon de diferentes formatos nos dados do Waze:
    - 'location' como dict {'x': lon, 'y': lat}
    - 'location' como string "{'x': ..., 'y': ...}"
    - Colunas separadas 'x' e 'y'
    - Colunas 'lat' e 'lon' já existentes
    """
    if df is None or df.empty:
        return df
    df = df.copy()

    if 'lat' in df.columns and 'lon' in df.columns:
        return df

    if 'location' in df.columns:
        try:
            sample = df['location'].dropna().iloc[0] if not df['location'].dropna().empty else None
            if isinstance(sample, str):
                import ast
                df['location'] = df['location'].apply(
                    lambda x: ast.literal_eval(x) if isinstance(x, str) else x
                )
            df['lat'] = df['location'].apply(lambda x: float(x.get('y', 0)) if isinstance(x, dict) else None)
            df['lon'] = df['location'].apply(lambda x: float(x.get('x', 0)) if isinstance(x, dict) else None)
        except Exception:
            pass

    if 'lat' not in df.columns and 'y' in df.columns:
        df['lat'] = pd.to_numeric(df['y'], errors='coerce')
    if 'lon' not in df.columns and 'x' in df.columns:
        df['lon'] = pd.to_numeric(df['x'], errors='coerce')

    return df

# =============================================
# 8. TRADUÇÕES WAZE → PT-BR
# =============================================
TYPE_MAP = {
    'ROAD_CLOSED': 'VIA FECHADA', 'ROAD_CLOSED_CONSTRUCTION': 'VIA FECHADA',
    'ROAD_CLOSED_EVENT': 'VIA FECHADA', 'HAZARD': 'PERIGO',
    'ACCIDENT': 'ACIDENTE', 'JAM': 'CONGESTIONAMENTO',
    'WEATHERHAZARD': 'PERIGO CLIMÁTICO',
}
SUBTYPE_MAP = {
    'ROAD_CLOSED_CONSTRUCTION': 'OBRAS', 'ROAD_CLOSED_EVENT': 'EVENTO',
    'HAZARD_ON_ROAD': 'PERIGO NA VIA', 'HAZARD_ON_SHOULDER': 'PERIGO NO ACOSTAMENTO',
    'HAZARD_WEATHER': 'CONDIÇÕES CLIMÁTICAS', 'HAZARD_ON_ROAD_POT_HOLE': 'BURACO NA VIA',
    'HAZARD_ON_ROAD_ROAD_KILL': 'ANIMAL NA VIA', 'HAZARD_ON_ROAD_CAR_STOPPED': 'VEÍCULO PARADO',
    'HAZARD_ON_ROAD_CONSTRUCTION': 'OBRAS NA VIA', 'HAZARD_ON_ROAD_OBJECT': 'OBJETO NA VIA',
    'HAZARD_ON_ROAD_TRAFFIC_LIGHT_FAULT': 'SEMÁFORO QUEBRADO',
    'HAZARD_WEATHER_FOG': 'NEBLINA', 'HAZARD_WEATHER_HAIL': 'GRANIZO',
    'HAZARD_WEATHER_HEAVY_RAIN': 'CHUVA FORTE', 'HAZARD_WEATHER_FLOOD': 'INUNDAÇÃO',
    'ACCIDENT_MAJOR': 'ACIDENTE GRAVE', 'ACCIDENT_MINOR': 'ACIDENTE LEVE',
    'JAM_HEAVY_TRAFFIC': 'TRÂNSITO PESADO', 'JAM_MODERATE_TRAFFIC': 'TRÂNSITO MODERADO',
    'JAM_STAND_STILL_TRAFFIC': 'TRÂNSITO PARADO',
}

def translate_dataframe(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    if 'type' in df.columns:
        df['type'] = df['type'].replace(TYPE_MAP)
    if 'subtype' in df.columns:
        df['subtype'] = df['subtype'].replace(SUBTYPE_MAP)
    return df

# =============================================
# 9. DADOS MOCKADOS — CORREÇÃO ERRO 3
# ✅ Usa random.choice() puro (sem numpy) para evitar
#    ValueError com lista de tuplas mistas
# =============================================
def create_mock_data():
    """Dados mockados realistas de Foz do Iguaçu para demonstração."""
    foz_streets = [
        ("Av. Brasil",           -25.5475, -54.5870),
        ("Av. JK",               -25.5502, -54.5851),
        ("Av. das Cataratas",    -25.5531, -54.5792),
        ("Av. Paraná",           -25.5458, -54.5901),
        ("Ponte Tancredo Neves", -25.5412, -54.5955),
        ("Rod. BR-277",          -25.5600, -54.5800),
        ("Av. Costa e Silva",    -25.5480, -54.5820),
        ("R. Edmundo de Barros", -25.5460, -54.5890),
    ]
    subtipos = [
        'Colisão frontal', 'Carro parado', 'Buraco na pista',
        'Obras na via', 'Semáforo quebrado', 'Animal na pista',
        'Acidente grave', 'Acidente leve', 'Inundação'
    ]
    tipos = ['ACIDENTE', 'VIA FECHADA', 'PERIGO', 'OBRAS', 'ALERTA']

    alerts_data, jams_data = [], []

    for _ in range(20):
        # ✅ CORRIGIDO: random.choice() em vez de np.random.choice()
        street, base_lat, base_lon = random.choice(foz_streets)
        alerts_data.append({
            'timestamp': datetime.now() - timedelta(minutes=random.randint(0, 120)),
            'type':    random.choice(tipos),
            'subtype': random.choice(subtipos),
            'street':  street,
            'lat': round(base_lat + random.uniform(-0.005, 0.005), 6),
            'lon': round(base_lon + random.uniform(-0.005, 0.005), 6),
        })

    for _ in range(15):
        # ✅ CORRIGIDO: random.choice() em vez de np.random.choice()
        street, base_lat, base_lon = random.choice(foz_streets)
        jams_data.append({
            'timestamp': datetime.now() - timedelta(minutes=random.randint(0, 60)),
            'speed':  round(random.uniform(5, 45), 1),
            'street': street,
            'lat': round(base_lat + random.uniform(-0.003, 0.003), 6),
            'lon': round(base_lon + random.uniform(-0.003, 0.003), 6),
        })

    df_alerts = pd.DataFrame(alerts_data)
    df_jams   = pd.DataFrame(jams_data)

    for df in [df_alerts, df_jams]:
        df['hour']        = df['timestamp'].dt.hour
        df['date']        = df['timestamp'].dt.date
        df['day_of_week'] = df['timestamp'].dt.day_name()

    return df_alerts, df_jams

# =============================================
# 10. PIPELINE PRINCIPAL DE DADOS
# =============================================
@st.cache_data(ttl=600, show_spinner="🔄 Carregando dados...")
def load_all_data():
    """
    Tenta Google Drive primeiro.
    Fallback automático para dados mockados se:
    - st.secrets não tiver 'gcp_service_account'
    - Drive não retornar arquivos
    - HDF5 falhar ao carregar
    """
    if not st.session_state.get('use_mock_data', False):
        try:
            alerts_id = get_latest_h5_id(FOLDER_ALERTS_ID)
            jams_id   = get_latest_h5_id(FOLDER_JAMS_ID)

            df_alerts_raw = load_hdf_from_drive(alerts_id) if alerts_id else None
            df_jams_raw   = load_hdf_from_drive(jams_id)   if jams_id   else None

            if df_alerts_raw is not None:
                df_alerts_raw = normalize_timestamps(df_alerts_raw)
                df_alerts_raw = extract_coordinates(df_alerts_raw)
                df_alerts_raw = translate_dataframe(df_alerts_raw)
                if 'street' not in df_alerts_raw.columns:
                    df_alerts_raw['street'] = 'N/A'

            if df_jams_raw is not None:
                df_jams_raw = normalize_timestamps(df_jams_raw)
                df_jams_raw = extract_coordinates(df_jams_raw)
                if 'speed' not in df_jams_raw.columns and 'speedKMH' in df_jams_raw.columns:
                    df_jams_raw['speed'] = df_jams_raw['speedKMH'] / 3.6
                if 'street' not in df_jams_raw.columns:
                    df_jams_raw['street'] = 'Via'

            if df_alerts_raw is not None or df_jams_raw is not None:
                return (
                    df_alerts_raw if df_alerts_raw is not None else pd.DataFrame(),
                    df_jams_raw   if df_jams_raw   is not None else pd.DataFrame(),
                    "drive"
                )
        except Exception:
            pass

    df_alerts, df_jams = create_mock_data()
    return df_alerts, df_jams, "mock"

# =============================================
# 11. FUNÇÕES DE MAPA — CORREÇÃO ERROS 1 e 2
# ✅ Removido folium.ScaleControl (não existe)
# ✅ Removido from folium.features import Control (não existe)
# ✅ Usa apenas plugins.MeasureControl (compatível)
# =============================================
def create_folium_map_with_compass(lat, lon, zoom_level=13):
    m = folium.Map(
        location=[lat, lon],
        zoom_start=zoom_level,
        tiles="OpenStreetMap",
        max_bounds=True
    )

    # ✅ Coordenadas do mouse (topo direito)
    plugins.MousePosition(
        position='topright',
        separator=' | ',
        prefix='Lat/Lon: ',
        num_digits=5
    ).add_to(m)

    # ✅ Ferramenta de medição (rodapé direito) — substitui ScaleControl
    plugins.MeasureControl(position='bottomright').add_to(m)

    # ✅ Seta Norte fixa (topo esquerdo)
    north_html = '''
    <div style="position:fixed;top:10px;left:10px;width:45px;height:45px;
        background:linear-gradient(145deg,#f0f0f0,#e6e6e6);
        border:2px solid #333;border-radius:8px;z-index:1000;
        box-shadow:0 2px 10px rgba(0,0,0,0.3);
        display:flex;align-items:center;justify-content:center;
        font-weight:bold;font-size:18px;">
        <div style="color:#d32f2f;text-shadow:1px 1px 1px white;">↑</div>
        <div style="position:absolute;bottom:2px;font-size:9px;color:#333;font-weight:bold;">N</div>
    </div>'''
    folium.Element(north_html).add_to(m)
    folium.LayerControl(position='topright', collapsed=True).add_to(m)
    return m

@st.cache_resource(ttl=600, show_spinner=False)
def generate_incidents_map(df_json):
    df = pd.read_json(io.StringIO(df_json))
    if df.empty:
        return None
    df_map = df.dropna(subset=['lat', 'lon']).head(50)
    df_map = df_map[
        (df_map['lat'].between(-25.60, -25.52)) &
        (df_map['lon'].between(-54.65, -54.55))
    ]
    if df_map.empty:
        return None

    m = create_folium_map_with_compass(df_map['lat'].mean(), df_map['lon'].mean())
    for _, row in df_map.iterrows():
        try:
            color = get_danger_color(row.get('type', 'ALERTA'))
            ts = pd.to_datetime(row['timestamp']).strftime('%H:%M') if pd.notna(row.get('timestamp')) else '--'
            popup_html = f"""
            <div style="min-width:200px;font-family:Arial;">
                <b style="color:{color};font-size:16px;">🚨 {row.get('type','?')}</b><br>
                <b>{row.get('subtype','')}</b><br>
                🛣️ <i>{row.get('street','N/A')}</i><br>
                🕒 {ts}<br>
                📍 {float(row['lat']):.4f}, {float(row['lon']):.4f}
            </div>"""
            folium.CircleMarker(
                location=[float(row['lat']), float(row['lon'])],
                radius=9,
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{row.get('type','?')}: {row.get('street','N/A')}",
                color=color, fill=True, fillColor=color,
                fillOpacity=0.8, weight=2
            ).add_to(m)
        except Exception:
            continue
    return m

@st.cache_resource(ttl=600, show_spinner=False)
def generate_jams_map(df_json):
    df = pd.read_json(io.StringIO(df_json))
    if df.empty:
        return None
    df_valid = df.dropna(subset=['lat', 'lon', 'speed']).head(40)
    df_valid = df_valid[
        (df_valid['lat'].between(-25.60, -25.52)) &
        (df_valid['lon'].between(-54.65, -54.55))
    ]
    if df_valid.empty:
        return None

    m = create_folium_map_with_compass(df_valid['lat'].mean(), df_valid['lon'].mean())
    for _, row in df_valid.iterrows():
        try:
            speed_kmh = float(row['speed']) * 3.6
            color = get_congestion_color(speed_kmh)
            ts = pd.to_datetime(row['timestamp']).strftime('%H:%M') if pd.notna(row.get('timestamp')) else '--'
            popup_html = f"""
            <div style="min-width:180px;">
                <b style="color:{color}">🚗 {speed_kmh:.0f} km/h</b><br>
                🛣️ <i>{row.get('street','Via')}</i><br>
                🕒 {ts}
            </div>"""
            folium.CircleMarker(
                location=[float(row['lat']), float(row['lon'])],
                radius=7,
                popup=folium.Popup(popup_html, max_width=220),
                tooltip=f"{speed_kmh:.0f}km/h - {row.get('street','Via')}",
                color=color, fill=True, fillColor=color, fillOpacity=0.7
            ).add_to(m)
        except Exception:
            continue
    return m

@st.cache_resource(ttl=600, show_spinner=False)
def generate_heatmap(df_json):
    df = pd.read_json(io.StringIO(df_json))
    if df.empty:
        return None
    df_map = df.dropna(subset=['lat', 'lon'])
    if df_map.empty:
        return None
    m = create_folium_map_with_compass(df_map['lat'].mean(), df_map['lon'].mean())
    heat_data = [[row['lat'], row['lon']] for _, row in df_map.iterrows()]
    plugins.HeatMap(heat_data, radius=15, blur=10).add_to(m)
    return m

# =============================================
# 12. SIDEBAR
# =============================================
st.sidebar.header("⚙️ Controles")
st.sidebar.markdown("### ⏰ Status da Sessão")
st.sidebar.metric("⏳ Tempo online",  f"{tempo_total//3600}h:{(tempo_total%3600)//60:02d}m")
st.sidebar.metric("⏳ Próximo ciclo", f"{minutos_restantes}:{segundos_restantes:02d}")
st.sidebar.metric("🔄 Atualizações",  st.session_state.manual_refreshes)

if st.sidebar.button("🔄 ATUALIZAR DADOS AGORA", use_container_width=True, type="primary"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.session_state.manual_refreshes += 1
    st.rerun()

st.sidebar.divider()

# =============================================
# 13. CARREGAMENTO DE DADOS
# =============================================
df_alerts_raw, df_jams_raw, fonte = load_all_data()

# Garante colunas auxiliares
for df_ref in [df_alerts_raw, df_jams_raw]:
    if not df_ref.empty:
        if 'hour' not in df_ref.columns:
            df_ref['hour'] = df_ref['timestamp'].dt.hour
        if 'date' not in df_ref.columns:
            df_ref['date'] = df_ref['timestamp'].dt.date

# =============================================
# 14. FILTROS NA SIDEBAR
# =============================================
st.sidebar.subheader("🔍 Filtros")

all_dates = set()
if not df_alerts_raw.empty: all_dates.update(df_alerts_raw['date'].unique())
if not df_jams_raw.empty:   all_dates.update(df_jams_raw['date'].unique())
min_date = min(all_dates) if all_dates else date.today()
max_date = max(all_dates) if all_dates else date.today()

selected_date = st.sidebar.date_input(
    "📅 Data", value=max_date, min_value=min_date, max_value=max_date
)

tipos_disponiveis = sorted(df_alerts_raw['type'].dropna().unique().tolist()) if not df_alerts_raw.empty else []
filtro_tipo = st.sidebar.multiselect(
    "🚨 Tipo de Alerta",
    options=tipos_disponiveis,
    default=tipos_disponiveis,
)

filtro_rua = st.sidebar.text_input("🛣️ Buscar Rua", placeholder="Ex: Av. Brasil")
hora_range = st.sidebar.slider("⏰ Horário", 0, 23, (0, 23))

# =============================================
# 15. APLICAÇÃO DOS FILTROS
# =============================================
df_filtered = pd.DataFrame()
if not df_alerts_raw.empty:
    df_filtered = df_alerts_raw[
        (df_alerts_raw['date'] == selected_date) &
        (df_alerts_raw['type'].isin(filtro_tipo)) &
        (df_alerts_raw['hour'].between(hora_range[0], hora_range[1]))
    ].copy()
    if filtro_rua:
        df_filtered = df_filtered[
            df_filtered['street'].str.contains(filtro_rua, case=False, na=False)
        ]

df_jams_filtered = pd.DataFrame()
if not df_jams_raw.empty:
    df_jams_filtered = df_jams_raw[
        (df_jams_raw['date'] == selected_date) &
        (df_jams_raw['hour'].between(hora_range[0], hora_range[1]))
    ].copy()

# =============================================
# 16. CABEÇALHO
# =============================================
st.title(f"🚗 Monitoramento de Tráfego — Foz do Iguaçu | {selected_date.strftime('%d/%m/%Y')}")

if fonte == "mock":
    st.warning(
        "⚠️ **Modo demonstração** — dados simulados. "
        "Configure `st.secrets['gcp_service_account']` para usar dados reais do Google Drive.",
        icon="🟡"
    )
else:
    st.success("✅ **Dados reais** carregados do Google Drive.", icon="🟢")

st.markdown("---")

# =============================================
# 17. RESUMO DOS FILTROS ATIVOS
# =============================================
col_f1, col_f2, col_f3, col_f4 = st.columns(4)
col_f1.metric("📅 Data",    selected_date.strftime("%d/%m/%Y"))
col_f2.metric("🚨 Alertas", f"{len(filtro_tipo)} tipos")
col_f3.metric("🛣️ Rua",     f"'{filtro_rua}'" if filtro_rua else "Todas")
col_f4.metric("⏰ Horário", f"{hora_range[0]:02d}:00–{hora_range[1]:02d}:59")
st.markdown("---")

# =============================================
# 18. KPIs PRINCIPAIS
# =============================================
st.subheader("📊 Resumo Estatístico")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

incidentes_dia   = len(df_filtered)
acidentes_graves = len(df_filtered[df_filtered['type'] == 'ACIDENTE']) if not df_filtered.empty else 0
v_media_kmh      = (df_jams_filtered['speed'].mean() * 3.6) if not df_jams_filtered.empty else 0
status_via       = "🚫 Crítico" if incidentes_dia > 15 else ("⚠️ Moderado" if incidentes_dia > 5 else "✅ Normal")

kpi1.metric("Total Alertas",  incidentes_dia)
kpi2.metric("Acidentes",      acidentes_graves)
kpi3.metric("Vel. Média",     f"{v_media_kmh:.1f} km/h")
kpi4.metric("Status da Via",  status_via)

st.markdown("---")

# =============================================
# 19. INDICADORES VISUAIS DE GRAVIDADE
# =============================================
st.subheader("📈 Indicadores de Gravidade")
col_grav, col_vel = st.columns(2)

gravidade = min(75, incidentes_dia * 5)
cor_grav  = '#FF0000' if gravidade >= 75 else ('#FF8800' if gravidade >= 50 else ('#FFDD00' if gravidade >= 25 else '#00AA00'))

with col_grav:
    fig_grav = px.bar_polar(
        r=[gravidade], theta=[0], range_r=[0, 100],
        color_discrete_sequence=[cor_grav]
    )
    fig_grav.update_layout(
        title=f"🚨 Gravidade: {incidentes_dia} incidentes",
        polar=dict(
            radialaxis=dict(range=[0, 100], showticklabels=False),
            angularaxis=dict(showticklabels=False)
        ),
        showlegend=False, height=220
    )
    st.plotly_chart(fig_grav, use_container_width=True)

cor_vel = 'green' if v_media_kmh > 40 else ('yellow' if v_media_kmh > 20 else 'red')

with col_vel:
    fig_vel = px.bar_polar(
        r=[v_media_kmh], theta=[0], range_r=[0, 80],
        color_discrete_sequence=[cor_vel]
    )
    fig_vel.update_layout(
        title=f"🚗 Velocidade Média: {v_media_kmh:.1f} km/h",
        polar=dict(
            radialaxis=dict(range=[0, 80], showticklabels=False),
            angularaxis=dict(showticklabels=False)
        ),
        showlegend=False, height=220
    )
    st.plotly_chart(fig_vel, use_container_width=True)

st.markdown("---")

# =============================================
# 20. ABAS DE VISUALIZAÇÃO
# =============================================
st.subheader("🗺️ Visualizações")
tab_inc, tab_jams, tab_calor, tab_graficos, tab_dados = st.tabs([
    "📍 Incidentes",
    "🚗 Congestionamentos",
    "🔥 Mapa de Calor",
    "📊 Gráficos",
    "📋 Dados Detalhados"
])

# --- ABA 1: Incidentes ---
with tab_inc:
    st.caption("📍 Centro: -25.54, -54.58 | 🧭 Norte ↑ | Clique nos pontos para detalhes")
    if not df_filtered.empty:
        m_inc = generate_incidents_map(df_filtered.to_json())
        if m_inc:
            st_folium(m_inc, width="100%", height=500, key="mapa_inc")
        else:
            st.info("⚠️ Nenhum incidente dentro da área de Foz do Iguaçu.")
    else:
        st.info("Nenhum incidente com os filtros aplicados.")

# --- ABA 2: Congestionamentos ---
with tab_jams:
    st.caption("📏 Escala métrica | 🟢 Livre → 🔴 Parado")
    if not df_jams_filtered.empty:
        m_jam = generate_jams_map(df_jams_filtered.to_json())
        if m_jam:
            st_folium(m_jam, width="100%", height=500, key="mapa_jam")
            st.markdown("**Legenda:** 🟢 >80 km/h | 🟡 40–80 km/h | 🟠 20–40 km/h | 🔴 <20 km/h")
        else:
            st.info("⚠️ Nenhum congestionamento na área filtrada.")
    else:
        st.info("Nenhum congestionamento para exibir.")

# --- ABA 3: Mapa de Calor ---
with tab_calor:
    st.subheader("Zonas de Concentração de Incidentes")
    if not df_filtered.empty:
        m_heat = generate_heatmap(df_filtered.to_json())
        if m_heat:
            st_folium(m_heat, width="100%", height=500, key="mapa_calor")
    else:
        st.info("Sem dados suficientes para mapa de calor.")

# --- ABA 4: Gráficos ---
with tab_graficos:
    if not df_filtered.empty:
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.subheader("📊 Incidentes por Hora")
            fig_hora = px.bar(
                df_filtered['hour'].value_counts().sort_index().reset_index(),
                x='hour', y='count',
                labels={'hour': 'Hora', 'count': 'Qtd'},
                color='count', color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_hora, use_container_width=True)

        with col_g2:
            st.subheader("🥧 Proporção por Tipo")
            fig_pie = px.pie(
                df_filtered, names='type',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        if 'day_of_week' in df_filtered.columns:
            st.subheader("📅 Incidentes por Dia da Semana")
            order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
            dow_counts = df_filtered['day_of_week'].value_counts().reindex(order).dropna().reset_index()
            dow_counts.columns = ['day_of_week', 'count']
            fig_dow = px.bar(
                dow_counts, x='day_of_week', y='count',
                labels={'day_of_week': 'Dia', 'count': 'Qtd'},
                color='count', color_continuous_scale='Blues'
            )
            st.plotly_chart(fig_dow, use_container_width=True)
    else:
        st.info("Sem dados para gerar gráficos.")

# --- ABA 5: Dados Detalhados ---
with tab_dados:
    st.subheader("Registros Filtrados")
    if not df_filtered.empty:
        df_display = df_filtered.copy()
        df_display['Google Maps'] = df_display.apply(
            lambda x: f"https://www.google.com/maps?q={x.get('lat',0)},{x.get('lon',0)}", axis=1
        )
        cols_show = [c for c in ['timestamp','type','subtype','street','Google Maps'] if c in df_display.columns]
        st.dataframe(
            df_display[cols_show].sort_values('timestamp', ascending=False),
            column_config={
                "timestamp":   st.column_config.DatetimeColumn("Horário", format="DD/MM HH:mm"),
                "type":        "Tipo",
                "subtype":     "Subtipo",
                "street":      "Rua",
                "Google Maps": st.column_config.LinkColumn("📍 Ver no Maps"),
            },
            use_container_width=True,
            hide_index=True
        )
        csv = df_display[cols_show].to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Baixar CSV", csv, "alertas_foz.csv", "text/csv")
    else:
        st.info("Nenhum registro com os filtros aplicados.")

# =============================================
# 21. RODAPÉ
# =============================================
st.markdown("---")
st.info("💡 Passe o mouse sobre os mapas para ver coordenadas em tempo real no canto superior direito.")
st.caption(
    f"Fonte: {'Google Drive (dados reais)' if fonte == 'drive' else 'Dados de demonstração'} | "
    f"Atualizações manuais: {st.session_state.manual_refreshes} | "
    f"App online há {tempo_total // 60} min"
)
