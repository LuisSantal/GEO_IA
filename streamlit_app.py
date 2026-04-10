import streamlit as st
import pandas as pd
import plotly.express as px
import io
import re
import ast
import tempfile
from datetime import datetime, date
from zoneinfo import ZoneInfo
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
TZ_FOZ = ZoneInfo("America/Sao_Paulo")

def now_foz():
    return datetime.now(TZ_FOZ).replace(tzinfo=None)

# =============================================
# 3. ESTADO DA SESSÃO
# =============================================
if 'app_start_time' not in st.session_state:
    st.session_state.app_start_time = now_foz()
    st.session_state.manual_refreshes = 0

tempo_sessao       = (now_foz() - st.session_state.app_start_time).total_seconds()
tempo_prox_refresh = 600 - (tempo_sessao % 600)
minutos_restantes  = int(tempo_prox_refresh // 60)
segundos_restantes = int(tempo_prox_refresh % 60)
tempo_total        = int(tempo_sessao)

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
    else:                 return '#FF0000'

def get_danger_color(incident_type):
    if pd.isna(incident_type) or str(incident_type).strip() == '':
        return '#0099FF'
    danger_colors = {
        'ACIDENTE':         '#FF0000',
        'VIA FECHADA':      '#FF4400',
        'CONGESTIONAMENTO': '#FFAA00',
        'PERIGO':           '#FF6600',
        'ALERTA':           '#FFDD00',
        'OBRAS':            '#AAAAAA',
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
    query   = f"'{folder_id}' in parents and name contains '.h5' and trashed=false"
    results = service.files().list(
        q=query,
        fields="files(id, name, modifiedTime)",
        orderBy="modifiedTime desc",
        pageSize=20
    ).execute()
    files = results.get('files', [])
    if not files:
        return None
    latest_id, latest_ts = None, -1
    for f in files:
        match = re.search(r'(\d{8,})', f['name'])
        if match:
            ts = int(match.group(1))
            if ts > latest_ts:
                latest_ts = ts
                latest_id = f['id']
    return latest_id if latest_id else files[0]['id']

@st.cache_data(ttl=600, show_spinner="📥 Baixando dados do Drive...")
def load_hdf_from_drive(file_id):
    from googleapiclient.http import MediaIoBaseDownload
    service    = get_drive_service()
    request    = service.files().get_media(fileId=file_id)
    fh         = io.BytesIO()
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
# 7. NORMALIZAÇÃO DE TIMESTAMPS
# =============================================
def normalize_timestamps(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    if 'pubMillis' in df.columns:
        df['timestamp'] = (
            pd.to_datetime(df['pubMillis'], unit='ms', utc=True)
            .dt.tz_convert('America/Sao_Paulo')
            .dt.tz_localize(None)
        )
    elif 'timestamp' not in df.columns:
        df['timestamp'] = datetime.now()
    df['date']        = df['timestamp'].dt.date
    df['hour']        = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.day_name()
    return df

# =============================================
# 8. EXTRAÇÃO DE COORDENADAS — ALERTAS
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
                df['location'] = df['location'].apply(
                    lambda x: ast.literal_eval(x) if isinstance(x, str) else x
                )
            df['lat'] = df['location'].apply(
                lambda x: float(x.get('y', 0)) if isinstance(x, dict) else None
            )
            df['lon'] = df['location'].apply(
                lambda x: float(x.get('x', 0)) if isinstance(x, dict) else None
            )
        except Exception:
            pass
    if 'lat' not in df.columns and 'y' in df.columns:
        df['lat'] = pd.to_numeric(df['y'], errors='coerce')
    if 'lon' not in df.columns and 'x' in df.columns:
        df['lon'] = pd.to_numeric(df['x'], errors='coerce')
    return df

# =============================================
# 8b. EXTRAÇÃO DE COORDENADAS — JAMS  ← NOVO
# =============================================
def extract_jams_coordinates(df):
    """
    Jams do Waze armazenam o traçado na coluna 'line' (lista de pontos {x, y}).
    Esta função extrai o ponto médio do traçado como representante do jam.
    Fallback: 'location', colunas soltas x/y.
    """
    if df is None or df.empty:
        return df
    df = df.copy()

    # Se já tem lat/lon válidos, apenas normaliza o tipo
    if 'lat' in df.columns and 'lon' in df.columns:
        df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
        df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
        if df['lat'].notna().any():
            return df

    # ── PRIORIDADE 1: coluna 'line' (traçado do jam) ──────────────────────────
    if 'line' in df.columns:
        def _midpoint(val):
            try:
                pts = val if isinstance(val, list) else ast.literal_eval(str(val))
                if not pts:
                    return None, None
                mid = pts[len(pts) // 2]
                return float(mid.get('y')), float(mid.get('x'))
            except Exception:
                return None, None

        coords    = df['line'].apply(lambda x: pd.Series(_midpoint(x), index=['lat', 'lon']))
        df['lat'] = coords['lat']
        df['lon'] = coords['lon']

        if df['lat'].notna().any():
            return df

    # ── PRIORIDADE 2: coluna 'location' ──────────────────────────────────────
    if 'location' in df.columns:
        try:
            sample = df['location'].dropna().iloc[0] if not df['location'].dropna().empty else None
            if isinstance(sample, str):
                df['location'] = df['location'].apply(
                    lambda x: ast.literal_eval(x) if isinstance(x, str) else x
                )
            df['lat'] = df['location'].apply(
                lambda x: float(x.get('y', 0)) if isinstance(x, dict) else None
            )
            df['lon'] = df['location'].apply(
                lambda x: float(x.get('x', 0)) if isinstance(x, dict) else None
            )
        except Exception:
            pass

    # ── PRIORIDADE 3: colunas soltas x / y ───────────────────────────────────
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
    'ROAD_CLOSED':              'VIA FECHADA',
    'ROAD_CLOSED_CONSTRUCTION': 'VIA FECHADA',
    'ROAD_CLOSED_EVENT':        'VIA FECHADA',
    'HAZARD':                   'PERIGO',
    'ACCIDENT':                 'ACIDENTE',
    'JAM':                      'CONGESTIONAMENTO',
    'WEATHERHAZARD':            'PERIGO CLIMÁTICO',
}
SUBTYPE_MAP = {
    'ROAD_CLOSED_CONSTRUCTION':          'OBRAS',
    'ROAD_CLOSED_EVENT':                 'EVENTO',
    'HAZARD_ON_ROAD':                    'PERIGO NA VIA',
    'HAZARD_ON_SHOULDER':                'PERIGO NO ACOSTAMENTO',
    'HAZARD_WEATHER':                    'CONDIÇÕES CLIMÁTICAS',
    'HAZARD_ON_ROAD_POT_HOLE':           'BURACO NA VIA',
    'HAZARD_ON_ROAD_ROAD_KILL':          'ANIMAL NA VIA',
    'HAZARD_ON_ROAD_CAR_STOPPED':        'VEÍCULO PARADO',
    'HAZARD_ON_ROAD_CONSTRUCTION':       'OBRAS NA VIA',
    'HAZARD_ON_ROAD_OBJECT':             'OBJETO NA VIA',
    'HAZARD_ON_ROAD_TRAFFIC_LIGHT_FAULT':'SEMÁFORO QUEBRADO',
    'HAZARD_WEATHER_FOG':                'NEBLINA',
    'HAZARD_WEATHER_HAIL':               'GRANIZO',
    'HAZARD_WEATHER_HEAVY_RAIN':         'CHUVA FORTE',
    'HAZARD_WEATHER_FLOOD':              'INUNDAÇÃO',
    'ACCIDENT_MAJOR':                    'ACIDENTE GRAVE',
    'ACCIDENT_MINOR':                    'ACIDENTE LEVE',
    'JAM_HEAVY_TRAFFIC':                 'TRÂNSITO PESADO',
    'JAM_MODERATE_TRAFFIC':              'TRÂNSITO MODERADO',
    'JAM_STAND_STILL_TRAFFIC':           'TRÂNSITO PARADO',
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
# 11. PIPELINE PRINCIPAL DE DADOS  ← CORRIGIDO
# =============================================
@st.cache_data(ttl=600, show_spinner="🔄 Carregando dados do Google Drive...")
def load_all_data():
    alerts_id = get_latest_h5_id(FOLDER_ALERTS_ID)
    jams_id   = get_latest_h5_id(FOLDER_JAMS_ID)

    df_alerts = load_hdf_from_drive(alerts_id) if alerts_id else pd.DataFrame()
    df_jams   = load_hdf_from_drive(jams_id)   if jams_id   else pd.DataFrame()

    if not df_alerts.empty:
        df_alerts = normalize_timestamps(df_alerts)
        df_alerts = extract_coordinates(df_alerts)       # alertas usam 'location'
        df_alerts = translate_dataframe(df_alerts)
        if 'street' not in df_alerts.columns:
            df_alerts['street'] = 'N/A'

    if not df_jams.empty:
        df_jams = normalize_timestamps(df_jams)
        df_jams = extract_jams_coordinates(df_jams)      # ← CORRIGIDO: usa 'line'
        df_jams = normalize_speed(df_jams)
        if 'street' not in df_jams.columns:
            df_jams['street'] = 'Via'

    return df_alerts, df_jams

# =============================================
# 12. BOUNDING BOX DE FOZ DO IGUAÇU
# =============================================
LAT_MIN, LAT_MAX = -25.70, -25.40
LON_MIN, LON_MAX = -54.75, -54.45

# =============================================
# 13. FUNÇÕES DE MAPA
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

    # ── Rosa dos ventos SVG — injetada direto no HTML do mapa ─────────────────
    compass_html = """
    <div style="
        position:absolute;
        bottom:40px;
        left:10px;
        z-index:9999;
        pointer-events:none;
    ">
      <svg width="54" height="54" viewBox="0 0 54 54"
           xmlns="http://www.w3.org/2000/svg"
           style="filter:drop-shadow(0 2px 6px rgba(0,0,0,0.5));">

        <!-- Círculo de fundo -->
        <circle cx="27" cy="27" r="26" fill="white" stroke="#555" stroke-width="2"/>

        <!-- Seta Norte (vermelha) — aponta para cima -->
        <polygon points="27,4 22,27 27,22 32,27" fill="#d32f2f"/>

        <!-- Seta Sul (cinza) — aponta para baixo -->
        <polygon points="27,50 22,27 27,32 32,27" fill="#999"/>

        <!-- Seta Leste (cinza claro) -->
        <polygon points="50,27 27,22 32,27 27,32" fill="#ccc"/>

        <!-- Seta Oeste (cinza claro) -->
        <polygon points="4,27 27,22 22,27 27,32" fill="#ccc"/>

        <!-- Círculo central -->
        <circle cx="27" cy="27" r="4" fill="#555"/>

        <!-- Letra N -->
        <text x="27" y="16" text-anchor="middle"
              font-size="9" font-weight="bold"
              font-family="Arial" fill="#d32f2f">N</text>

        <!-- Letra S -->
        <text x="27" y="51" text-anchor="middle"
              font-size="9" font-weight="bold"
              font-family="Arial" fill="#777">S</text>

        <!-- Letra L (Leste) -->
        <text x="49" y="30" text-anchor="middle"
              font-size="8" font-family="Arial" fill="#888">L</text>

        <!-- Letra O (Oeste) -->
        <text x="6" y="30" text-anchor="middle"
              font-size="8" font-family="Arial" fill="#888">O</text>
      </svg>
    </div>
    """

    m.get_root().html.add_child(folium.Element(compass_html))

    folium.LayerControl(position='topright', collapsed=True).add_to(m)
    return m





def generate_incidents_map(df_json):
    df = pd.read_json(io.StringIO(df_json))
    if df.empty:
        return None

    # Recupera coordenadas caso venham zeradas do JSON
    if ('lat' not in df.columns or df['lat'].isna().all()) and 'location' in df.columns:
        def _gy(x):
            try: return float((ast.literal_eval(x) if isinstance(x, str) else x).get('y'))
            except: return None
        def _gx(x):
            try: return float((ast.literal_eval(x) if isinstance(x, str) else x).get('x'))
            except: return None
        df['lat'] = df['location'].apply(_gy)
        df['lon'] = df['location'].apply(_gx)
    if 'lat' not in df.columns and 'y' in df.columns:
        df['lat'] = pd.to_numeric(df['y'], errors='coerce')
    if 'lon' not in df.columns and 'x' in df.columns:
        df['lon'] = pd.to_numeric(df['x'], errors='coerce')
    if 'lat' not in df.columns or 'lon' not in df.columns:
        return None

    # ── CORRIGIDO: filtra bbox ANTES de aplicar head() ────────────────────────
    df_map = df.dropna(subset=['lat', 'lon'])
    df_map = df_map[
        df_map['lat'].between(LAT_MIN, LAT_MAX) &
        df_map['lon'].between(LON_MIN, LON_MAX)
    ].head(50)

    if df_map.empty:
        return None

    m = create_folium_map_with_compass(df_map['lat'].mean(), df_map['lon'].mean())
    for _, row in df_map.iterrows():
        try:
            tipo    = str(row.get('type', '?'))
            subtipo = str(row.get('subtype', ''))
            rua     = str(row.get('street', 'N/A'))
            color   = get_danger_color(tipo)
            ts_raw  = row.get('timestamp')
            ts      = pd.to_datetime(ts_raw).strftime('%H:%M') if pd.notna(ts_raw) else '--'
            lat_val = float(row['lat'])
            lon_val = float(row['lon'])

            popup_html = (
                f"<div style='min-width:200px;font-family:Arial;'>"
                f"<b style='color:{color};font-size:16px;'>🚨 {tipo}</b><br>"
                f"<b>{subtipo}</b><br>"
                f"🛣️ <i>{rua}</i><br>"
                f"🕒 {ts}<br>"
                f"📍 {lat_val:.4f}, {lon_val:.4f}"
                f"</div>"
            )
            folium.CircleMarker(
                location=[lat_val, lon_val],
                radius=9,
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=tipo + ": " + rua,
                color=color, fill=True, fillColor=color,
                fillOpacity=0.8, weight=2
            ).add_to(m)
        except Exception:
            continue
    return m



def generate_jams_map(df_json):
    df = pd.read_json(io.StringIO(df_json))
    if df.empty:
        return None

    # ── CORRIGIDO: extrai coords da coluna 'line' se lat/lon ausentes ─────────
    if ('lat' not in df.columns or df['lat'].isna().all()) and 'line' in df.columns:
        def _midpoint(val):
            try:
                pts = val if isinstance(val, list) else ast.literal_eval(str(val))
                if not pts:
                    return None, None
                mid = pts[len(pts) // 2]
                return float(mid.get('y')), float(mid.get('x'))
            except Exception:
                return None, None
        coords    = df['line'].apply(lambda x: pd.Series(_midpoint(x), index=['lat', 'lon']))
        df['lat'] = coords['lat']
        df['lon'] = coords['lon']

    # Fallbacks adicionais
    if ('lat' not in df.columns or df['lat'].isna().all()) and 'location' in df.columns:
        def _get_y(x):
            try: return float((ast.literal_eval(x) if isinstance(x, str) else x).get('y'))
            except: return None
        def _get_x(x):
            try: return float((ast.literal_eval(x) if isinstance(x, str) else x).get('x'))
            except: return None
        df['lat'] = df['location'].apply(_get_y)
        df['lon'] = df['location'].apply(_get_x)
    if 'lat' not in df.columns and 'y' in df.columns:
        df['lat'] = pd.to_numeric(df['y'], errors='coerce')
    if 'lon' not in df.columns and 'x' in df.columns:
        df['lon'] = pd.to_numeric(df['x'], errors='coerce')

    # Normaliza velocidade se ausente
    if 'speed' not in df.columns:
        for alt in ['speedKMH', 'speedkmh', 'speed_kmh', 'velocity']:
            if alt in df.columns:
                df['speed'] = pd.to_numeric(df[alt], errors='coerce') / 3.6
                break
        else:
            df['speed'] = float('nan')

    if 'lat' not in df.columns or 'lon' not in df.columns:
        return None

    # ── CORRIGIDO: filtra bbox ANTES de aplicar head() ────────────────────────
    df_valid = df.dropna(subset=['lat', 'lon'])
    df_valid = df_valid[
        df_valid['lat'].between(LAT_MIN, LAT_MAX) &
        df_valid['lon'].between(LON_MIN, LON_MAX)
    ].head(40)

    if df_valid.empty:
        return None

    m = create_folium_map_with_compass(df_valid['lat'].mean(), df_valid['lon'].mean())
    for _, row in df_valid.iterrows():
        try:
            speed_raw = row.get('speed', float('nan'))
            speed_kmh = float(speed_raw) * 3.6 if pd.notna(speed_raw) else 0.0
            color     = get_congestion_color(speed_kmh)
            rua       = str(row.get('street', 'Via'))
            ts_raw    = row.get('timestamp')
            ts        = pd.to_datetime(ts_raw).strftime('%H:%M') if pd.notna(ts_raw) else '--'
            lat_val   = float(row['lat'])
            lon_val   = float(row['lon'])
            spd_str   = f"{speed_kmh:.0f} km/h"

            popup_html = (
                f"<div style='min-width:180px;'>"
                f"<b style='color:{color}'>🚗 {spd_str}</b><br>"
                f"🛣️ <i>{rua}</i><br>"
                f"🕒 {ts}"
                f"</div>"
            )
            folium.CircleMarker(
                location=[lat_val, lon_val],
                radius=7,
                popup=folium.Popup(popup_html, max_width=220),
                tooltip=spd_str + " — " + rua,
                color=color, fill=True, fillColor=color, fillOpacity=0.7
            ).add_to(m)
        except Exception:
            continue
    return m



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
# 14. SIDEBAR — STATUS E CONTROLES
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
# 15. CARREGAMENTO DE DADOS
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
# 16. FILTROS NA SIDEBAR — CASCATA INTELIGENTE
# =============================================
st.sidebar.subheader("🔍 Filtros")
today_foz = hora_foz_atual.date()
# ── 1. DATA (âncora de todos os filtros) ──────────────────────────────────────
all_dates = set()
if not df_alerts_raw.empty:
    all_dates.update(df_alerts_raw["date"].unique())
if not df_jams_raw.empty:
    all_dates.update(df_jams_raw["date"].unique())

if all_dates:
    min_date  = min(all_dates)
    max_date  = max(all_dates)
    default_date = today_foz if today_foz in all_dates else max_date
else:
    min_date = max_date = default_date = today_foz

selected_date = st.sidebar.date_input(
    "📅 Data",
    value=default_date,
    min_value=min_date,
    max_value=max(max_date, today_foz),
)

# ── 2. HORÁRIO ────────────────────────────────────────────────────────────────
hora_range = st.sidebar.slider("🕐 Horário", 0, 23, (0, 23))

# ── 3. TIPOS DE OCORRÊNCIA (atrelado à data) ──────────────────────────────────
tipos_na_data = (
    sorted(
        df_alerts_raw.loc[df_alerts_raw["date"] == selected_date, "type"]
        .dropna().unique().tolist()
    )
    if not df_alerts_raw.empty else []
)
if not tipos_na_data:   # fallback: todos os tipos disponíveis
    tipos_na_data = sorted(df_alerts_raw["type"].dropna().unique().tolist()) if not df_alerts_raw.empty else []

filtro_tipo = st.sidebar.multiselect(
    "⚠️ Tipo de Ocorrência",
    options=tipos_na_data,
    default=tipos_na_data,
)

# ── 4. RUA / VIA (selectbox com ruas reais da data) ───────────────────────────
ruas_na_data = []
if not df_alerts_raw.empty and "street" in df_alerts_raw.columns:
    ruas_na_data = sorted(
        df_alerts_raw.loc[
            (df_alerts_raw["date"] == selected_date) &
            (df_alerts_raw["street"].notna()) &
            (~df_alerts_raw["street"].isin(["NA", "nan", ""]))
        , "street"].unique().tolist()
    )

filtro_rua = st.sidebar.selectbox(
    "🛣️ Rua / Via",
    options=["(Todas)"] + ruas_na_data,
    index=0,
)
filtro_rua = "" if filtro_rua == "(Todas)" else filtro_rua

# ── 5. FAIXA DE VELOCIDADE — congestionamentos (atrelado à data) ──────────────
vel_min_data, vel_max_data = 0.0, 120.0
if not df_jams_raw.empty and "speed" in df_jams_raw.columns:
    speeds_na_data = (
        df_jams_raw.loc[df_jams_raw["date"] == selected_date, "speed"]
        .dropna()
    )
    if not speeds_na_data.empty:
        vel_min_data = float((speeds_na_data * 3.6).min())
        vel_max_data = float((speeds_na_data * 3.6).max())

vel_range = st.sidebar.slider(
    "🚗 Velocidade (km/h)",
    min_value=0.0,
    max_value=max(120.0, vel_max_data),
    value=(vel_min_data, min(120.0, vel_max_data)),
    step=5.0,
)

# ── 6. PAINEL DE CONGESTIONAMENTO (atrelado à data) ───────────────────────────
if not df_jams_raw.empty and "speed" in df_jams_raw.columns:
    jams_data = df_jams_raw[df_jams_raw["date"] == selected_date]
    if not jams_data.empty and jams_data["speed"].notna().any():
        media_vel  = jams_data["speed"].mean() * 3.6
        total_jams = len(jams_data)
        status_label = (
            "🔴 Crítico"  if media_vel < 20 else
            "🟠 Lento"    if media_vel < 40 else
            "🟡 Moderado" if media_vel < 60 else
            "🟢 Fluindo"
        )
        st.sidebar.markdown("---")
        st.sidebar.markdown("**📊 Congestionamentos em** " + selected_date.strftime("%d/%m"))
        st.sidebar.metric("Vel. Média", f"{media_vel:.1f} km/h", delta=status_label)
        st.sidebar.metric("Total de Jams", total_jams)
    else:
        st.sidebar.info(f"Sem dados de congestionamento em {selected_date.strftime('%d/%m')}.")

# =============================================
# 17. APLICAÇÃO DOS FILTROS
# =============================================
df_filtered = pd.DataFrame()
if not df_alerts_raw.empty:

    df_filtered = df_alerts_raw[
        (df_alerts_raw['date'] == selected_date) &
        (df_alerts_raw['type'].isin(filtro_tipo) if filtro_tipo else True) &
        (df_alerts_raw['hour'].between(hora_range[0], hora_range[1]))
    ].copy()


    # Aplica rua (seleção exata, não busca livre)
    if filtro_rua and 'street' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['street'] == filtro_rua]

    # Fallback: se filtros zeraram os resultados
    if df_filtered.empty:
        st.sidebar.warning("⚠️ Sem dados para essa combinação. Exibindo dados da data sem filtro de tipo/subtipo/rua.")
        df_filtered = df_alerts_raw[
            (df_alerts_raw['date'] == selected_date) &
            (df_alerts_raw['hour'].between(hora_range[0], hora_range[1]))
        ].copy()
        # Segundo fallback: sem data também
        if df_filtered.empty:
            df_filtered = df_alerts_raw[
                df_alerts_raw['hour'].between(hora_range[0], hora_range[1])
            ].copy()

df_jams_filtered = pd.DataFrame()
if not df_jams_raw.empty:
    df_jams_filtered = df_jams_raw[
        (df_jams_raw['date'] == selected_date) &
        (df_jams_raw['hour'].between(hora_range[0], hora_range[1])) &
        (df_jams_raw["speed"].fillna(0) * 3.6).between(vel_range[0], vel_range[1])
    ].copy()
    if df_jams_filtered.empty:
        df_jams_filtered = df_jams_raw[
            df_jams_raw['hour'].between(hora_range[0], hora_range[1])
        ].copy()

# =============================================
# 18. CABEÇALHO
# =============================================
st.title(f"🚗 Monitoramento de Tráfego — Foz do Iguaçu | {selected_date.strftime('%d/%m/%Y')}")
st.success(
    f"✅ **Dados reais** carregados do Google Drive | "
    f"🕐 Hora local (Foz): **{hora_foz_atual.strftime('%H:%M:%S')}**",
    icon="🟢"
)
st.markdown("---")

# =============================================
# 19. RESUMO DOS FILTROS ATIVOS
# =============================================
col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)

# Resumo do tipo selecionado
if filtro_tipo and len(filtro_tipo) < len(tipos_na_data):
    label_tipo = ", ".join(filtro_tipo) if len(filtro_tipo) <= 2 else f"{len(filtro_tipo)} tipos"
else:
    label_tipo = "Todos"

# Resumo do subtipo selecionado
if filtro_tipo and len(filtro_tipo) < len(tipos_na_data):
    label_tipo = ", ".join(filtro_tipo) if len(filtro_tipo) <= 2 else f"{len(filtro_tipo)} tipos"
else:
    label_tipo = "Todos"

col_f1, col_f2, col_f3, col_f4 = st.columns(4)

col_f1.metric("📅 Data",     selected_date.strftime("%d/%m/%Y"))
col_f2.metric("🚨 Tipo",     label_tipo)
col_f3.metric("🛣️ Rua",      filtro_rua if filtro_rua else "Todas")
col_f4.metric("⏰ Horário",  f"{hora_range[0]:02d}h – {hora_range[1]:02d}h")

# Barra de contexto compacta com total de registros exibidos
st.caption(
    f"🔍 Filtros ativos → "
    f"**{len(df_filtered)} incidente(s)** exibidos "
    f"{'de ' + selected_date.strftime('%d/%m/%Y') if not df_filtered.empty else '(fallback: dados mais recentes)'} "
    f"| Congestionamentos: **{len(df_jams_filtered)}**"
)
st.markdown("---")

# =============================================
# 20. KPIs PRINCIPAIS
# =============================================
st.subheader("📊 Resumo Estatístico")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

incidentes_dia   = len(df_filtered)
acidentes_graves = len(df_filtered[df_filtered['type'] == 'ACIDENTE']) if not df_filtered.empty else 0
v_media_kmh      = (
    df_jams_filtered['speed'].mean() * 3.6
    if not df_jams_filtered.empty
    and 'speed' in df_jams_filtered.columns
    and df_jams_filtered['speed'].notna().any()
    else 0
)
status_via = "🚫 Crítico" if incidentes_dia > 15 else ("⚠️ Moderado" if incidentes_dia > 5 else "✅ Normal")

kpi1.metric("Total Alertas", incidentes_dia)
kpi2.metric("Acidentes",     acidentes_graves)
kpi3.metric("Vel. Média",    f"{v_media_kmh:.1f} km/h")
kpi4.metric("Status da Via", status_via)
st.markdown("---")

# =============================================
# 21. INDICADORES DE GRAVIDADE
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
# 22. ABAS DE VISUALIZAÇÃO
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
            st_folium(m_inc, width="100%", height=500, key=f"mapa_inc_{len(df_filtered)}")
        else:
            st.info("⚠️ Nenhum incidente dentro da área de Foz do Iguaçu.")
    else:
        st.info("Nenhum incidente com os filtros aplicados.")

# --- ABA 2: Congestionamentos ---
with tab_jams:
    st.caption("📏 Escala métrica | 🟢 Livre → 🔴 Parado")
    # Painel de diagnóstico — remova após confirmar que os mapas aparecem
    with st.expander("🔎 Diagnóstico de dados (remover após validação)", expanded=False):
        st.write("Total de jams carregados:", len(df_jams_raw))
        st.write("Total após filtro:", len(df_jams_filtered))
        if not df_jams_filtered.empty:
            st.write("Colunas disponíveis:", df_jams_filtered.columns.tolist())
            st.write("Tem coluna 'line'?", 'line' in df_jams_filtered.columns)
            st.write("Tem coluna 'lat'?",  'lat'  in df_jams_filtered.columns)
            if 'lat' in df_jams_filtered.columns:
                n_nan = int(df_jams_filtered['lat'].isna().sum())
                st.write(f"NaN em lat: {n_nan} / {len(df_jams_filtered)}")
                st.write("Amostra lat/lon:")
                st.dataframe(df_jams_filtered[['lat','lon']].dropna().head(5))

    if not df_jams_filtered.empty:
        m_jam = generate_jams_map(df_jams_filtered.to_json(date_format='iso'))
        if m_jam:
            st_folium(m_jam, width="100%", height=500, key=f"mapa_jam_{len(df_jams_filtered)}")
            st.markdown("**Legenda:** 🟢 >80 km/h | 🟡 40–80 km/h | 🟠 20–40 km/h | 🔴 <20 km/h")
        else:
            st.warning("⚠️ Nenhum congestionamento na área filtrada.")
            cols_diag = [c for c in ['lat','lon','line','speed','street'] if c in df_jams_filtered.columns]
            if cols_diag:
                st.caption("Amostra dos dados de jams:")
                st.dataframe(df_jams_filtered[cols_diag].head(5), use_container_width=True)
    else:
        st.info("Nenhum congestionamento para exibir.")

# --- ABA 3: Mapa de Calor ---
with tab_calor:
    st.subheader("🔥 Zonas de Concentração de Incidentes")

    if not df_filtered.empty:
        df_heat = df_filtered.copy()

        # Garante lat/lon limpos e dentro de Foz
        df_heat = df_heat.dropna(subset=['lat', 'lon'])
        df_heat = df_heat[
            df_heat['lat'].between(LAT_MIN, LAT_MAX) &
            df_heat['lon'].between(LON_MIN, LON_MAX)
        ]

        if not df_heat.empty:
            import folium
            from folium import plugins

            # ── Mapa base ────────────────────────────────────────────────────
            m_heat = folium.Map(
                location=[df_heat['lat'].mean(), df_heat['lon'].mean()],
                zoom_start=13,
                tiles="OpenStreetMap"
            )

            # ── Camada de calor ───────────────────────────────────────────────
            heat_data = [[row['lat'], row['lon']] for _, row in df_heat.iterrows()]
            plugins.HeatMap(
                heat_data,
                radius=20,
                blur=15,
                min_opacity=0.35,
                gradient={0.2: '#ffffb2', 0.4: '#fecc5c', 0.6: '#fd8d3c',
                          0.8: '#f03b20', 1.0: '#bd0026'}
            ).add_to(m_heat)

            # ── Ícones por tipo de incidente ──────────────────────────────────
            ICON_MAP = {
                'ACIDENTE':           ('car-crash',  'red',    '💥'),
                'VIA FECHADA':        ('ban',        'darkred','🚫'),
                'PERIGO':             ('warning',    'orange', '⚠️'),
                'PERIGO CLIMÁTICO':   ('cloud-rain', 'blue',   '🌧️'),
                'CONGESTIONAMENTO':   ('traffic-light','gray', '🚦'),
            }

            # Grupos separados por tipo (para o LayerControl)
            grupos = {}
            for tipo in df_heat['type'].dropna().unique():
                grupos[tipo] = folium.FeatureGroup(name=f"{ICON_MAP.get(tipo, ('','',' '))[2]} {tipo}", show=True)

            for _, row in df_heat.iterrows():
                try:
                    tipo    = str(row.get('type',    'ALERTA'))
                    subtipo = str(row.get('subtype', ''))
                    rua     = str(row.get('street',  'N/A'))
                    conf    = row.get('confidence',  'N/A')
                    rating  = row.get('reportRating','N/A')
                    ts_raw  = row.get('timestamp')
                    ts      = pd.to_datetime(ts_raw).strftime('%d/%m %H:%M') if pd.notna(ts_raw) else '--'
                    lat_val = float(row['lat'])
                    lon_val = float(row['lon'])

                    icon_name, icon_color, emoji = ICON_MAP.get(tipo, ('info-sign', 'cadetblue', 'ℹ️'))
                    danger_cor = get_danger_color(tipo)

                    # ── Popup rico ────────────────────────────────────────────
                    popup_html = f"""
                    <div style="min-width:220px;font-family:Arial,sans-serif;font-size:13px;">
                        <div style="background:{danger_cor};color:white;padding:6px 10px;
                                    border-radius:6px 6px 0 0;font-size:15px;font-weight:bold;">
                            {emoji} {tipo}
                        </div>
                        <div style="padding:8px 10px;border:1px solid #ddd;border-top:none;border-radius:0 0 6px 6px;">
                            <b>Subtipo:</b> {subtipo if subtipo and subtipo != 'nan' else '—'}<br>
                            <b>🛣️ Rua:</b> {rua}<br>
                            <b>🕒 Horário:</b> {ts}<br>
                            <b>⭐ Rating:</b> {rating}<br>
                            <b>🔒 Confiança:</b> {conf}<br>
                            <b>📍 Coords:</b> {lat_val:.5f}, {lon_val:.5f}<br>
                            <a href="https://www.google.com/maps?q={lat_val},{lon_val}"
                               target="_blank"
                               style="color:#1a73e8;font-weight:bold;">
                               🗺️ Abrir no Google Maps
                            </a>
                        </div>
                    </div>"""

                    # ── Tooltip sempre visível (rótulo no mapa) ───────────────
                    tooltip_txt = f"{emoji} {tipo}"
                    if rua and rua != 'N/A' and rua != 'nan':
                        tooltip_txt += f" — {rua[:30]}"
                    if ts != '--':
                        tooltip_txt += f" ({ts[-5:]})"   # só HH:MM

                    marker = folium.Marker(
                        location=[lat_val, lon_val],
                        popup=folium.Popup(popup_html, max_width=270),
                        tooltip=folium.Tooltip(
                            tooltip_txt,
                            permanent=False,   # True = sempre visível (pode poluir)
                            sticky=True
                        ),
                        icon=folium.Icon(
                            color=icon_color,
                            icon=icon_name,
                            prefix='fa'
                        )
                    )

                    if tipo in grupos:
                        marker.add_to(grupos[tipo])
                    else:
                        marker.add_to(m_heat)

                except Exception:
                    continue

            # Adiciona os grupos ao mapa
            for g in grupos.values():
                g.add_to(m_heat)

            # ── Rótulos permanentes nos TOP 5 pontos mais críticos ────────────
            # Prioridade: ACIDENTE > VIA FECHADA > PERIGO
            prioridade = {'ACIDENTE': 1, 'VIA FECHADA': 2, 'PERIGO': 3,
                          'PERIGO CLIMÁTICO': 4, 'CONGESTIONAMENTO': 5}
            df_top = df_heat.copy()
            df_top['_prio'] = df_top['type'].map(prioridade).fillna(9)
            df_top = df_top.sort_values('_prio').head(5)

            for _, row in df_top.iterrows():
                try:
                    tipo    = str(row.get('type', '?'))
                    rua     = str(row.get('street', ''))
                    emoji   = ICON_MAP.get(tipo, ('','','ℹ️'))[2]
                    cor     = get_danger_color(tipo)
                    label   = f"{emoji} {tipo}"
                    if rua and rua not in ('N/A', 'nan', ''):
                        label += f"\n{rua[:25]}"

                    folium.Marker(
                        location=[float(row['lat']), float(row['lon'])],
                        icon=folium.DivIcon(
                            html=f"""
                            <div style="
                                background:{cor};color:white;
                                padding:3px 7px;border-radius:5px;
                                font-size:11px;font-weight:bold;
                                white-space:nowrap;
                                box-shadow:0 2px 6px rgba(0,0,0,0.4);
                                border:1px solid rgba(255,255,255,0.4);
                                pointer-events:none;">
                                {label.replace(chr(10),'<br>')}
                            </div>""",
                            icon_size=(160, 36),
                            icon_anchor=(80, 36)
                        )
                    ).add_to(m_heat)
                except Exception:
                    continue

            # ── Controles do mapa ─────────────────────────────────────────────
            plugins.MousePosition(
                position='topright', separator=' | ',
                prefix='Lat/Lon: ', num_digits=5
            ).add_to(m_heat)
            plugins.MeasureControl(position='bottomright').add_to(m_heat)
            folium.LayerControl(position='topleft', collapsed=False).add_to(m_heat)

            # ── Renderiza ─────────────────────────────────────────────────────
            st_folium(
                m_heat,
                width="100%",
                height=560,
                key=f"mapa_calor_{len(df_heat)}"
            )

            # ── Legenda abaixo do mapa ────────────────────────────────────────
            st.markdown("""
            **Legenda do Gradiente de Calor:**
            🟡 Baixa concentração → 🟠 Média → 🔴 Alta concentração → 🟣 Crítica
            """)

            tipos_no_mapa = df_heat['type'].value_counts().reset_index()
            tipos_no_mapa.columns = ['Tipo', 'Qtd']
            tipos_no_mapa['Emoji'] = tipos_no_mapa['Tipo'].map(
                lambda t: ICON_MAP.get(t, ('','','ℹ️'))[2]
            )
            st.dataframe(
                tipos_no_mapa[['Emoji','Tipo','Qtd']],
                hide_index=True,
                use_container_width=True
            )

        else:
            st.info("⚠️ Nenhum ponto dentro da área de Foz do Iguaçu.")
    else:
        st.info("Sem dados suficientes para mapa de calor.")

# --- ABA 4: Gráficos ---
with tab_graficos:
    if not df_filtered.empty:

        st.markdown(
            f"📋 **{len(df_filtered)} registros** analisados para "
            f"**{selected_date.strftime('%d/%m/%Y')}** "
            f"no intervalo **{hora_range[0]:02d}:00 – {hora_range[1]:02d}:59**"
        )
        st.markdown("---")

        # =====================================================
        # GRÁFICO 1 + 2 — lado a lado
        # =====================================================
        col_g1, col_g2 = st.columns(2)

        # ── Incidentes por Hora ───────────────────────────
        with col_g1:
            st.subheader("📊 Incidentes por Hora do Dia")
            st.caption(
                "Distribuição dos alertas ao longo das 24 horas. "
                "Barras mais escuras indicam os horários de maior ocorrência — "
                "útil para identificar picos de risco no trânsito."
            )

            hora_counts = (
                df_filtered['hour']
                .value_counts()
                .reindex(range(24), fill_value=0)
                .reset_index()
            )
            hora_counts.columns = ['Hora', 'Quantidade']
            hora_pico = int(hora_counts.loc[hora_counts['Quantidade'].idxmax(), 'Hora'])

            fig_hora = px.bar(
                hora_counts,
                x='Hora', y='Quantidade',
                labels={'Hora': 'Hora do dia (UTC-3 / Foz)', 'Quantidade': 'Nº de Incidentes'},
                color='Quantidade',
                color_continuous_scale='Reds',
                text='Quantidade'
            )
            fig_hora.update_traces(
                textposition='outside',
                textfont_size=10,
                marker_line_width=0.5,
                marker_line_color='white'
            )
            fig_hora.add_vline(
                x=hora_pico,
                line_dash="dash",
                line_color="darkred",
                annotation_text=f"Pico: {hora_pico:02d}h",
                annotation_position="top right",
                annotation_font_color="darkred"
            )
            fig_hora.update_layout(
                xaxis=dict(tickmode='linear', tick0=0, dtick=1),
                coloraxis_showscale=False,
                margin=dict(t=40, b=40),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                height=360
            )
            st.plotly_chart(fig_hora, use_container_width=True)
            st.caption(f"🔺 Horário de pico: **{hora_pico:02d}:00 – {hora_pico:02d}:59**")

        # ── Proporção por Tipo ────────────────────────────
        with col_g2:
            st.subheader("🥧 Proporção por Tipo de Incidente")
            st.caption(
                "Cada fatia representa a participação percentual de um tipo de incidente "
                "no total filtrado. Clique em um tipo na legenda para ocultá-lo."
            )

            CORES_TIPO = {
                'ACIDENTE':         '#e74c3c',
                'VIA FECHADA':      '#c0392b',
                'PERIGO':           '#e67e22',
                'PERIGO CLIMÁTICO': '#3498db',
                'CONGESTIONAMENTO': '#f39c12',
                'ALERTA':           '#9b59b6',
            }
            tipo_counts = df_filtered['type'].value_counts().reset_index()
            tipo_counts.columns = ['Tipo', 'Quantidade']
            cores_ordem = [CORES_TIPO.get(t, '#95a5a6') for t in tipo_counts['Tipo']]

            fig_pie = px.pie(
                tipo_counts,
                names='Tipo',
                values='Quantidade',
                color='Tipo',
                color_discrete_sequence=cores_ordem,
                hole=0.38
            )
            fig_pie.update_traces(
                textposition='outside',
                textinfo='label+percent',
                textfont_size=12,
                pull=[0.05] * len(tipo_counts),
                marker=dict(line=dict(color='white', width=2))
            )
            fig_pie.update_layout(
                legend=dict(
                    title="Tipos",
                    orientation="v",
                    x=1.02, y=0.5
                ),
                margin=dict(t=40, b=40, l=0, r=120),
                paper_bgcolor='rgba(0,0,0,0)',
                height=360
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            tipo_dominante = tipo_counts.iloc[0]['Tipo']
            pct_dominante  = 100 * tipo_counts.iloc[0]['Quantidade'] / tipo_counts['Quantidade'].sum()
            st.caption(f"🔺 Tipo predominante: **{tipo_dominante}** ({pct_dominante:.1f}% dos incidentes)")

        st.markdown("---")

        # =====================================================
        # GRÁFICO 3 — Dia da Semana
        # =====================================================
        if 'day_of_week' in df_filtered.columns:
            st.subheader("📅 Incidentes por Dia da Semana")
            st.caption(
                "Permite identificar quais dias concentram mais ocorrências. "
                "Dias úteis tendem a ter maior volume por conta do fluxo de veículos "
                "no corredor Foz–Ciudad del Este."
            )

            DIAS_PT = {
                'Monday':    'Segunda',
                'Tuesday':   'Terça',
                'Wednesday': 'Quarta',
                'Thursday':  'Quinta',
                'Friday':    'Sexta',
                'Saturday':  'Sábado',
                'Sunday':    'Domingo'
            }
            order = list(DIAS_PT.keys())
            dow_counts = (
                df_filtered['day_of_week']
                .value_counts()
                .reindex(order, fill_value=0)
                .reset_index()
            )
            dow_counts.columns = ['day_of_week', 'Quantidade']
            dow_counts['Dia'] = dow_counts['day_of_week'].map(DIAS_PT)
            dow_counts['Fim de Semana'] = dow_counts['day_of_week'].isin(['Saturday','Sunday'])

            fig_dow = px.bar(
                dow_counts,
                x='Dia', y='Quantidade',
                labels={'Dia': 'Dia da Semana', 'Quantidade': 'Nº de Incidentes'},
                color='Fim de Semana',
                color_discrete_map={True: '#3498db', False: '#e74c3c'},
                text='Quantidade',
                category_orders={'Dia': list(DIAS_PT.values())}
            )
            fig_dow.update_traces(
                textposition='outside',
                textfont_size=11,
                marker_line_width=0.5,
                marker_line_color='white'
            )
            fig_dow.update_layout(
                legend=dict(
                    title="",
                    orientation="h",
                    y=-0.2,
                    x=0.5,
                    xanchor='center'
                ),
                coloraxis_showscale=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=40, b=60),
                height=380
            )
            # Linha de média
            media_dia = dow_counts['Quantidade'].mean()
            fig_dow.add_hline(
                y=media_dia,
                line_dash="dot",
                line_color="gray",
                annotation_text=f"Média: {media_dia:.1f}",
                annotation_position="top right",
                annotation_font_color="gray"
            )
            st.plotly_chart(fig_dow, use_container_width=True)
            st.caption(
                "🔴 Dias úteis (seg–sex) &nbsp;|&nbsp; 🔵 Fim de semana &nbsp;|&nbsp; "
                "- - - Média diária do período"
            )

        st.markdown("---")

        # =====================================================
        # GRÁFICO 4 — Top 10 Ruas com mais incidentes
        # =====================================================
        if 'street' in df_filtered.columns:
            st.subheader("🛣️ Top 10 Ruas com Mais Incidentes")
            st.caption(
                "As vias com maior concentração de alertas no período filtrado. "
                "Pode indicar trechos que necessitam de atenção especial da gestão viária."
            )

            rua_counts = (
                df_filtered[df_filtered['street'].notna() & (df_filtered['street'] != 'N/A')]
                ['street']
                .value_counts()
                .head(10)
                .reset_index()
            )
            rua_counts.columns = ['Rua', 'Quantidade']

            if not rua_counts.empty:
                fig_ruas = px.bar(
                    rua_counts.sort_values('Quantidade'),
                    x='Quantidade', y='Rua',
                    orientation='h',
                    labels={'Quantidade': 'Nº de Incidentes', 'Rua': ''},
                    color='Quantidade',
                    color_continuous_scale='OrRd',
                    text='Quantidade'
                )
                fig_ruas.update_traces(
                    textposition='outside',
                    textfont_size=11,
                    marker_line_width=0
                )
                fig_ruas.update_layout(
                    coloraxis_showscale=False,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=20, b=20, l=10, r=60),
                    height=420,
                    yaxis=dict(autorange='reversed')
                )
                st.plotly_chart(fig_ruas, use_container_width=True)
                rua_top = rua_counts.iloc[0]['Rua']
                qtd_top = rua_counts.iloc[0]['Quantidade']
                st.caption(f"🔺 Via mais crítica: **{rua_top}** com **{qtd_top}** ocorrências")
            else:
                st.info("Nenhuma rua identificada nos registros filtrados.")

    else:
        st.info("ℹ️ Sem dados para gerar gráficos. Ajuste os filtros na barra lateral.")

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
# 23. RODAPÉ
# =============================================
st.markdown("---")
st.info("💡 Passe o mouse sobre os mapas para ver coordenadas em tempo real no canto superior direito.")
st.caption(
    f"Fonte: Google Drive | "
    f"Hora Foz: {hora_foz_atual.strftime('%H:%M')} (UTC-3) | "
    f"Atualizações manuais: {st.session_state.manual_refreshes} | "
    f"App online há {tempo_total // 60} min"
)
