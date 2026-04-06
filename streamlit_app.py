import streamlit as st
import pandas as pd
import plotly.express as px
import io
import re
import tempfile
from datetime import datetime, date
import pytz
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
# 2. TIMEZONE E HORA LOCAL
# =============================================
TZ_FOZ = pytz.timezone("America/Sao_Paulo")

def now_foz():
    """Retorna datetime atual no horário de Foz do Iguaçu."""
    return datetime.now(TZ_FOZ)

# =============================================
# 3. ESTADO DA SESSÃO
# =============================================
if 'app_start_time' not in st.session_state:
    st.session_state.app_start_time = now_foz()
    st.session_state.manual_refreshes = 0

tempo_sessao = (now_foz() - st.session_state.app_start_time).total_seconds()
tempo_prox_refresh = 600 - (tempo_sessao % 600)
minutos_restantes = int(tempo_prox_refresh // 60)
segundos_restantes = int(tempo_prox_refresh % 60)
tempo_total = int(tempo_sessao)

# =============================================
# 4. IDs DAS PASTAS DO GOOGLE DRIVE
# =============================================
FOLDER_ALERTS_ID = "1xKkqLEusWuNoGzy5-UYuevUbMHAvc-bL"
FOLDER_JAMS_ID   = "192MCefe9vQwYhQcu-uZXekMbgdslTcgC"

# =============================================
# 5. FUNÇÕES DE CORES
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
# 6. CONEXÃO COM GOOGLE DRIVE
# =============================================
@st.cache_resource(show_spinner=False)
def get_drive_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    creds_info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build('drive', 'v3', credentials=creds)

def get_latest_h5_id(folder_id):
    service = get_drive_service()
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
    latest_id = None
    latest_ts = -1
    for f in files:
        match = re.search(r'(\d{8,})', f['name'])
        if match:
            ts = int(match.group(1))
            if ts > latest_ts:
                latest_ts = ts
                latest_id = f['id']
    if latest_id is None:
        latest_id = files[0]['id']
    return latest_id

@st.cache_data(ttl=600, show_spinner="📥 Baixando dados do Drive...")
def load_hdf_from_drive(file_id):
    from googleapiclient.http import MediaIoBaseDownload
    service = get_drive_service()
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
    return pd.read_hdf(tmp_path, key='s')

# =============================================
# 7. NORMALIZAÇÃO DE TIMESTAMPS  ← CORRIGIDO
# =============================================
def normalize_timestamps(df):
    """Converte pubMillis (UTC epoch ms) para horário local de Foz do Iguaçu (UTC-3)."""
    if df is None or df.empty:
        return df
    df = df.copy()
    if 'pubMillis' in df.columns:
        # Converte epoch ms → UTC → America/Sao_Paulo (UTC-3), remove tzinfo para compatibilidade
        df['timestamp'] = (
            pd.to_datetime(df['pubMillis'], unit='ms', utc=True)
            .dt.tz_convert('America/Sao_Paulo')
            .dt.tz_localize(None)
        )
    elif 'timestamp' not in df.columns:
        df['timestamp'] = now_foz().replace(tzinfo=None)

    df['date']        = df['timestamp'].dt.date
    df['hour']        = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.day_name()
    return df

# =============================================
# 8. EXTRAÇÃO DE COORDENADAS
# =============================================
def extract_coordinates(df):
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
# 9. NORMALIZAÇÃO DE VELOCIDADE
# =============================================
def normalize_speed(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    if 'speed' in df.columns:
        df['speed'] = pd.to_numeric(df['speed'], errors='coerce')
        return df
    for alt in ['speedKMH', 'speedkmh', 'speed_kmh', 'velocity']:
        if alt in df.columns:
            df['speed'] = pd.to_numeric(df[alt], errors='coerce') / 3.6
            return df
    df['speed'] = float('nan')
    return df

# =============================================
# 10. TRADUÇÕES WAZE → PT-BR
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
# 11. PIPELINE PRINCIPAL DE DADOS
# =============================================
@st.cache_data(ttl=600, show_spinner="🔄 Carregando dados do Google Drive...")
def load_all_data():
    alerts_id = get_latest_h5_id(FOLDER_ALERTS_ID)
    jams_id   = get_latest_h5_id(FOLDER_JAMS_ID)

    df_alerts = load_hdf_from_drive(alerts_id) if alerts_id else pd.DataFrame()
    df_jams   = load_hdf_from_drive(jams_id)   if jams_id   else pd.DataFrame()

    if not df_alerts.empty:
        df_alerts = normalize_timestamps(df_alerts)
        df_alerts = extract_coordinates(df_alerts)
        df_alerts = translate_dataframe(df_alerts)
        if 'street' not in df_alerts.columns:
            df_alerts['street'] = 'N/A'

    if not df_jams.empty:
        df_jams = normalize_timestamps(df_jams)
        df_jams = extract_coordinates(df_jams)
        df_jams = normalize_speed(df_jams)
        if 'street' not in df_jams.columns:
            df_jams['street'] = 'Via'

    return df_alerts, df_jams

# =============================================
# 12. FUNÇÕES DE MAPA  ← BOUNDING BOX AMPLIADA
# =============================================
def create_folium_map_with_compass(lat, lon, zoom_level=13):
    m = folium.Map(
        location=[lat, lon],
        zoom_start=zoom_level,
        tiles="OpenStreetMap",
        max_bounds=True
    )
    plugins.MousePosition(
        position='topright',
        separator=' | ',
        prefix='Lat/Lon: ',
        num_digits=5
    ).add_to(m)
    plugins.MeasureControl(position='bottomright').add_to(m)
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

# Bounding box ampliada: ±0.15 grau em torno de Foz do Iguaçu
LAT_MIN, LAT_MAX = -25.70, -25.40
LON_MIN, LON_MAX = -54.75, -54.45

@st.cache_resource(ttl=600, show_spinner=False)
def generate_incidents_map(df_json):
    df = pd.read_json(io.StringIO(df_json))
    if df.empty:
        return None
    if 'lat' not in df.columns and 'y' in df.columns:
        df['lat'] = pd.to_numeric(df['y'], errors='coerce')
    if 'lon' not in df.columns and 'x' in df.columns:
        df['lon'] = pd.to_numeric(df['x'], errors='coerce')
    if 'lat' not in df.columns and 'location' in df.columns:
        import ast
        def _gy(x):
            try: return float((ast.literal_eval(x) if isinstance(x, str) else x).get('y'))
            except: return None
        def _gx(x):
            try: return float((ast.literal_eval(x) if isinstance(x, str) else x).get('x'))
            except: return None
        df['lat'] = df['location'].apply(_gy)
        df['lon'] = df['location'].apply(_gx)
    if 'lat' not in df.columns or 'lon' not in df.columns:
        return None
    df_map = df.dropna(subset=['lat', 'lon']).head(50)
    df_map = df_map[
        (df_map['lat'].between(LAT_MIN, LAT_MAX)) &
        (df_map['lon'].between(LON_MIN, LON_MAX))
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
    if 'lat' not in df.columns and 'y' in df.columns:
        df['lat'] = pd.to_numeric(df['y'], errors='coerce')
    if 'lon' not in df.columns and 'x' in df.columns:
        df['lon'] = pd.to_numeric(df['x'], errors='coerce')
    if 'lat' not in df.columns and 'location' in df.columns:
        import ast
        def _get_y(x):
            try: return float((ast.literal_eval(x) if isinstance(x, str) else x).get('y'))
            except: return None
        def _get_x(x):
            try: return float((ast.literal_eval(x) if isinstance(x, str) else x).get('x'))
            except: return None
        df['lat'] = df['location'].apply(_get_y)
        df['lon'] = df['location'].apply(_get_x)
    if 'speed' not in df.columns:
        for alt in ['speedKMH', 'speedkmh', 'speed_kmh', 'velocity']:
            if alt in df.columns:
                df['speed'] = pd.to_numeric(df[alt], errors='coerce') / 3.6
                break
        else:
            df['speed'] = float('nan')
    if any(c not in df.columns for c in ['lat', 'lon']):
        return None
    df_valid = df.dropna(subset=['lat', 'lon']).head(40)
    df_valid = df_valid[
        (df_valid['lat'].between(LAT_MIN, LAT_MAX)) &
        (df_valid['lon'].between(LON_MIN, LON_MAX))
    ]
    if df_valid.empty:
        return None
    m = create_folium_map_with_compass(df_valid['lat'].mean(), df_valid['lon'].mean())
    for _, row in df_valid.iterrows():
        try:
            speed_raw = row.get('speed', float('nan'))
            speed_kmh = float(speed_raw) * 3.6 if pd.notna(speed_raw) else 0.0
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
    if 'lat' not in df.columns and 'y' in df.columns:
        df['lat'] = pd.to_numeric(df['y'], errors='coerce')
    if 'lon' not in df.columns and 'x' in df.columns:
        df['lon'] = pd.to_numeric(df['x'], errors='coerce')
    if 'lat' not in df.columns or 'lon' not in df.columns:
        return None
    df_map = df.dropna(subset=['lat', 'lon'])
    if df_map.empty:
        return None
    m = create_folium_map_with_compass(df_map['lat'].mean(), df_map['lon'].mean())
    heat_data = [[row['lat'], row['lon']] for _, row in df_map.iterrows()]
    plugins.HeatMap(heat_data, radius=15, blur=10).add_to(m)
    return m

# =============================================
# 13. SIDEBAR
# =============================================
hora_foz_atual = now_foz()

st.sidebar.header("⚙️ Controles")
st.sidebar.markdown("### ⏰ Status da Sessão")
st.sidebar.markdown(f"🕐 **Hora atual (Foz):** `{hora_foz_atual.strftime('%d/%m/%Y %H:%M:%S')}`")
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
# 14. CARREGAMENTO DE DADOS
# =============================================
try:
    df_alerts_raw, df_jams_raw = load_all_data()
except Exception as e:
    st.error(f"❌ Erro ao conectar com o Google Drive: {e}")
    st.markdown("""
    **Verifique:**
    - As credenciais `gcp_service_account` estão configuradas em **Settings → Secrets**
    - A Service Account tem acesso às pastas do Drive
    - Os arquivos `.h5` existem nas pastas configuradas
    """)
    st.stop()

for df_ref in [df_alerts_raw, df_jams_raw]:
    if not df_ref.empty:
        if 'hour' not in df_ref.columns:
            df_ref['hour'] = df_ref['timestamp'].dt.hour
        if 'date' not in df_ref.columns:
            df_ref['date'] = df_ref['timestamp'].dt.date

# =============================================
# 15. FILTROS NA SIDEBAR  ← DATA DEFAULT CORRIGIDA
# =============================================
st.sidebar.subheader("🔍 Filtros")

# Data atual em Foz do Iguaçu (UTC-3) — NUNCA usa UTC
today_foz = hora_foz_atual.date()

all_dates = set()
if not df_alerts_raw.empty: all_dates.update(df_alerts_raw['date'].unique())
if not df_jams_raw.empty:   all_dates.update(df_jams_raw['date'].unique())

if all_dates:
    min_date = min(all_dates)
    max_date = max(all_dates)
    # Prefere a data de hoje (Foz); se não há dados hoje, usa o máximo disponível
    default_date = today_foz if today_foz in all_dates else max_date
else:
    min_date = max_date = default_date = today_foz

selected_date = st.sidebar.date_input(
    "📅 Data",
    value=default_date,
    min_value=min_date,
    max_value=max(max_date, today_foz)  # permite selecionar hoje mesmo sem dados ainda
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
# 16. APLICAÇÃO DOS FILTROS  ← FALLBACK SE SEM DADOS HOJE
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
    # Fallback: se filtro de data zerou os registros, mostra os mais recentes disponíveis
    if df_filtered.empty:
        st.sidebar.warning(f"⚠️ Sem dados em {selected_date}. Exibindo dados mais recentes.")
        df_filtered = df_alerts_raw[
            (df_alerts_raw['type'].isin(filtro_tipo)) &
            (df_alerts_raw['hour'].between(hora_range[0], hora_range[1]))
        ].copy()

df_jams_filtered = pd.DataFrame()
if not df_jams_raw.empty:
    df_jams_filtered = df_jams_raw[
        (df_jams_raw['date'] == selected_date) &
        (df_jams_raw['hour'].between(hora_range[0], hora_range[1]))
    ].copy()
    # Fallback para jams também
    if df_jams_filtered.empty:
        df_jams_filtered = df_jams_raw[
            df_jams_raw['hour'].between(hora_range[0], hora_range[1])
        ].copy()

# =============================================
# 17. CABEÇALHO
# =============================================
st.title(f"🚗 Monitoramento de Tráfego — Foz do Iguaçu | {selected_date.strftime('%d/%m/%Y')}")
st.success(
    f"✅ **Dados reais** carregados do Google Drive | "
    f"🕐 Hora local (Foz): **{hora_foz_atual.strftime('%H:%M:%S')}**",
    icon="🟢"
)
st.markdown("---")

# =============================================
# 18. RESUMO DOS FILTROS ATIVOS
# =============================================
col_f1, col_f2, col_f3, col_f4 = st.columns(4)
col_f1.metric("📅 Data",    selected_date.strftime("%d/%m/%Y"))
col_f2.metric("🚨 Alertas", f"{len(filtro_tipo)} tipos")
col_f3.metric("🛣️ Rua",     f"'{filtro_rua}'" if filtro_rua else "Todas")
col_f4.metric("⏰ Horário", f"{hora_range[0]:02d}:00–{hora_range[1]:02d}:59")
st.markdown("---")

# =============================================
# 19. KPIs PRINCIPAIS
# =============================================
st.subheader("📊 Resumo Estatístico")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

incidentes_dia   = len(df_filtered)
acidentes_graves = len(df_filtered[df_filtered['type'] == 'ACIDENTE']) if not df_filtered.empty else 0
v_media_kmh      = (df_jams_filtered['speed'].mean() * 3.6) if not df_jams_filtered.empty and 'speed' in df_jams_filtered.columns and df_jams_filtered['speed'].notna().any() else 0
status_via       = "🚫 Crítico" if incidentes_dia > 15 else ("⚠️ Moderado" if incidentes_dia > 5 else "✅ Normal")

kpi1.metric("Total Alertas",  incidentes_dia)
kpi2.metric("Acidentes",      acidentes_graves)
kpi3.metric("Vel. Média",     f"{v_media_kmh:.1f} km/h")
kpi4.metric("Status da Via",  status_via)
st.markdown("---")

# =============================================
# 20. INDICADORES VISUAIS DE GRAVIDADE
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
# 21. ABAS DE VISUALIZAÇÃO
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
        m_inc = generate_incidents_map(df_filtered.to_json(date_format='iso'))
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
        m_jam = generate_jams_map(df_jams_filtered.to_json(date_format='iso'))
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
        m_heat = generate_heatmap(df_filtered.to_json(date_format='iso'))
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
                labels={'hour': 'Hora (Foz UTC-3)', 'count': 'Qtd'},
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
        if 'lat' in df_display.columns and 'lon' in df_display.columns:
            df_display['Google Maps'] = df_display.apply(
                lambda x: f"https://www.google.com/maps?q={x.get('lat',0)},{x.get('lon',0)}", axis=1
            )
        cols_show = [c for c in ['timestamp','type','subtype','street','Google Maps'] if c in df_display.columns]
        st.dataframe(
            df_display[cols_show].sort_values('timestamp', ascending=False),
            column_config={
                "timestamp":   st.column_config.DatetimeColumn("Horário (Foz)", format="DD/MM HH:mm"),
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
# 22. RODAPÉ
# =============================================
st.markdown("---")
st.info("💡 Passe o mouse sobre os mapas para ver coordenadas em tempo real no canto superior direito.")
st.caption(
    f"Fonte: Google Drive | "
    f"Hora Foz: {hora_foz_atual.strftime('%H:%M')} (UTC-3) | "
    f"Atualizações manuais: {st.session_state.manual_refreshes} | "
    f"App online há {tempo_total // 60} min"
)
