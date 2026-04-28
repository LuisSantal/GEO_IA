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
# ── Pastas secundárias (novos dados — mesmo formato) ──────────────────────────
FOLDER_ALERTS_ID2 = "1kQfYRJz0-EwY4gcsjTTVBCgK9zO5BAR0"   # ← substitua pelo ID real
FOLDER_JAMS_ID2   = "16bblUG7NQmLMZM7BQUGAa3-GZIFYMka0"     # ← substitua pelo ID real

# =============================================
# 5. FUNÇÕES DE CORES
# =============================================

def get_congestion_color(speed_kmh):
    """
    Azul (fluindo) → Verde → Amarelo → Laranja → Vermelho (parado)
    """
    if speed_kmh >= 80:   return '#2196F3'   # 🔵 Azul       — livre / fluindo
    elif speed_kmh >= 60: return '#4CAF50'   # 🟢 Verde       — bom
    elif speed_kmh >= 40: return '#8BC34A'   # 🟡 Verde claro — moderado
    elif speed_kmh >= 20: return '#FF9800'   # 🟠 Laranja     — lento
    elif speed_kmh >= 5:  return '#F44336'   # 🔴 Vermelho    — muito lento
    else:                 return '#7B1FA2'   # 🟣 Roxo        — parado / travado


def get_danger_color(incident_type, subtype=None):
    """
    Cores por tipo de ocorrência.
    Subtipo pode suavizar a cor para ocorrências leves.
    """
    # Ocorrências leves — tons mais suaves
    LEVE_SUBTYPES = {
        'ACIDENTE LEVE',
        'TRÂNSITO MODERADO',
        'PERIGO NA VIA',
        'OBJETO NA VIA',
        'ANIMAL NA VIA',
        'VEÍCULO PARADO',
        'CONDIÇÕES CLIMÁTICAS',
    }

    t = str(incident_type).upper().strip() if incident_type else ''
    s = str(subtype).upper().strip()       if subtype       else ''

    is_leve = s in LEVE_SUBTYPES

    color_map = {
        # Graves — cores fortes
        'ACIDENTE':          '#F44336' if not is_leve else '#EF9A9A',  # vermelho → rosado
        'VIA FECHADA':       '#B71C1C',                                 # vermelho escuro
        'CONGESTIONAMENTO':  '#7B1FA2' if not is_leve else '#CE93D8',  # roxo → lilás
        # Perigos — laranja
        'PERIGO':            '#FF9800' if not is_leve else '#FFCC80',  # laranja → pêssego
        'PERIGO CLIMÁTICO':  '#29B6F6',                                 # azul claro
        # Obras — cinza
        'OBRAS':             '#78909C',                                 # cinza azulado
        # Alerta genérico — amarelo
        'ALERTA':            '#FDD835',                                 # amarelo
    }

    # Subtipo com cor específica sobrepõe o tipo
    subtype_override = {
        'ACIDENTE GRAVE':    '#B71C1C',   # vermelho escuro
        'ACIDENTE LEVE':     '#EF9A9A',   # rosado
        'BURACO NA VIA':     '#FF9800',   # laranja
        'OBRAS NA VIA':      '#78909C',   # cinza
        'SEMÁFORO QUEBRADO': '#FDD835',   # amarelo
        'INUNDAÇÃO':         '#0288D1',   # azul médio
        'NEBLINA':           '#B0BEC5',   # cinza claro
        'TRÂNSITO PARADO':   '#7B1FA2',   # roxo
        'TRÂNSITO PESADO':   '#F44336',   # vermelho
        'TRÂNSITO MODERADO': '#FF9800',   # laranja
    }

    if s in subtype_override:
        return subtype_override[s]

    return color_map.get(t, '#90A4AE')   # fallback cinza claro

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
    # ── Vias fechadas ─────────────────────────────────────────────────────────
    'ROAD_CLOSED_CONSTRUCTION':               'OBRAS',
    'ROAD_CLOSED_EVENT':                      'EVENTO',

    # ── Perigos na pista ──────────────────────────────────────────────────────
    'HAZARD_ON_ROAD':                         'PERIGO NA VIA',
    'HAZARD_ON_ROAD_POT_HOLE':                'BURACO NA VIA',
    'HAZARD_ON_ROAD_ROAD_KILL':               'ANIMAL NA VIA',
    'HAZARD_ON_ROAD_CAR_STOPPED':             'VEÍCULO PARADO NA VIA',
    'HAZARD_ON_ROAD_CONSTRUCTION':            'OBRAS NA VIA',
    'HAZARD_ON_ROAD_OBJECT':                  'OBJETO NA VIA',
    'HAZARD_ON_ROAD_TRAFFIC_LIGHT_FAULT':     'SEMÁFORO QUEBRADO',
    'HAZARD_ON_ROAD_ICE':                     'PISTA COM GELO',
    'HAZARD_ON_ROAD_LANE_CLOSED':             'FAIXA INTERDITADA',

    # ── Perigos no acostamento ────────────────────────────────────────────────
    'HAZARD_ON_SHOULDER':                     'PERIGO NO ACOSTAMENTO',
    'HAZARD_ON_SHOULDER_CAR_STOPPED':         'VEÍCULO PARADO NO ACOSTAMENTO',
    'HAZARD_ON_SHOULDER_ANIMALS':             'ANIMAIS NO ACOSTAMENTO',
    'HAZARD_ON_SHOULDER_MISSING_SIGN':        'SINALIZAÇÃO AUSENTE',

    # ── Condições climáticas ──────────────────────────────────────────────────
    'HAZARD_WEATHER':                         'CONDIÇÕES CLIMÁTICAS',
    'HAZARD_WEATHER_FOG':                     'NEBLINA',
    'HAZARD_WEATHER_HAIL':                    'GRANIZO',
    'HAZARD_WEATHER_HEAVY_RAIN':              'CHUVA FORTE',
    'HAZARD_WEATHER_FLOOD':                   'INUNDAÇÃO',
    'HAZARD_WEATHER_MONSOON':                 'TEMPORAL',
    'HAZARD_WEATHER_TORNADO':                 'TORNADO',
    'HAZARD_WEATHER_HEAT_WAVE':               'ONDA DE CALOR',
    'HAZARD_WEATHER_HEAVY_SNOW':              'NEVE INTENSA',
    'HAZARD_WEATHER_FREEZING_RAIN':           'CHUVA COM GELO',

    # ── Acidentes ─────────────────────────────────────────────────────────────
    'ACCIDENT_MAJOR':                         'ACIDENTE GRAVE',
    'ACCIDENT_MINOR':                         'ACIDENTE LEVE',

    # ── Congestionamentos ─────────────────────────────────────────────────────
    'JAM_HEAVY_TRAFFIC':                      'TRÂNSITO PESADO',
    'JAM_MODERATE_TRAFFIC':                   'TRÂNSITO MODERADO',
    'JAM_STAND_STILL_TRAFFIC':                'TRÂNSITO PARADO',
    'JAM_LIGHT_TRAFFIC':                      'TRÂNSITO LEVE',
}

def translate_dataframe(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    if 'type' in df.columns:
        df['type'] = df['type'].replace(TYPE_MAP)
    if 'subtype' in df.columns:
        df['subtype'] = df['subtype'].replace(SUBTYPE_MAP)
        # Fallback: formata códigos desconhecidos removendo prefixo e underscores
        known = set(SUBTYPE_MAP.values())
        mask  = df['subtype'].notna() & ~df['subtype'].isin(known)
        df.loc[mask, 'subtype'] = (
            df.loc[mask, 'subtype']
            .str.replace(r'^(HAZARD_ON_ROAD_|HAZARD_ON_SHOULDER_|HAZARD_WEATHER_|HAZARD_|ACCIDENT_|JAM_|ROAD_CLOSED_)', '', regex=True)
            .str.replace('_', ' ', regex=False)
            .str.title()
        )
    return df


# =============================================
# 11. PIPELINE PRINCIPAL DE DADOS
# =============================================
@st.cache_data(ttl=600, show_spinner="🔄 Carregando dados do Google Drive...")
def load_all_data():

    # ── Busca o arquivo mais recente em cada pasta ────────────────────────────
    alerts_id  = get_latest_h5_id(FOLDER_ALERTS_ID)
    alerts_id2 = get_latest_h5_id(FOLDER_ALERTS_ID2)
    jams_id    = get_latest_h5_id(FOLDER_JAMS_ID)
    jams_id2   = get_latest_h5_id(FOLDER_JAMS_ID2)

    # ── Carrega e mescla alertas ──────────────────────────────────────────────
    frames_alerts = []
    if alerts_id:  frames_alerts.append(load_hdf_from_drive(alerts_id))
    if alerts_id2: frames_alerts.append(load_hdf_from_drive(alerts_id2))

    if frames_alerts:
        df_alerts = pd.concat(frames_alerts, ignore_index=True)
        dedup_cols = ['uuid'] if 'uuid' in df_alerts.columns else ['pubMillis', 'street']
        df_alerts  = df_alerts.drop_duplicates(subset=dedup_cols)
    else:
        df_alerts = pd.DataFrame()

    # ── Carrega e mescla jams ─────────────────────────────────────────────────
    frames_jams = []
    if jams_id:  frames_jams.append(load_hdf_from_drive(jams_id))
    if jams_id2: frames_jams.append(load_hdf_from_drive(jams_id2))

    if frames_jams:
        df_jams   = pd.concat(frames_jams, ignore_index=True)
        dedup_cols = ['uuid'] if 'uuid' in df_jams.columns else ['pubMillis', 'street']
        df_jams   = df_jams.drop_duplicates(subset=dedup_cols)
    else:
        df_jams = pd.DataFrame()

    # ── Pipeline de normalização (inalterado) ─────────────────────────────────
    if not df_alerts.empty:
        df_alerts = normalize_timestamps(df_alerts)
        df_alerts = extract_coordinates(df_alerts)   # alertas usam 'location'
        df_alerts = translate_dataframe(df_alerts)
        if 'street' not in df_alerts.columns:
            df_alerts['street'] = 'N/A'

    if not df_jams.empty:
        df_jams = normalize_timestamps(df_jams)
        df_jams = extract_jams_coordinates(df_jams)  # jams usam 'line'
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

    # ── Posição do cursor ──────────────────────────────────────────────────────
    plugins.MousePosition(
        position='topright', separator=' | ',
        prefix='Lat/Lon: ', num_digits=5
    ).add_to(m)

    # ── Tela cheia ────────────────────────────────────────────────────────────
    plugins.Fullscreen(
        position='topleft',
        title='Expandir mapa',
        title_cancel='Sair da tela cheia',
        force_separate_button=True
    ).add_to(m)

    # ── Barra de escala gráfica (atualiza com zoom) ───────────────────────────
    scale_js = """
    <script>
    document.addEventListener("DOMContentLoaded", function() {
        setTimeout(function() {
            var maps = Object.values(window).filter(function(v) {
                return v && v._leaflet_id && typeof v.addControl === 'function';
            });
            maps.forEach(function(map) {
                // Barra de escala métrica
                L.control.scale({
                    position: 'bottomleft',
                    metric: true,
                    imperial: false,
                    maxWidth: 120
                }).addTo(map);

                // ── Indicador de nível de zoom ────────────────────────────
                var ZoomIndicator = L.Control.extend({
                    options: { position: 'bottomleft' },
                    onAdd: function(map) {
                        var div = L.DomUtil.create('div');
                        div.style.cssText = [
                            'background:white',
                            'border:2px solid #555',
                            'border-radius:6px',
                            'padding:3px 8px',
                            'font-size:12px',
                            'font-family:Arial,sans-serif',
                            'font-weight:bold',
                            'color:#333',
                            'box-shadow:0 2px 6px rgba(0,0,0,0.3)',
                            'min-width:64px',
                            'text-align:center',
                            'margin-bottom:4px'
                        ].join(';');
                        div.innerHTML = '🔍 Zoom: ' + map.getZoom();
                        map.on('zoomend', function() {
                            div.innerHTML = '🔍 Zoom: ' + map.getZoom();
                        });
                        return div;
                    }
                });
                new ZoomIndicator().addTo(map);
            });
        }, 800);
    });
    </script>
    """
    m.get_root().html.add_child(folium.Element(scale_js))

    # ── Rosa dos ventos SVG ────────────────────────────────────────────────────
    compass_html = """
    <div style="
        position:absolute;
        bottom:110px;
        left:10px;
        z-index:9999;
        pointer-events:none;
    ">
      <svg width="54" height="54" viewBox="0 0 54 54"
           xmlns="http://www.w3.org/2000/svg"
           style="filter:drop-shadow(0 2px 6px rgba(0,0,0,0.5));">
        <circle cx="27" cy="27" r="26" fill="white" stroke="#555" stroke-width="2"/>
        <polygon points="27,4 22,27 27,22 32,27" fill="#d32f2f"/>
        <polygon points="27,50 22,27 27,32 32,27" fill="#999"/>
        <polygon points="50,27 27,22 32,27 27,32" fill="#ccc"/>
        <polygon points="4,27 27,22 22,27 27,32" fill="#ccc"/>
        <circle cx="27" cy="27" r="4" fill="#555"/>
        <text x="27" y="16" text-anchor="middle" font-size="9" font-weight="bold"
              font-family="Arial" fill="#d32f2f">N</text>
        <text x="27" y="51" text-anchor="middle" font-size="9" font-weight="bold"
              font-family="Arial" fill="#777">S</text>
        <text x="49" y="30" text-anchor="middle" font-size="8"
              font-family="Arial" fill="#888">L</text>
        <text x="6"  y="30" text-anchor="middle" font-size="8"
              font-family="Arial" fill="#888">O</text>
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
            color = get_danger_color(tipo, row.get('subtype'))
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
    all_dates.update(pd.to_datetime(df_alerts_raw["date"]).dt.date.unique())
if not df_jams_raw.empty:
    all_dates.update(pd.to_datetime(df_jams_raw["date"]).dt.date.unique())

if all_dates:
    min_date     = min(all_dates)
    max_date     = max(all_dates)
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

# ── 3. TIPO DE OCORRÊNCIA (atrelado à data) ───────────────────────────────────
tipos_na_data = []
if not df_alerts_raw.empty:
    tipos_na_data = sorted(
        df_alerts_raw.loc[df_alerts_raw["date"] == selected_date, "type"]
        .dropna().unique().tolist()
    )
if not tipos_na_data:  # fallback
    tipos_na_data = sorted(df_alerts_raw["type"].dropna().unique().tolist()) if not df_alerts_raw.empty else []

filtro_tipo = st.sidebar.multiselect(
    "⚠️ Tipo de Ocorrência",
    options=tipos_na_data,
    default=tipos_na_data,
)

# ── 4. NATUREZA DA OCORRÊNCIA (atrelado ao tipo selecionado + data) ───────────
naturezas_na_data = []
if not df_alerts_raw.empty and "subtype" in df_alerts_raw.columns:
    mask_natureza = (df_alerts_raw["date"] == selected_date)
    if filtro_tipo:
        mask_natureza &= df_alerts_raw["type"].isin(filtro_tipo)
    naturezas_na_data = sorted(
        df_alerts_raw.loc[mask_natureza, "subtype"]
        .dropna()
        .loc[lambda s: ~s.isin(["nan", ""])]
        .unique().tolist()
    )

filtro_natureza = st.sidebar.multiselect(
    "🔍 Natureza da Ocorrência",
    options=naturezas_na_data,
    default=naturezas_na_data,
)

# ── 5. RUA / VIA (atrelado à data + tipo) ─────────────────────────────────────
ruas_na_data = []
if not df_alerts_raw.empty and "street" in df_alerts_raw.columns:
    mask_rua = (
        (df_alerts_raw["date"] == selected_date) &
        (df_alerts_raw["street"].notna()) &
        (~df_alerts_raw["street"].isin(["NA", "nan", ""]))
    )
    if filtro_tipo:
        mask_rua &= df_alerts_raw["type"].isin(filtro_tipo)
    ruas_na_data = sorted(df_alerts_raw.loc[mask_rua, "street"].unique().tolist())

filtro_rua = st.sidebar.selectbox(
    "🛣️ Rua / Via",
    options=["(Todas)"] + ruas_na_data,
    index=0,
)
filtro_rua = "" if filtro_rua == "(Todas)" else filtro_rua

# ── 6. FAIXA DE VELOCIDADE — congestionamentos (atrelado à data) ──────────────
vel_min_data, vel_max_data = 0.0, 120.0
if not df_jams_raw.empty and "speed" in df_jams_raw.columns:
    speeds_na_data = df_jams_raw.loc[df_jams_raw["date"] == selected_date, "speed"].dropna()
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

# ── 7. PAINEL DE CONGESTIONAMENTO (atrelado à data) ───────────────────────────
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
        st.sidebar.metric("Vel. Média",    f"{media_vel:.1f} km/h", delta=status_label)
        st.sidebar.metric("Total de Jams", total_jams)
    else:
        st.sidebar.info(f"Sem dados de congestionamento em {selected_date.strftime('%d/%m')}.")

# =============================================
# 17. APLICAÇÃO DOS FILTROS
# =============================================
df_filtered = pd.DataFrame()
if not df_alerts_raw.empty:
    df_filtered = df_alerts_raw[
        (df_alerts_raw["date"] == selected_date) &
        (df_alerts_raw["hour"].between(hora_range[0], hora_range[1])) &
        (df_alerts_raw["type"].isin(filtro_tipo) if filtro_tipo else True)
    ].copy()

    if filtro_natureza and "subtype" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["subtype"].isin(filtro_natureza)]

    if filtro_rua and "street" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["street"] == filtro_rua]

    # Fallback 1: zera tipo/natureza/rua mas mantém data + hora
    if df_filtered.empty:
        st.sidebar.warning("⚠️ Sem dados para essa combinação. Exibindo todos os registros da data.")
        df_filtered = df_alerts_raw[
            (df_alerts_raw["date"] == selected_date) &
            (df_alerts_raw["hour"].between(hora_range[0], hora_range[1]))
        ].copy()
    # Fallback 2: ignora data também
    if df_filtered.empty:
        df_filtered = df_alerts_raw[
            df_alerts_raw["hour"].between(hora_range[0], hora_range[1])
        ].copy()

df_jams_filtered = pd.DataFrame()
if not df_jams_raw.empty:
    df_jams_filtered = df_jams_raw[
        (df_jams_raw["date"] == selected_date) &
        (df_jams_raw["hour"].between(hora_range[0], hora_range[1])) &
        ((df_jams_raw["speed"].fillna(0) * 3.6).between(vel_range[0], vel_range[1]))
    ].copy()
    if df_jams_filtered.empty:
        df_jams_filtered = df_jams_raw[
            df_jams_raw["hour"].between(hora_range[0], hora_range[1])
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
label_tipo = (
    ", ".join(filtro_tipo) if filtro_tipo and len(filtro_tipo) <= 2
    else f"{len(filtro_tipo)} tipos" if filtro_tipo and len(filtro_tipo) < len(tipos_na_data)
    else "Todos"
)
label_natureza = (
    ", ".join(filtro_natureza) if filtro_natureza and len(filtro_natureza) <= 2
    else f"{len(filtro_natureza)} naturezas" if filtro_natureza and len(filtro_natureza) < len(naturezas_na_data)
    else "Todas"
)

col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
col_f1.metric("📅 Data",       selected_date.strftime("%d/%m/%Y"))
col_f2.metric("🚨 Tipo",       label_tipo)
col_f3.metric("🔍 Natureza",   label_natureza)
col_f4.metric("🛣️ Rua",        filtro_rua if filtro_rua else "Todas")
col_f5.metric("⏰ Horário",    f"{hora_range[0]:02d}h – {hora_range[1]:02d}h")

st.caption(
    f"🔍 Filtros ativos → "
    f"**{len(df_filtered)} incidente(s)** exibidos "
    f"{'em ' + selected_date.strftime('%d/%m/%Y') if not df_filtered.empty else '(fallback: dados mais recentes)'} "
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
            # ── Legenda ──────────────────────────────────────────────────────────
            st.markdown("""
            | Cor | Tipo | Natureza |
            |---|---|---|
            | 🔴 | Acidente grave | Alta gravidade |
            | 🩷 | Acidente leve | Baixa gravidade |
            | 🟤 | Via fechada / Obras | Bloqueio total |
            | 🟠 | Perigo / Buraco na via | Risco moderado |
            | 🟡 | Alerta / Semáforo | Atenção |
            | 🩵 | Perigo climático | Condições adversas |
            | 🟣 | Congestionamento | Trânsito parado |
            """)
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
            # ── Legenda ──────────────────────────────────────────────────────────
            st.markdown("""
            | Cor | Velocidade | Status |
            |---|---|---|
            | 🔵 | ≥ 80 km/h | Livre / Fluindo |
            | 🟢 | 60–80 km/h | Bom |
            | 🟡 | 40–60 km/h | Moderado |
            | 🟠 | 20–40 km/h | Lento |
            | 🔴 | 5–20 km/h | Muito lento |
            | 🟣 | < 5 km/h | Parado / Travado |
            """)
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
                    danger_cor = get_danger_color(tipo, row.get('subtype'))


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
                    cor     = get_danger_color(tipo, row.get('subtype'))

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

           # ── Legenda ──────────────────────────────────────────────────────────
            st.markdown("""
            | Cor | Concentração |
            |---|---|
            | 🟡 Amarelo claro | Baixa — poucos registros |
            | 🟠 Laranja | Média — atenção |
            | 🔴 Vermelho | Alta — ponto crítico |
            | 🟤 Bordô | Crítica — intervenção necessária |
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

        # Base histórica para gráficos que não dependem da data
        df_hist = df_alerts_raw.copy()
        if filtro_tipo:
            df_hist = df_hist[df_hist['type'].isin(filtro_tipo)]
        if filtro_natureza and 'subtype' in df_hist.columns:
            df_hist = df_hist[df_hist['subtype'].isin(filtro_natureza)]
        if filtro_rua and 'street' in df_hist.columns:
            df_hist = df_hist[df_hist['street'] == filtro_rua]

        DIAS_PT = {
            'Monday': 'Segunda', 'Tuesday': 'Terça',  'Wednesday': 'Quarta',
            'Thursday': 'Quinta', 'Friday': 'Sexta',
            'Saturday': 'Sábado', 'Sunday': 'Domingo'
        }
        CORES_TIPO = {
            'ACIDENTE': '#e74c3c', 'VIA FECHADA': '#c0392b',
            'PERIGO': '#e67e22', 'PERIGO CLIMÁTICO': '#3498db',
            'CONGESTIONAMENTO': '#f39c12', 'ALERTA': '#9b59b6',
        }

        # =====================================================
        # GRÁFICO 1 + 2 — Hora do dia | Proporção por tipo
        # =====================================================
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.subheader("📊 Incidentes por Hora do Dia")
            st.caption("Distribuição dos alertas ao longo das 24h do dia selecionado.")
            hora_counts = (
                df_filtered['hour'].value_counts()
                .reindex(range(24), fill_value=0).reset_index()
            )
            hora_counts.columns = ['Hora', 'Quantidade']
            hora_pico = int(hora_counts.loc[hora_counts['Quantidade'].idxmax(), 'Hora'])
            fig_hora = px.bar(
                hora_counts, x='Hora', y='Quantidade',
                labels={'Hora': 'Hora (UTC-3 Foz)', 'Quantidade': 'Nº Incidentes'},
                color='Quantidade', color_continuous_scale='Reds', text='Quantidade'
            )
            fig_hora.update_traces(textposition='outside', textfont_size=10,
                                   marker_line_width=0.5, marker_line_color='white')
            fig_hora.add_vline(x=hora_pico, line_dash="dash", line_color="darkred",
                               annotation_text=f"Pico: {hora_pico:02d}h",
                               annotation_position="top right",
                               annotation_font_color="darkred")
            fig_hora.update_layout(
                xaxis=dict(tickmode='linear', tick0=0, dtick=1),
                coloraxis_showscale=False, margin=dict(t=40, b=40),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=360
            )
            st.plotly_chart(fig_hora, use_container_width=True)
            st.caption(f"🔺 Pico: **{hora_pico:02d}:00 – {hora_pico:02d}:59**")

        with col_g2:
            st.subheader("🥧 Natureza das Ocorrências")
            st.caption(
                "Distribuição por subtipo de todos os incidentes do dia selecionado. "
                "Detalha a natureza real de cada ocorrência além do tipo genérico."
            )

            # ── Tenta usar subtipo; fallback para tipo se subtipo vazio ──────
            tem_subtipo = (
                'subtype' in df_filtered.columns and
                df_filtered['subtype'].notna().any() and
                (~df_filtered['subtype'].isin(['nan', ''])).any()
            )

            if tem_subtipo:
                df_sub = df_filtered[
                    df_filtered['subtype'].notna() &
                    (~df_filtered['subtype'].isin(['nan', '']))
                ].copy()
                # Adiciona o tipo como prefixo quando o subtipo for genérico
                df_sub['label'] = df_sub.apply(
                    lambda r: r['subtype']
                    if r['subtype'] != r['type']
                    else r['type'],
                    axis=1
                )
                sub_counts = df_sub['label'].value_counts().reset_index()
                sub_counts.columns = ['Natureza', 'Quantidade']
                dimensao = "subtipo"
            else:
                # Fallback: agrupa por tipo
                sub_counts = df_filtered['type'].value_counts().reset_index()
                sub_counts.columns = ['Natureza', 'Quantidade']
                dimensao = "tipo"

            CORES_NATUREZA = {
                # Acidentes
                'ACIDENTE GRAVE':                 '#b71c1c',
                'ACIDENTE LEVE':                  '#ef9a9a',
                'ACIDENTE':                       '#e74c3c',
                # Vias fechadas
                'VIA FECHADA':                    '#c0392b',
                'OBRAS':                          '#78909c',
                'EVENTO':                         '#ab47bc',
                # Perigos na pista
                'BURACO NA VIA':                  '#e67e22',
                'PERIGO NA VIA':                  '#f39c12',
                'OBJETO NA VIA':                  '#d35400',
                'ANIMAL NA VIA':                  '#27ae60',
                'VEÍCULO PARADO NA VIA':          '#c0392b',
                'VEÍCULO PARADO NO ACOSTAMENTO':  '#e74c3c',
                'OBRAS NA VIA':                   '#7f8c8d',
                'SEMÁFORO QUEBRADO':              '#f1c40f',
                'FAIXA INTERDITADA':              '#8e44ad',
                'PISTA COM GELO':                 '#3498db',
                # Acostamento
                'PERIGO NO ACOSTAMENTO':          '#ff8c00',
                'ANIMAIS NO ACOSTAMENTO':         '#2ecc71',
                'SINALIZAÇÃO AUSENTE':            '#95a5a6',
                # Climáticos
                'NEBLINA':                        '#bdc3c7',
                'CHUVA FORTE':                    '#2980b9',
                'INUNDAÇÃO':                      '#1a5276',
                'GRANIZO':                        '#5dade2',
                'TEMPORAL':                       '#1abc9c',
                'ONDA DE CALOR':                  '#ff6b35',
                'CONDIÇÕES CLIMÁTICAS':           '#85c1e9',
                'PERIGO CLIMÁTICO':               '#3498db',
                # Congestionamentos
                'TRÂNSITO PARADO':                '#7b1fa2',
                'TRÂNSITO PESADO':                '#f44336',
                'TRÂNSITO MODERADO':              '#ff9800',
                'TRÂNSITO LEVE':                  '#4caf50',
                'CONGESTIONAMENTO':               '#f39c12',
                # Genérico
                'PERIGO':                         '#e67e22',
                'ALERTA':                         '#9b59b6',
            }
            cores_seq = [CORES_NATUREZA.get(n, '#95a5a6') for n in sub_counts['Natureza']]

            fig_pie = px.pie(
                sub_counts,
                names='Natureza', values='Quantidade',
                color='Natureza',
                color_discrete_sequence=cores_seq,
                hole=0.38
            )
            fig_pie.update_traces(
                textposition='outside',
                textinfo='label+percent',
                textfont_size=11,
                pull=[0.04] * len(sub_counts),
                marker=dict(line=dict(color='white', width=2))
            )
            fig_pie.update_layout(
                legend=dict(title="Natureza", orientation="v", x=1.02, y=0.5),
                margin=dict(t=40, b=40, l=0, r=150),
                paper_bgcolor='rgba(0,0,0,0)',
                height=380
            )
            st.plotly_chart(fig_pie, use_container_width=True)

            nat_top = sub_counts.iloc[0]['Natureza']
            pct_top = 100 * sub_counts.iloc[0]['Quantidade'] / sub_counts['Quantidade'].sum()
            st.caption(
                f"🔺 Natureza predominante: **{nat_top}** ({pct_top:.1f}%) &nbsp;|&nbsp; "
                f"{'Agrupado por subtipo' if dimensao == 'subtipo' else '⚠️ Sem subtipo disponível — agrupado por tipo'}"
            )
        st.markdown("---")

        # ── Filtro de tipo/subtipo exclusivo da aba de gráficos (histórico) ──
        st.markdown("#### 🔎 Refinar análise histórica")
        col_ft1, col_ft2 = st.columns(2)

        tipos_hist_disp = sorted(df_hist['type'].dropna().unique().tolist()) \
            if 'type' in df_hist.columns else []

        with col_ft1:
            filtro_tipo_graf = st.multiselect(
                "Tipo de ocorrência",
                options=tipos_hist_disp,
                default=tipos_hist_disp,
                key="graf_tipo"
            )

        # Subtipos atrelados aos tipos selecionados
        subtipos_hist_disp = []
        if 'subtype' in df_hist.columns and filtro_tipo_graf:
            subtipos_hist_disp = sorted(
                df_hist[
                    df_hist['type'].isin(filtro_tipo_graf) &
                    df_hist['subtype'].notna() &
                    (~df_hist['subtype'].isin(['nan', '']))
                ]['subtype'].unique().tolist()
            )

        with col_ft2:
            filtro_sub_graf = st.multiselect(
                "Natureza (subtipo)",
                options=subtipos_hist_disp,
                default=subtipos_hist_disp,
                key="graf_sub"
            )

        # Aplica os filtros na base histórica
        df_hist_graf = df_hist.copy()
        if filtro_tipo_graf:
            df_hist_graf = df_hist_graf[df_hist_graf['type'].isin(filtro_tipo_graf)]
        if filtro_sub_graf and 'subtype' in df_hist_graf.columns:
            df_hist_graf = df_hist_graf[
                df_hist_graf['subtype'].isin(filtro_sub_graf) |
                df_hist_graf['subtype'].isna()
            ]

        total_graf = len(df_hist_graf)
        st.caption(f"📊 Base histórica refinada: **{total_graf}** registros")
        st.markdown("---")

        # =====================================================
        # GRÁFICO 3 — Dia da Semana com barras por Tipo
        # =====================================================
        st.subheader("📅 Incidentes por Dia da Semana")
        st.caption("Barras empilhadas por tipo de ocorrência — histórico completo.")

        order_dow = list(DIAS_PT.keys())
        if 'day_of_week' in df_hist.columns and not df_hist.empty:
            df_dow = df_hist.copy()
            df_dow['Dia'] = df_dow['day_of_week'].map(DIAS_PT)

            dow_tipo = (
                df_dow.groupby(['Dia', 'type'])
                .size().reset_index(name='Quantidade')
            )
            order_dias = list(DIAS_PT.values())

            fig_dow = px.bar(
                dow_tipo, x='Dia', y='Quantidade', color='type',
                labels={'Dia': 'Dia da Semana', 'Quantidade': 'Nº Incidentes', 'type': 'Tipo'},
                color_discrete_map=CORES_TIPO,
                category_orders={'Dia': order_dias},
                barmode='stack', text_auto=True
            )
            # Marca o dia atual
            dia_hoje_pt = DIAS_PT.get(hora_foz_atual.strftime('%A'), '')
            if dia_hoje_pt:
                idx_hoje = order_dias.index(dia_hoje_pt)
                fig_dow.add_shape(type='line', x0=idx_hoje, x1=idx_hoje,
                                  y0=0, y1=1, xref='x', yref='paper',
                                  line=dict(color='gold', width=2, dash='dot'))
                fig_dow.add_annotation(x=idx_hoje, y=1, xref='x', yref='paper',
                                       text=f'Hoje ({dia_hoje_pt})', showarrow=False,
                                       font=dict(color='gold', size=11),
                                       xanchor='left', yanchor='top')
            fig_dow.update_layout(
                legend=dict(title='Tipo', orientation='h', y=-0.25, x=0.5, xanchor='center'),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=40, b=80), height=420
            )
            st.plotly_chart(fig_dow, use_container_width=True)
            st.caption("🟡 Hoje marcado em dourado &nbsp;|&nbsp; Cores por tipo de ocorrência")

        st.markdown("---")

        # =====================================================
        # GRÁFICO 4 — Top 10 Vias com barras por Subtipo
        # =====================================================
        st.subheader("🛣️ Vias Críticas — Incidentes por Natureza")
        st.caption(
            "Top 10 vias com mais ocorrências históricas. "
            "Cada barra mostra a composição por natureza (subtipo) do incidente."
        )

        top_ruas_lista = []
        if 'street' in df_hist.columns:
            top_ruas_lista = (
                df_hist[df_hist['street'].notna() &
                        (~df_hist['street'].isin(['N/A', 'nan', '']))]
                ['street'].value_counts().head(10).index.tolist()
            )

        if top_ruas_lista and 'subtype' in df_hist.columns:
            df_rua = df_hist[
                df_hist['street'].isin(top_ruas_lista) &
                df_hist['subtype'].notna() &
                (~df_hist['subtype'].isin(['nan', '']))
            ].copy()

            rua_sub = (
                df_rua.groupby(['street', 'subtype'])
                .size().reset_index(name='Quantidade')
            )
            # Ordena ruas pelo total
            ordem_ruas = (
                rua_sub.groupby('street')['Quantidade'].sum()
                .sort_values(ascending=True).index.tolist()
            )
            fig_rua = px.bar(
                rua_sub, x='Quantidade', y='street', color='subtype',
                labels={'Quantidade': 'Nº Incidentes', 'street': '', 'subtype': 'Natureza'},
                orientation='h', barmode='stack',
                category_orders={'street': ordem_ruas}
            )
            fig_rua.update_layout(
                legend=dict(title='Natureza', orientation='v', x=1.01, y=1),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=20, b=20, l=10, r=200), height=460
            )
            st.plotly_chart(fig_rua, use_container_width=True)
            st.caption(f"🔺 Via mais crítica: **{top_ruas_lista[-1]}**")

        st.markdown("---")

        # =====================================================
        # GRÁFICO 5 — Concentração Rua × Dia da Semana
        # =====================================================
        st.subheader("🗓️ Quais dias cada rua tem mais problemas?")
        st.caption(
            "Quanto mais escura a célula, mais incidentes aconteceram naquele dia. "
            "Use para saber em quais dias fiscalizar cada via."
        )

        if top_ruas_lista and 'day_of_week' in df_hist.columns:
            import plotly.graph_objects as go
            df_hm = df_hist[df_hist['street'].isin(top_ruas_lista)].copy()
            if not df_hm.empty:
                pivot = (
                    df_hm.groupby(['street', 'day_of_week']).size()
                    .unstack(fill_value=0)
                    .reindex(columns=order_dow, fill_value=0)
                )
                pivot.columns = [DIAS_PT.get(c, c) for c in pivot.columns]

                # Rótulos descritivos por célula
                def nivel(v, vmax):
                    if v == 0:           return "Nenhum"
                    elif v <= vmax*0.25: return f"{v} — Baixo"
                    elif v <= vmax*0.60: return f"{v} — Médio"
                    else:                return f"{v} — ⚠️ Alto"

                vmax = pivot.values.max() if pivot.values.max() > 0 else 1
                texto = [[nivel(v, vmax) for v in row] for row in pivot.values]

                fig_hm = go.Figure(data=go.Heatmap(
                    z=pivot.values,
                    x=pivot.columns.tolist(),
                    y=pivot.index.tolist(),
                    colorscale=[
                        [0.0,  '#f0f9e8'],   # branco-verde = nenhum
                        [0.25, '#bae4bc'],   # verde claro  = baixo
                        [0.60, '#f7cb45'],   # amarelo       = médio
                        [0.85, '#f97b2c'],   # laranja       = alto
                        [1.0,  '#d73027'],   # vermelho      = crítico
                    ],
                    text=texto,
                    texttemplate='%{text}',
                    textfont=dict(size=11, color='#333'),
                    hoverongaps=False,
                    showscale=True,
                    colorbar=dict(
                        title='Incidentes',
                        tickvals=[0, vmax*0.25, vmax*0.60, vmax*0.85, vmax],
                        ticktext=['Nenhum', 'Baixo', 'Médio', 'Alto', 'Crítico'],
                        len=0.8
                    )
                ))
                fig_hm.update_layout(
                    xaxis=dict(title='Dia da Semana', side='top',
                               tickfont=dict(size=13, color='#222')),
                    yaxis=dict(title='', tickfont=dict(size=12)),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=60, b=20, l=10, r=20),
                    height=420
                )
                st.plotly_chart(fig_hm, use_container_width=True)

                # Mini legenda textual
                st.markdown(
                    "🟢 **Nenhum** — sem ocorrências &nbsp;|&nbsp; "
                    "🟡 **Médio** — atenção &nbsp;|&nbsp; "
                    "🟠 **Alto** — fiscalizar &nbsp;|&nbsp; "
                    "🔴 **Crítico** — intervenção necessária"
                )

        st.markdown("---")

        # =====================================================
        # GRÁFICO 6 — Concentração Rua × Hora
        # =====================================================
        st.subheader("⏰ Em quais horários cada rua tem mais problemas?")
        st.caption(
            "Cada coluna é uma hora do dia. Quanto mais escura, mais incidentes naquele horário. "
            "Útil para definir horários de patrulhamento ou sinalização extra."
        )

        if top_ruas_lista and 'hour' in df_hist.columns:
            df_hh = df_hist[df_hist['street'].isin(top_ruas_lista)].copy()
            if not df_hh.empty:
                pivot2 = (
                    df_hh.groupby(['street', 'hour']).size()
                    .unstack(fill_value=0)
                    .reindex(columns=range(24), fill_value=0)
                )

                vmax2 = pivot2.values.max() if pivot2.values.max() > 0 else 1
                texto2 = [
                    [nivel(v, vmax2) for v in row]
                    for row in pivot2.values
                ]

                # Agrupa horas em períodos para o eixo X
                labels_hora = []
                for h in range(24):
                    if h < 6:    labels_hora.append(f"{h:02d}h 🌙")
                    elif h < 12: labels_hora.append(f"{h:02d}h 🌅")
                    elif h < 18: labels_hora.append(f"{h:02d}h ☀️")
                    else:        labels_hora.append(f"{h:02d}h 🌆")

                fig_hm2 = go.Figure(data=go.Heatmap(
                    z=pivot2.values,
                    x=labels_hora,
                    y=pivot2.index.tolist(),
                    colorscale=[
                        [0.0,  '#eaf4fb'],
                        [0.25, '#aed6f1'],
                        [0.60, '#f7cb45'],
                        [0.85, '#f97b2c'],
                        [1.0,  '#d73027'],
                    ],
                    text=texto2,
                    texttemplate='%{text}',
                    textfont=dict(size=9, color='#333'),
                    hoverongaps=False,
                    showscale=True,
                    colorbar=dict(
                        title='Incidentes',
                        tickvals=[0, vmax2*0.25, vmax2*0.60, vmax2*0.85, vmax2],
                        ticktext=['Nenhum', 'Baixo', 'Médio', 'Alto', 'Crítico'],
                        len=0.8
                    )
                ))

                # Linhas verticais separando os períodos do dia
                for x_sep in [5.5, 11.5, 17.5]:
                    fig_hm2.add_shape(
                        type='line', x0=x_sep, x1=x_sep, y0=-0.5,
                        y1=len(pivot2)-0.5, xref='x', yref='y',
                        line=dict(color='white', width=2, dash='dot')
                    )

                fig_hm2.update_layout(
                    xaxis=dict(
                        title='Hora do Dia',
                        side='top',
                        tickfont=dict(size=10, color='#222'),
                        tickangle=-45
                    ),
                    yaxis=dict(title='', tickfont=dict(size=12)),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=80, b=20, l=10, r=20),
                    height=440
                )
                st.plotly_chart(fig_hm2, use_container_width=True)

                st.markdown(
                    "🌙 **Madrugada** (00–05h) &nbsp;|&nbsp; "
                    "🌅 **Manhã** (06–11h) &nbsp;|&nbsp; "
                    "☀️ **Tarde** (12–17h) &nbsp;|&nbsp; "
                    "🌆 **Noite** (18–23h)"
                )

        # =====================================================
        # GRÁFICO 7 — Natureza Top 10 com barras por Tipo
        # =====================================================
        st.subheader("🔍 Natureza das Ocorrências × Tipo")
        st.caption("Top 10 subtipos mais frequentes, coloridos pelo tipo pai.")

        if 'subtype' in df_hist.columns and 'type' in df_hist.columns:
            df_nat = df_hist[
                df_hist['subtype'].notna() &
                (~df_hist['subtype'].isin(['nan', '']))
            ].copy()
            nat_tipo = (
                df_nat.groupby(['subtype', 'type']).size().reset_index(name='Quantidade')
            )
            top10_nat = (
                nat_tipo.groupby('subtype')['Quantidade'].sum()
                .nlargest(10).index.tolist()
            )
            nat_tipo = nat_tipo[nat_tipo['subtype'].isin(top10_nat)]
            ordem_nat = (
                nat_tipo.groupby('subtype')['Quantidade'].sum()
                .sort_values(ascending=True).index.tolist()
            )
            fig_nat = px.bar(
                nat_tipo, x='Quantidade', y='subtype', color='type',
                labels={'Quantidade': 'Total', 'subtype': '', 'type': 'Tipo'},
                orientation='h', barmode='stack',
                color_discrete_map=CORES_TIPO,
                category_orders={'subtype': ordem_nat}
            )
            fig_nat.update_layout(
                legend=dict(title='Tipo', orientation='v', x=1.01, y=1),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=20, b=20, l=10, r=160), height=420
            )
            st.plotly_chart(fig_nat, use_container_width=True)

        st.markdown("---")

        # =====================================================
        # GRÁFICO 8 — Tendência Diária por Tipo
        # =====================================================
        st.subheader("📈 Tendência Diária por Tipo de Incidente")
        st.caption("Evolução diária com linhas separadas por tipo — identifica qual categoria está aumentando.")

        if 'date' in df_hist.columns and 'type' in df_hist.columns:
            serie_tipo = (
                df_hist.groupby(['date', 'type']).size().reset_index(name='Quantidade')
            )
            serie_tipo['date'] = pd.to_datetime(serie_tipo['date'])
            if len(serie_tipo) > 1:
                fig_trend = px.line(
                    serie_tipo, x='date', y='Quantidade', color='type',
                    labels={'date': 'Data', 'Quantidade': 'Nº Incidentes', 'type': 'Tipo'},
                    color_discrete_map=CORES_TIPO, markers=True
                )
                fig_trend.update_layout(
                    legend=dict(title='Tipo', orientation='h', y=-0.25, x=0.5, xanchor='center'),
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=30, b=80), height=400
                )
                st.plotly_chart(fig_trend, use_container_width=True)
                dia_pico = serie_tipo.groupby('date')['Quantidade'].sum().idxmax()
                qtd_pico = serie_tipo.groupby('date')['Quantidade'].sum().max()
                st.caption(
                    f"🔺 Dia mais crítico: **{pd.to_datetime(dia_pico).strftime('%d/%m/%Y')}** "
                    f"com **{int(qtd_pico)}** incidentes totais"
                )

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
