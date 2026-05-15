import streamlit as st
import pandas as pd
import plotly.express as px
import io
import re
import ast
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo
import folium
from folium import plugins
from streamlit_folium import st_folium

# =========================================================
# BLOCO 1 — CONFIGURAÇÃO BASE DO APP
# =========================================================

# ---------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Waze Foz do Iguaçu",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# 2. TOKENS VISUAIS E CSS GLOBAL
# ---------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root{
    --bg: #f8fafc;
    --surface: #ffffff;
    --surface-soft: #f1f5f9;
    --text: #1e293b;
    --text-strong: #0f172a;
    --text-muted: #64748b;
    --border: #e2e8f0;
    --primary: #3b82f6;
    --primary-dark: #1d4ed8;
    --primary-soft: #eff6ff;
    --success: #16a34a;
    --warning: #f59e0b;
    --danger: #ef4444;
    --purple: #7b1fa2;
    --radius: 12px;
    --shadow-sm: 0 1px 4px rgba(0,0,0,0.06);
    --shadow-md: 0 4px 15px rgba(59,130,246,0.25);
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
}

body {
    color: var(--text);
}

.stApp {
    background: var(--bg) !important;
    color: var(--text) !important;
}

[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}

[data-testid="stSidebar"] * {
    color: #334155 !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--primary), var(--primary-dark)) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    box-shadow: var(--shadow-md) !important;
}

.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #60a5fa, var(--primary)) !important;
    transform: translateY(-1px) !important;
}

[data-testid="metric-container"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 1rem !important;
    box-shadow: var(--shadow-sm) !important;
}

[data-testid="metric-container"] label {
    color: var(--text-muted) !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
}

[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--text-strong) !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
}

.stTabs [data-baseweb="tab-list"] {
    background: var(--surface-soft) !important;
    border-radius: 12px !important;
    padding: 4px !important;
    gap: 4px !important;
    border: 1px solid var(--border) !important;
}

.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-muted) !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    padding: 8px 16px !important;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, var(--primary), var(--primary-dark)) !important;
    color: white !important;
    box-shadow: 0 2px 8px rgba(59,130,246,0.3) !important;
}

[data-testid="stDataFrame"] {
    border-radius: 12px !important;
    overflow: hidden !important;
    border: 1px solid var(--border) !important;
    background: var(--surface) !important;
}

[data-testid="stAlert"] {
    background: var(--primary-soft) !important;
    border: 1px solid #bfdbfe !important;
    border-radius: 10px !important;
    color: var(--primary-dark) !important;
}

[data-testid="stExpander"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
}

hr {
    border-color: var(--border) !important;
}

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--surface-soft); }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. TIMEZONE LOCAL
# ---------------------------------------------------------
TZ_FOZ = ZoneInfo("America/Sao_Paulo")

def now_foz() -> datetime:
    return datetime.now(TZ_FOZ).replace(tzinfo=None)

# ---------------------------------------------------------
# 4. ESTADO DA SESSÃO
# ---------------------------------------------------------
if "app_start_time" not in st.session_state:
    st.session_state.app_start_time = now_foz()

if "manual_refreshes" not in st.session_state:
    st.session_state.manual_refreshes = 0

tempo_sessao = (now_foz() - st.session_state.app_start_time).total_seconds()
tempo_prox_refresh = 600 - (tempo_sessao % 600)
minutos_restantes = int(tempo_prox_refresh // 60)
segundos_restantes = int(tempo_prox_refresh % 60)
tempo_total = int(tempo_sessao)

# ---------------------------------------------------------
# 5. CONFIGURAÇÕES DE FONTE DE DADOS
# ---------------------------------------------------------
FOLDER_ALERTS_ID = "1xKkqLEusWuNoGzy5-UYuevUbMHAvc-bL"
FOLDER_JAMS_ID = "192MCefe9vQwYhQcu-uZXekMbgdslTcgC"
FOLDER_ALERTS_ID2 = "1kQfYRJz0-EwY4gcsjTTVBCgK9zO5BAR0"
FOLDER_JAMS_ID2 = "16bblUG7NQmLMZM7BQUGAa3-GZIFYMka0"

# ---------------------------------------------------------
# 6. FUNÇÕES DE COR
# ---------------------------------------------------------
def get_congestion_color(speed_kmh: float) -> str:
    if speed_kmh >= 80:
        return "#2196F3"
    elif speed_kmh >= 60:
        return "#4CAF50"
    elif speed_kmh >= 40:
        return "#8BC34A"
    elif speed_kmh >= 20:
        return "#FF9800"
    elif speed_kmh >= 5:
        return "#F44336"
    return "#7B1FA2"

def get_danger_color(incident_type: str, subtype: str | None = None) -> str:
    leves = {
        "ACIDENTE LEVE",
        "TRÂNSITO MODERADO",
        "PERIGO NA VIA",
        "OBJETO NA VIA",
        "ANIMAL NA VIA",
        "VEÍCULO PARADO",
        "CONDIÇÕES CLIMÁTICAS",
    }

    t = str(incident_type).upper().strip() if incident_type else ""
    s = str(subtype).upper().strip() if subtype else ""
    is_leve = s in leves

    color_map = {
        "ACIDENTE": "#F44336" if not is_leve else "#EF9A9A",
        "VIA FECHADA": "#B71C1C",
        "CONGESTIONAMENTO": "#7B1FA2" if not is_leve else "#CE93D8",
        "PERIGO": "#FF9800" if not is_leve else "#FFCC80",
        "PERIGO CLIMÁTICO": "#29B6F6",
        "OBRAS": "#78909C",
        "ALERTA": "#FDD835",
    }

    subtype_override = {
        "ACIDENTE GRAVE": "#B71C1C",
        "ACIDENTE LEVE": "#EF9A9A",
        "BURACO NA VIA": "#FF9800",
        "OBRAS NA VIA": "#78909C",
        "SEMÁFORO QUEBRADO": "#FDD835",
        "INUNDAÇÃO": "#0288D1",
        "NEBLINA": "#B0BEC5",
        "TRÂNSITO PARADO": "#7B1FA2",
        "TRÂNSITO PESADO": "#F44336",
        "TRÂNSITO MODERADO": "#FF9800",
    }

    if s in subtype_override:
        return subtype_override[s]

    return color_map.get(t, "#90A4AE")

# =========================================================
# BLOCO 2 — CONEXÃO, INGESTÃO E NORMALIZAÇÃO DOS DADOS
# =========================================================

import os

# ---------------------------------------------------------
# 1. CONEXÃO COM GOOGLE DRIVE
# ---------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_drive_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build("drive", "v3", credentials=creds)


# ---------------------------------------------------------
# 2. DESCOBRIR O ARQUIVO .H5 MAIS RECENTE
# ---------------------------------------------------------
def get_latest_h5_id(folder_id: str) -> str | None:
    service = get_drive_service()
    query = f"'{folder_id}' in parents and name contains '.h5' and trashed=false"

    results = service.files().list(
        q=query,
        fields="files(id, name, modifiedTime)",
        orderBy="modifiedTime desc",
        pageSize=20
    ).execute()

    files = results.get("files", [])
    if not files:
        return None

    latest_id = None
    latest_ts = -1

    for file_meta in files:
        match = re.search(r"(\d{8,})", file_meta["name"])
        if match:
            ts = int(match.group(1))
            if ts > latest_ts:
                latest_ts = ts
                latest_id = file_meta["id"]

    return latest_id if latest_id else files[0]["id"]


# ---------------------------------------------------------
# 3. BAIXAR E LER HDF DO DRIVE
# ---------------------------------------------------------
@st.cache_data(ttl=600, show_spinner="📥 Baixando dados do Drive...")
def load_hdf_from_drive(file_id: str) -> pd.DataFrame:
    from googleapiclient.http import MediaIoBaseDownload

    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)

    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    buffer.seek(0)
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".h5") as tmp:
            tmp.write(buffer.getvalue())
            tmp_path = tmp.name

        df = pd.read_hdf(tmp_path, key="s")
        return df

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


# ---------------------------------------------------------
# 4. NORMALIZAR TIMESTAMPS
# ---------------------------------------------------------
def normalize_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    df = df.copy()

    if "pubMillis" in df.columns:
        df["timestamp"] = (
            pd.to_datetime(df["pubMillis"], unit="ms", utc=True)
            .dt.tz_convert("America/Sao_Paulo")
            .dt.tz_localize(None)
        )
    elif "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    else:
        df["timestamp"] = now_foz()

    df["date"] = df["timestamp"].dt.date
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.day_name()

    return df


# ---------------------------------------------------------
# 5. EXTRAÇÃO DE COORDENADAS — HELPERS
# ---------------------------------------------------------
def _parse_dict_like(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return ast.literal_eval(value)
        except Exception:
            return None
    return None


def _extract_lat_lon_from_location(value):
    parsed = _parse_dict_like(value)
    if isinstance(parsed, dict):
        try:
            return float(parsed.get("y")), float(parsed.get("x"))
        except Exception:
            return None, None
    return None, None


# ---------------------------------------------------------
# 6. EXTRAÇÃO DE COORDENADAS — ALERTAS
# ---------------------------------------------------------
def extract_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    df = df.copy()

    if "lat" in df.columns and "lon" in df.columns:
        df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
        df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
        return df

    if "location" in df.columns:
        coords = df["location"].apply(
            lambda x: pd.Series(_extract_lat_lon_from_location(x), index=["lat", "lon"])
        )
        df["lat"] = coords["lat"]
        df["lon"] = coords["lon"]

    if "lat" not in df.columns and "y" in df.columns:
        df["lat"] = pd.to_numeric(df["y"], errors="coerce")

    if "lon" not in df.columns and "x" in df.columns:
        df["lon"] = pd.to_numeric(df["x"], errors="coerce")

    return df


# ---------------------------------------------------------
# 7. EXTRAÇÃO DE COORDENADAS — JAMS
# ---------------------------------------------------------
def _extract_midpoint_from_line(value):
    try:
        points = value if isinstance(value, list) else ast.literal_eval(str(value))
        if not points:
            return None, None
        mid = points[len(points) // 2]
        return float(mid.get("y")), float(mid.get("x"))
    except Exception:
        return None, None


def extract_jams_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    df = df.copy()

    if "lat" in df.columns and "lon" in df.columns:
        df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
        df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
        if df["lat"].notna().any():
            return df

    if "line" in df.columns:
        coords = df["line"].apply(
            lambda x: pd.Series(_extract_midpoint_from_line(x), index=["lat", "lon"])
        )
        df["lat"] = coords["lat"]
        df["lon"] = coords["lon"]
        if df["lat"].notna().any():
            return df

    if "location" in df.columns:
        coords = df["location"].apply(
            lambda x: pd.Series(_extract_lat_lon_from_location(x), index=["lat", "lon"])
        )
        df["lat"] = coords["lat"]
        df["lon"] = coords["lon"]

    if "lat" not in df.columns and "y" in df.columns:
        df["lat"] = pd.to_numeric(df["y"], errors="coerce")

    if "lon" not in df.columns and "x" in df.columns:
        df["lon"] = pd.to_numeric(df["x"], errors="coerce")

    return df


# ---------------------------------------------------------
# 8. NORMALIZAÇÃO DE VELOCIDADE
# ---------------------------------------------------------
def normalize_speed(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    df = df.copy()

    if "speed" in df.columns:
        df["speed"] = pd.to_numeric(df["speed"], errors="coerce")
        return df

    for alt in ["speedKMH", "speedkmh", "speed_kmh", "velocity"]:
        if alt in df.columns:
            df["speed"] = pd.to_numeric(df[alt], errors="coerce") / 3.6
            return df

    df["speed"] = float("nan")
    return df


# ---------------------------------------------------------
# 9. TRADUÇÕES WAZE → PT-BR
# ---------------------------------------------------------
TYPE_MAP = {
    "ROAD_CLOSED": "VIA FECHADA",
    "ROAD_CLOSED_CONSTRUCTION": "VIA FECHADA",
    "ROAD_CLOSED_EVENT": "VIA FECHADA",
    "HAZARD": "PERIGO",
    "ACCIDENT": "ACIDENTE",
    "JAM": "CONGESTIONAMENTO",
    "WEATHERHAZARD": "PERIGO CLIMÁTICO",
}

SUBTYPE_MAP = {
    "ROAD_CLOSED_CONSTRUCTION": "OBRAS",
    "ROAD_CLOSED_EVENT": "EVENTO",
    "HAZARD_ON_ROAD": "PERIGO NA VIA",
    "HAZARD_ON_ROAD_POT_HOLE": "BURACO NA VIA",
    "HAZARD_ON_ROAD_ROAD_KILL": "ANIMAL NA VIA",
    "HAZARD_ON_ROAD_CAR_STOPPED": "VEÍCULO PARADO NA VIA",
    "HAZARD_ON_ROAD_CONSTRUCTION": "OBRAS NA VIA",
    "HAZARD_ON_ROAD_OBJECT": "OBJETO NA VIA",
    "HAZARD_ON_ROAD_TRAFFIC_LIGHT_FAULT": "SEMÁFORO QUEBRADO",
    "HAZARD_ON_ROAD_ICE": "PISTA COM GELO",
    "HAZARD_ON_ROAD_LANE_CLOSED": "FAIXA INTERDITADA",
    "HAZARD_ON_SHOULDER": "PERIGO NO ACOSTAMENTO",
    "HAZARD_ON_SHOULDER_CAR_STOPPED": "VEÍCULO PARADO NO ACOSTAMENTO",
    "HAZARD_ON_SHOULDER_ANIMALS": "ANIMAIS NO ACOSTAMENTO",
    "HAZARD_ON_SHOULDER_MISSING_SIGN": "SINALIZAÇÃO AUSENTE",
    "HAZARD_WEATHER": "CONDIÇÕES CLIMÁTICAS",
    "HAZARD_WEATHER_FOG": "NEBLINA",
    "HAZARD_WEATHER_HAIL": "GRANIZO",
    "HAZARD_WEATHER_HEAVY_RAIN": "CHUVA FORTE",
    "HAZARD_WEATHER_FLOOD": "INUNDAÇÃO",
    "HAZARD_WEATHER_MONSOON": "TEMPORAL",
    "HAZARD_WEATHER_TORNADO": "TORNADO",
    "HAZARD_WEATHER_HEAT_WAVE": "ONDA DE CALOR",
    "HAZARD_WEATHER_HEAVY_SNOW": "NEVE INTENSA",
    "HAZARD_WEATHER_FREEZING_RAIN": "CHUVA COM GELO",
    "ACCIDENT_MAJOR": "ACIDENTE GRAVE",
    "ACCIDENT_MINOR": "ACIDENTE LEVE",
    "JAM_HEAVY_TRAFFIC": "TRÂNSITO PESADO",
    "JAM_MODERATE_TRAFFIC": "TRÂNSITO MODERADO",
    "JAM_STAND_STILL_TRAFFIC": "TRÂNSITO PARADO",
    "JAM_LIGHT_TRAFFIC": "TRÂNSITO LEVE",
}

def translate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    df = df.copy()

    if "type" in df.columns:
        df["type"] = df["type"].replace(TYPE_MAP)

    if "subtype" in df.columns:
        df["subtype"] = df["subtype"].replace(SUBTYPE_MAP)

        known_values = set(SUBTYPE_MAP.values())
        mask = df["subtype"].notna() & ~df["subtype"].isin(known_values)

        df.loc[mask, "subtype"] = (
            df.loc[mask, "subtype"]
            .astype(str)
            .str.replace(
                r"^(HAZARD_ON_ROAD_|HAZARD_ON_SHOULDER_|HAZARD_WEATHER_|HAZARD_|ACCIDENT_|JAM_|ROAD_CLOSED_)",
                "",
                regex=True
            )
            .str.replace("_", " ", regex=False)
            .str.title()
        )

    return df


# ---------------------------------------------------------
# 10. PIPELINE PRINCIPAL
# ---------------------------------------------------------
@st.cache_data(ttl=600, show_spinner="🔄 Carregando dados do Google Drive...")
def load_all_data():
    alerts_id = get_latest_h5_id(FOLDER_ALERTS_ID)
    alerts_id2 = get_latest_h5_id(FOLDER_ALERTS_ID2)
    jams_id = get_latest_h5_id(FOLDER_JAMS_ID)
    jams_id2 = get_latest_h5_id(FOLDER_JAMS_ID2)

    # Alertas
    frames_alerts = []
    if alerts_id:
        frames_alerts.append(load_hdf_from_drive(alerts_id))
    if alerts_id2:
        frames_alerts.append(load_hdf_from_drive(alerts_id2))

    if frames_alerts:
        df_alerts = pd.concat(frames_alerts, ignore_index=True)
        dedup_cols = ["uuid"] if "uuid" in df_alerts.columns else ["pubMillis", "street"]
        df_alerts = df_alerts.drop_duplicates(subset=dedup_cols)
    else:
        df_alerts = pd.DataFrame()

    # Jams
    frames_jams = []
    if jams_id:
        frames_jams.append(load_hdf_from_drive(jams_id))
    if jams_id2:
        frames_jams.append(load_hdf_from_drive(jams_id2))

    if frames_jams:
        df_jams = pd.concat(frames_jams, ignore_index=True)
        dedup_cols = ["uuid"] if "uuid" in df_jams.columns else ["pubMillis", "street"]
        df_jams = df_jams.drop_duplicates(subset=dedup_cols)
    else:
        df_jams = pd.DataFrame()

    # Enriquecimento alertas
    if not df_alerts.empty:
        df_alerts = normalize_timestamps(df_alerts)
        df_alerts = extract_coordinates(df_alerts)
        df_alerts = translate_dataframe(df_alerts)

        if "street" not in df_alerts.columns:
            df_alerts["street"] = "N/A"

    # Enriquecimento jams
    if not df_jams.empty:
        df_jams = normalize_timestamps(df_jams)
        df_jams = extract_jams_coordinates(df_jams)
        df_jams = normalize_speed(df_jams)

        if "street" not in df_jams.columns:
            df_jams["street"] = "Via"

    return df_alerts, df_jams

# =========================================================
# BLOCO 3 — MAPAS E VISUALIZAÇÕES GEOESPACIAIS
# =========================================================

# ---------------------------------------------------------
# 1. BOUNDING BOX DE FOZ DO IGUAÇU
# ---------------------------------------------------------
LAT_MIN, LAT_MAX = -25.70, -25.40
LON_MIN, LON_MAX = -54.75, -54.45

def filter_bbox_foz(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    df = df.copy()

    if "lat" not in df.columns or "lon" not in df.columns:
        return pd.DataFrame()

    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    return df[
        df["lat"].between(LAT_MIN, LAT_MAX) &
        df["lon"].between(LON_MIN, LON_MAX)
    ].copy()


# ---------------------------------------------------------
# 2. MAPA BASE COM BÚSSOLA
# ---------------------------------------------------------
def create_folium_map_with_compass(lat: float, lon: float, zoom_level: int = 13) -> folium.Map:
    m = folium.Map(
        location=[lat, lon],
        zoom_start=zoom_level,
        tiles="OpenStreetMap",
        max_bounds=True,
        control_scale=False
    )

    plugins.MousePosition(
        position="topright",
        separator=" | ",
        prefix="Lat/Lon: ",
        num_digits=5
    ).add_to(m)

    plugins.Fullscreen(
        position="topleft",
        title="Expandir mapa",
        title_cancel="Sair da tela cheia",
        force_separate_button=True
    ).add_to(m)

    scale_js = """
    <script>
    document.addEventListener("DOMContentLoaded", function() {
        setTimeout(function() {
            var maps = Object.values(window).filter(function(v) {
                return v && v._leaflet_id && typeof v.addControl === 'function';
            });

            maps.forEach(function(map) {
                L.control.scale({
                    position: 'bottomleft',
                    metric: true,
                    imperial: false,
                    maxWidth: 120
                }).addTo(map);

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
        <text x="6" y="30" text-anchor="middle" font-size="8"
              font-family="Arial" fill="#888">O</text>
      </svg>
    </div>
    """
    m.get_root().html.add_child(folium.Element(compass_html))

    folium.LayerControl(position="topright", collapsed=True).add_to(m)
    return m


# ---------------------------------------------------------
# 3. HELPERS DE SEGURANÇA / SERIALIZAÇÃO
# ---------------------------------------------------------
def _load_json_df(df_json: str) -> pd.DataFrame:
    try:
        df = pd.read_json(io.StringIO(df_json))
        return df if df is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def _safe_time_label(value) -> str:
    try:
        if pd.notna(value):
            return pd.to_datetime(value).strftime("%H:%M")
    except Exception:
        pass
    return "--"


# ---------------------------------------------------------
# 4. MAPA DE INCIDENTES
# ---------------------------------------------------------
def generate_incidents_map(df_json: str) -> folium.Map | None:
    df = _load_json_df(df_json)
    if df.empty:
        return None

    if ("lat" not in df.columns or df["lat"].isna().all()) and "location" in df.columns:
        def _gy(x):
            try:
                parsed = ast.literal_eval(x) if isinstance(x, str) else x
                return float(parsed.get("y"))
            except Exception:
                return None

        def _gx(x):
            try:
                parsed = ast.literal_eval(x) if isinstance(x, str) else x
                return float(parsed.get("x"))
            except Exception:
                return None

        df["lat"] = df["location"].apply(_gy)
        df["lon"] = df["location"].apply(_gx)

    if "lat" not in df.columns and "y" in df.columns:
        df["lat"] = pd.to_numeric(df["y"], errors="coerce")
    if "lon" not in df.columns and "x" in df.columns:
        df["lon"] = pd.to_numeric(df["x"], errors="coerce")

    if "lat" not in df.columns or "lon" not in df.columns:
        return None

    df_map = filter_bbox_foz(df.dropna(subset=["lat", "lon"])).head(50)
    if df_map.empty:
        return None

    m = create_folium_map_with_compass(df_map["lat"].mean(), df_map["lon"].mean())

    for _, row in df_map.iterrows():
        try:
            tipo = str(row.get("type", "?"))
            subtipo = str(row.get("subtype", ""))
            rua = str(row.get("street", "N/A"))
            color = get_danger_color(tipo, row.get("subtype"))
            ts = _safe_time_label(row.get("timestamp"))
            lat_val = float(row["lat"])
            lon_val = float(row["lon"])

            popup_html = f"""
            <div style='min-width:200px;font-family:Arial,sans-serif;'>
                <b style='color:{color};font-size:16px;'>🚨 {tipo}</b><br>
                <b>{subtipo}</b><br>
                🛣️ <i>{rua}</i><br>
                🕒 {ts}<br>
                📍 {lat_val:.4f}, {lon_val:.4f}
            </div>
            """

            folium.CircleMarker(
                location=[lat_val, lon_val],
                radius=9,
                popup=folium.Popup(popup_html, max_width=260),
                tooltip=f"{tipo}: {rua}",
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.8,
                weight=2
            ).add_to(m)

        except Exception:
            continue

    return m


# ---------------------------------------------------------
# 5. MAPA DE CONGESTIONAMENTOS
# ---------------------------------------------------------
def generate_jams_map(df_json: str) -> folium.Map | None:
    df = _load_json_df(df_json)
    if df.empty:
        return None

    if ("lat" not in df.columns or df["lat"].isna().all()) and "line" in df.columns:
        def _midpoint(val):
            try:
                pts = val if isinstance(val, list) else ast.literal_eval(str(val))
                if not pts:
                    return None, None
                mid = pts[len(pts) // 2]
                return float(mid.get("y")), float(mid.get("x"))
            except Exception:
                return None, None

        coords = df["line"].apply(lambda x: pd.Series(_midpoint(x), index=["lat", "lon"]))
        df["lat"] = coords["lat"]
        df["lon"] = coords["lon"]

    if ("lat" not in df.columns or df["lat"].isna().all()) and "location" in df.columns:
        def _get_y(x):
            try:
                parsed = ast.literal_eval(x) if isinstance(x, str) else x
                return float(parsed.get("y"))
            except Exception:
                return None

        def _get_x(x):
            try:
                parsed = ast.literal_eval(x) if isinstance(x, str) else x
                return float(parsed.get("x"))
            except Exception:
                return None

        df["lat"] = df["location"].apply(_get_y)
        df["lon"] = df["location"].apply(_get_x)

    if "lat" not in df.columns and "y" in df.columns:
        df["lat"] = pd.to_numeric(df["y"], errors="coerce")
    if "lon" not in df.columns and "x" in df.columns:
        df["lon"] = pd.to_numeric(df["x"], errors="coerce")

    if "speed" not in df.columns:
        for alt in ["speedKMH", "speedkmh", "speed_kmh", "velocity"]:
            if alt in df.columns:
                df["speed"] = pd.to_numeric(df[alt], errors="coerce") / 3.6
                break
        else:
            df["speed"] = float("nan")

    if "lat" not in df.columns or "lon" not in df.columns:
        return None

    df_valid = filter_bbox_foz(df.dropna(subset=["lat", "lon"])).head(40)
    if df_valid.empty:
        return None

    m = create_folium_map_with_compass(df_valid["lat"].mean(), df_valid["lon"].mean())

    for _, row in df_valid.iterrows():
        try:
            speed_raw = row.get("speed", float("nan"))
            speed_kmh = float(speed_raw) * 3.6 if pd.notna(speed_raw) else 0.0
            color = get_congestion_color(speed_kmh)
            rua = str(row.get("street", "Via"))
            ts = _safe_time_label(row.get("timestamp"))
            lat_val = float(row["lat"])
            lon_val = float(row["lon"])
            spd_str = f"{speed_kmh:.0f} km/h"

            popup_html = f"""
            <div style='min-width:180px;font-family:Arial,sans-serif;'>
                <b style='color:{color}'>🚗 {spd_str}</b><br>
                🛣️ <i>{rua}</i><br>
                🕒 {ts}
            </div>
            """

            folium.CircleMarker(
                location=[lat_val, lon_val],
                radius=7,
                popup=folium.Popup(popup_html, max_width=220),
                tooltip=f"{spd_str} — {rua}",
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=2
            ).add_to(m)

        except Exception:
            continue

    return m


# ---------------------------------------------------------
# 6. MAPA DE CALOR
# ---------------------------------------------------------
def generate_heatmap(df_json: str) -> folium.Map | None:
    df = _load_json_df(df_json)
    if df.empty:
        return None

    if "lat" not in df.columns and "y" in df.columns:
        df["lat"] = pd.to_numeric(df["y"], errors="coerce")
    if "lon" not in df.columns and "x" in df.columns:
        df["lon"] = pd.to_numeric(df["x"], errors="coerce")

    if "lat" not in df.columns or "lon" not in df.columns:
        return None

    df_map = filter_bbox_foz(df.dropna(subset=["lat", "lon"]))
    if df_map.empty:
        return None

    m = create_folium_map_with_compass(df_map["lat"].mean(), df_map["lon"].mean())

    heat_data = [[row["lat"], row["lon"]] for _, row in df_map.iterrows()]
    plugins.HeatMap(
        heat_data,
        radius=15,
        blur=10,
        min_opacity=0.35
    ).add_to(m)

    return m

# =========================================================
# BLOCO 4 — SIDEBAR, CARGA OPERACIONAL E FILTROS
# =========================================================

# ---------------------------------------------------------
# 1. HORA LOCAL E STATUS DA SESSÃO
# ---------------------------------------------------------
hora_foz_atual = now_foz()

st.sidebar.header("⚙️ Controles")
st.sidebar.markdown("### ⏰ Status da Sessão")
st.sidebar.markdown(
    f"🕐 **Hora atual (Foz):** `{hora_foz_atual.strftime('%d/%m/%Y %H:%M:%S')}`"
)
st.sidebar.metric(
    "⏳ Tempo online",
    f"{tempo_total // 3600}h:{(tempo_total % 3600) // 60:02d}m"
)
st.sidebar.metric(
    "⏳ Próximo ciclo",
    f"{minutos_restantes}:{segundos_restantes:02d}"
)
st.sidebar.metric(
    "🔄 Atualizações",
    st.session_state.manual_refreshes
)

if st.sidebar.button(
    "🔄 ATUALIZAR DADOS AGORA",
    width="stretch",
    type="primary"
):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.session_state.manual_refreshes += 1
    st.rerun()

st.sidebar.divider()


# ---------------------------------------------------------
# 2. CARREGAMENTO PRINCIPAL DE DADOS
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# 3. GARANTIA DE COLUNAS TEMPORAIS
# ---------------------------------------------------------
for df_ref in [df_alerts_raw, df_jams_raw]:
    if not df_ref.empty and "timestamp" in df_ref.columns:
        if "hour" not in df_ref.columns:
            df_ref["hour"] = pd.to_datetime(df_ref["timestamp"], errors="coerce").dt.hour
        if "date" not in df_ref.columns:
            df_ref["date"] = pd.to_datetime(df_ref["timestamp"], errors="coerce").dt.date


# ---------------------------------------------------------
# 4. HELPERS DE FILTRO
# ---------------------------------------------------------
def apply_base_time_filter(df: pd.DataFrame, selected_date, hora_range: tuple[int, int]) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    if "date" not in df.columns or "hour" not in df.columns:
        return pd.DataFrame()

    return df[
        (df["date"] == selected_date) &
        (df["hour"].between(hora_range[0], hora_range[1]))
    ].copy()


def clean_unique_values(series: pd.Series, invalid_values=None):
    if series is None:
        return []

    invalid_values = set(invalid_values or [])
    values = (
        series.dropna()
        .astype(str)
        .str.strip()
    )
    values = values[~values.isin(invalid_values)]
    return sorted(values.unique().tolist())


def classify_traffic_status(media_vel_kmh: float) -> str:
    if media_vel_kmh < 20:
        return "🔴 Crítico"
    elif media_vel_kmh < 40:
        return "🟠 Lento"
    elif media_vel_kmh < 60:
        return "🟡 Moderado"
    return "🟢 Fluindo"


# ---------------------------------------------------------
# 5. FILTROS DA SIDEBAR
# ---------------------------------------------------------
# ---------------------------------------------------------
# 5. FILTROS DA SIDEBAR
# ---------------------------------------------------------
st.sidebar.subheader("🔍 Filtros")
today_foz = nowfoz().date()

all_dates = set()
if not dfalertsraw.empty and "date" in dfalertsraw.columns:
    all_dates.update(pd.to_datetime(dfalertsraw["date"]).dt.date.unique())
if not dfjamsraw.empty and "date" in dfjamsraw.columns:
    all_dates.update(pd.to_datetime(dfjamsraw["date"]).dt.date.unique())

if all_dates:
    min_date = min(all_dates)
    max_date = max(all_dates)
    default_date = today_foz if today_foz in all_dates else max_date
else:
    min_date = max_date = default_date = today_foz

selecteddate = st.sidebar.date_input(
    "📅 Data",
    value=default_date,
    min_value=min_date,
    max_value=max(max_date, today_foz),
)

horarange = st.sidebar.slider(
    "🕐 Horário",
    min_value=0,
    max_value=23,
    value=(0, 23)
)

# ---------------------------------------------------------
# 6. BASES INTERMEDIÁRIAS POR DATA/HORA
# ---------------------------------------------------------
alertsdatebase = applybasetimefilter(dfalertsraw, selecteddate, horarange)
jamsdatebase = applybasetimefilter(dfjamsraw, selecteddate, horarange)

# ---------------------------------------------------------
# 7. FILTROS DE ALERTAS
# ---------------------------------------------------------
tiposnadata = (
    cleanuniquevalues(alertsdatebase["type"])
    if not alertsdatebase.empty and "type" in alertsdatebase.columns
    else []
)

filtrotipo = st.sidebar.multiselect(
    "🚨 Tipo",
    options=tiposnadata,
    default=tiposnadata,
)

naturezabase = alertsdatebase.copy()
if filtrotipo and "type" in naturezabase.columns:
    naturezabase = naturezabase[naturezabase["type"].isin(filtrotipo)]

naturezasnadata = (
    cleanuniquevalues(naturezabase["subtype"], invalidvalues=["nan", ""])
    if not naturezabase.empty and "subtype" in naturezabase.columns
    else []
)

filtronatureza = st.sidebar.multiselect(
    "🔎 Natureza",
    options=naturezasnadata,
    default=naturezasnadata,
)

ruabase = naturezabase.copy()
if filtronatureza and "subtype" in ruabase.columns:
    ruabase = ruabase[ruabase["subtype"].isin(filtronatureza)]

ruasnadata = (
    cleanuniquevalues(ruabase["street"], invalidvalues=["NA", "nan", "", "N/A"])
    if not ruabase.empty and "street" in ruabase.columns
    else []
)

ruaescolhida = st.sidebar.selectbox(
    "🛣️ Rua",
    options=["(Todas)"] + ruasnadata,
    index=0,
)

filtrorua = "" if ruaescolhida == "(Todas)" else ruaescolhida

# ---------------------------------------------------------
# 8. FILTRO DE VELOCIDADE DOS JAMS
# ---------------------------------------------------------
velmindata, velmaxdata = 0.0, 120.0

if not jamsdatebase.empty and "speed" in jamsdatebase.columns:
    speedsnadata = jamsdatebase["speed"].dropna() * 3.6
    if not speedsnadata.empty:
        velmindata = max(0.0, float(speedsnadata.min()))
        velmaxdata = max(5.0, float(speedsnadata.max()))

velrange = st.sidebar.slider(
    "🚗 Velocidade (km/h)",
    min_value=0.0,
    max_value=max(120.0, velmaxdata),
    value=(velmindata, max(velmindata, min(120.0, velmaxdata))),
    step=5.0,
)

# ---------------------------------------------------------
# 9. RESUMO LATERAL DE CONGESTIONAMENTOS
# ---------------------------------------------------------
if (
    not jamsdatebase.empty
    and "speed" in jamsdatebase.columns
    and jamsdatebase["speed"].notna().any()
):
    mediavel = jamsdatebase["speed"].mean() * 3.6
    totaljams = len(jamsdatebase)
    statuslabel = classifytrafficstatus(mediavel)

    st.sidebar.markdown("---")
    st.sidebar.markdown("**📊 Congestionamentos em** " + selecteddate.strftime("%d/%m"))
    st.sidebar.metric("Vel. Média", f"{mediavel:.1f} km/h", delta=statuslabel)
    st.sidebar.metric("Total de Jams", totaljams)
else:
    st.sidebar.info(
        f"Sem dados de congestionamento em {selecteddate.strftime('%d/%m')}."
    )

# ---------------------------------------------------------
# 10. APLICAÇÃO GLOBAL DOS FILTROS
# ---------------------------------------------------------
dffiltered = applybasetimefilter(dfalertsraw, selecteddate, horarange)

if not dffiltered.empty:
    if filtrotipo and "type" in dffiltered.columns:
        dffiltered = dffiltered[dffiltered["type"].isin(filtrotipo)]

    if filtronatureza and "subtype" in dffiltered.columns:
        dffiltered = dffiltered[dffiltered["subtype"].isin(filtronatureza)]

    if filtrorua and "street" in dffiltered.columns:
        dffiltered = dffiltered[dffiltered["street"] == filtrorua]

dfjamsfiltered = applybasetimefilter(dfjamsraw, selecteddate, horarange)

if not dfjamsfiltered.empty and "speed" in dfjamsfiltered.columns:
    dfjamsfiltered = dfjamsfiltered[
        (dfjamsfiltered["speed"].fillna(0) * 3.6).between(velrange[0], velrange[1])
    ]

# ---------------------------------------------------------
# 11. BASES MESTRES DO DASHBOARD
# ---------------------------------------------------------
basealertasdashboard = dffiltered.copy()
basejamsdashboard = dfjamsfiltered.copy()
# =========================================================
# BLOCO 5 — CABEÇALHO, RESUMO, KPIs E INDICADORES
# =========================================================

# ---------------------------------------------------------
# 1. HELPERS DE CLASSIFICAÇÃO
# ---------------------------------------------------------
def classify_risk_level(total_incidentes: int):
    if total_incidentes >= 15:
        return "Crítico", "🔴", "Volume muito alto de incidentes no período filtrado."
    elif total_incidentes >= 10:
        return "Alto", "🟠", "Quantidade elevada de ocorrências; atenção operacional recomendada."
    elif total_incidentes >= 5:
        return "Moderado", "🟡", "Ocorrências acima do nível de normalidade para o recorte atual."
    return "Baixo", "🟢", "Baixa pressão operacional no período filtrado."


def classify_flow_status(vmedia_kmh: float):
    if vmedia_kmh < 20:
        return "Travado", "🔴", "Fluxo muito comprometido, com forte retenção nas vias."
    elif vmedia_kmh < 40:
        return "Lento", "🟠", "Tráfego com perda relevante de fluidez."
    elif vmedia_kmh < 60:
        return "Moderado", "🟡", "Fluxo estável, mas com redução perceptível de velocidade."
    return "Fluindo", "🟢", "Boas condições de circulação no recorte selecionado."


def classify_road_status(total_incidentes: int) -> str:
    if total_incidentes >= 15:
        return "🚫 Crítico"
    elif total_incidentes >= 5:
        return "⚠️ Moderado"
    return "✅ Normal"


def build_selection_label(selected_values, total_available, singular_name, plural_name):
    if not selected_values or len(selected_values) == total_available:
        return "Todos" if plural_name == "tipos" else "Todas"
    if len(selected_values) <= 2:
        return ", ".join(selected_values)
    return f"{len(selected_values)} {plural_name}"


# ---------------------------------------------------------
# 2. CABEÇALHO PRINCIPAL
# ---------------------------------------------------------
st.markdown(f"""
<div style="
    background: linear-gradient(135deg,
        rgba(30,41,59,0.95) 0%,
        rgba(15,23,42,0.98) 50%,
        rgba(17,24,39,0.95) 100%);
    border: 1px solid rgba(59,130,246,0.2);
    border-radius: 20px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    backdrop-filter: blur(20px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05);
    position: relative;
    overflow: hidden;
">
  <div style="
      position:absolute; top:-60px; right:-60px;
      width:200px; height:200px;
      background: radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%);
      pointer-events:none;
  "></div>
  <div style="
      display:inline-flex; align-items:center; gap:6px;
      background: rgba(34,197,94,0.12);
      border: 1px solid rgba(34,197,94,0.25);
      border-radius: 20px;
      padding: 4px 12px;
      font-size: 0.72rem;
      font-weight: 600;
      color: #4ade80;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      margin-bottom: 0.75rem;
  ">
      <span style="width:7px;height:7px;background:#4ade80;border-radius:50%;
                   animation:pulse 2s infinite;display:inline-block;"></span>
      SISTEMA ATIVO — DADOS REAIS
  </div>
  <h1 style="
      margin: 0 0 0.25rem 0;
      font-size: clamp(1.4rem, 3vw, 2rem);
      font-weight: 800;
      color: #f1f5f9;
      letter-spacing: -0.5px;
      line-height: 1.2;
  ">
      🚗 Monitoramento de Tráfego
      <span style="
          background: linear-gradient(135deg, #3b82f6, #60a5fa);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
      "> — Foz do Iguaçu</span>
  </h1>
  <p style="
      margin: 0.4rem 0 0 0;
      color: #64748b;
      font-size: 0.88rem;
      font-weight: 400;
  ">
      📅 {selected_date.strftime('%d/%m/%Y')}
      &nbsp;·&nbsp;
      🕐 Hora local: <strong style="color:#94a3b8;">{hora_foz_atual.strftime('%H:%M:%S')}</strong>
      &nbsp;·&nbsp;
      🔄 Atualização automática a cada 10 minutos
  </p>
  <div style="
      margin-top: 1rem;
      padding-top: 0.75rem;
      border-top: 1px solid rgba(255,255,255,0.06);
      font-size: 0.72rem;
      color: #475569;
      display: flex;
      gap: 1.5rem;
      flex-wrap: wrap;
      align-items: center;
  ">
      <span>🔬 <strong style="color:#64748b;">GPMME</strong> — Grupo de Pesquisa em Mobilidade e Matriz Energética</span>
      <span>🧪 <strong style="color:#64748b;">LAGGRA</strong> — Lab. de Geologia, Geotecnia e Recuperação Ambiental</span>
      <span>💻 <strong style="color:#64748b;">LACA</strong> — Laboratório deComputação Aplicada</span>
      <span style="margin-left:auto; color:#334155;">UNILA · FOZ DO IGUAÇU</span>
  </div>
</div>
<style>
@keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.4; }}
}}
</style>
""", unsafe_allow_html=True)



# ---------------------------------------------------------
# 3. SOBRE O DASHBOARD
# ---------------------------------------------------------
st.markdown("""
<div style="
    background:#FFFFFF;
    border:1px solid #E2E8F0;
    border-radius:12px;
    padding:16px 18px;
    margin-bottom:16px;
    box-shadow:0 1px 4px rgba(15,23,42,0.04);
">
    <div style="
        font-size:15px;
        font-weight:700;
        color:#0F172A;
        margin-bottom:6px;
    ">
        Sobre este dashboard
    </div>
    <div style="
        font-size:14px;
        line-height:1.7;
        color:#475569;
    ">
        Este dashboard apresenta o monitoramento de incidentes viários e congestionamentos em Foz do Iguaçu com base em dados do Waze.
        Os painéis reúnem mapas, filtros e indicadores para apoiar análises espaciais, temporais e históricas da mobilidade urbana.
        Os dados podem ser explorados por tipo de ocorrência, natureza, via, horário e intensidade do tráfego.
    </div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# 4. RESUMO DOS FILTROS
# ---------------------------------------------------------
label_tipo = build_selection_label(
    filtro_tipo,
    len(tipos_na_data),
    "tipo",
    "tipos"
)

label_natureza = build_selection_label(
    filtro_natureza,
    len(naturezas_na_data),
    "natureza",
    "naturezas"
)

col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)

col_f1.metric("📅 Data", selected_date.strftime("%d/%m/%Y"))
col_f2.metric("🚨 Tipo", label_tipo)
col_f3.metric("🔍 Natureza", label_natureza)
col_f4.metric("🛣️ Rua", filtro_rua if filtro_rua else "Todas")
col_f5.metric("⏰ Horário", f"{hora_range[0]:02d}h – {hora_range[1]:02d}h")

st.caption(
    f"🔍 Filtros ativos → {len(df_filtered)} incidente(s) exibidos em "
    f"{selected_date.strftime('%d/%m/%Y')} | Congestionamentos: {len(df_jams_filtered)}"
)

st.markdown("---")


# ---------------------------------------------------------
# 5. KPIs
# ---------------------------------------------------------
st.subheader("📊 Resumo Estatístico")

incidentes_dia = len(df_filtered)
acidentes = (
    len(df_filtered[df_filtered["type"] == "ACIDENTE"])
    if not df_filtered.empty and "type" in df_filtered.columns
    else 0
)

vmedia_kmh = (
    df_jams_filtered["speed"].mean() * 3.6
    if not df_jams_filtered.empty
    and "speed" in df_jams_filtered.columns
    and df_jams_filtered["speed"].notna().any()
    else 0
)

status_via = classify_road_status(incidentes_dia)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Total Alertas", incidentes_dia)
kpi2.metric("Acidentes", acidentes)
kpi3.metric("Vel. Média", f"{vmedia_kmh:.1f} km/h")
kpi4.metric("Status da Via", status_via)

st.markdown("---")


# ---------------------------------------------------------
# 6. INDICADORES DE GRAVIDADE
# ---------------------------------------------------------
st.subheader("📈 Indicadores de Gravidade")

nivel_risco, emoji_risco, desc_risco = classify_risk_level(incidentes_dia)
status_fluxo, emoji_fluxo, desc_fluxo = classify_flow_status(vmedia_kmh)

col_grav, col_vel = st.columns(2)

with col_grav:
    with st.container(border=True):
        st.markdown(f"### {emoji_risco} Risco operacional")
        st.metric("Classificação", nivel_risco)
        st.metric("Incidentes no período", incidentes_dia)
        st.caption(desc_risco)
        st.write(f"🚨 Acidentes: {acidentes}")
        st.write(f"📍 Status geral: {status_via}")
        st.caption("Faixas: 0–4 = Baixo · 5–9 = Moderado · 10–14 = Alto · 15+ = Crítico")

with col_vel:
    with st.container(border=True):
        st.markdown(f"### {emoji_fluxo} Condição do tráfego")
        st.metric("Classificação", status_fluxo)
        st.metric("Velocidade média", f"{vmedia_kmh:.1f} km/h")
        st.caption(desc_fluxo)
        st.write(f"🚗 Média observada: {vmedia_kmh:.1f} km/h")
        st.write(f"📍 Total de jams: {len(df_jams_filtered)}")
        st.caption("Faixas: <20 = Travado · 20–39 = Lento · 40–59 = Moderado · 60+ = Fluindo")

st.caption(
    "Os indicadores acima resumem o comportamento do período filtrado: "
    "o risco operacional considera o volume de incidentes, enquanto a condição "
    "do tráfego é baseada na velocidade média observada nos congestionamentos."
)

st.markdown("---")
# =========================================================
# BLOCO 6 — VISUALIZAÇÕES PRINCIPAIS
# =========================================================

st.subheader("🗺️ Visualizações")
tab_inc, tab_jams, tab_calor, tab_graficos, tab_dados = st.tabs(
    ["Incidentes", "Congestionamentos", "Mapa de Calor", "Gráficos", "Dados Detalhados"]
)

# ---------------------------------------------------------
# ABA 1 — INCIDENTES
# ---------------------------------------------------------
with tab_inc:
    st.caption("📍 Centro: -25.54, -54.58 · Norte ↑ · Clique nos pontos para detalhes")

    if not df_filtered.empty:
        m_inc = generate_incidents_map(df_filtered.to_json(date_format="iso"))

        if m_inc:
            st_folium(m_inc, width="100%", height=500, key=f"mapa_inc_{len(df_filtered)}")

            st.markdown("""
            | Cor | Tipo / Natureza |
            |---|---|
            | 🔴 | Acidente grave / Alta gravidade |
            | 🩷 | Acidente leve / Baixa gravidade |
            | 🟥 | Via fechada / Obras / Bloqueio total |
            | 🟧 | Perigo / Buraco na via / Risco moderado |
            | 🟨 | Alerta / Semáforo / Atenção |
            | 🟦 | Perigo climático / Condições adversas |
            | 🟪 | Congestionamento / Trânsito parado |
            """)
        else:
            st.info("Nenhum incidente dentro da área de Foz do Iguaçu.")
    else:
        st.info("Nenhum incidente com os filtros aplicados.")


# ---------------------------------------------------------
# ABA 2 — CONGESTIONAMENTOS
# ---------------------------------------------------------
with tab_jams:
    st.caption("🚦 Escala métrica · Livre → Parado")

    if not df_jams_filtered.empty:
        m_jam = generate_jams_map(df_jams_filtered.to_json(date_format="iso"))

        if m_jam:
            st_folium(m_jam, width="100%", height=500, key=f"mapa_jam_{len(df_jams_filtered)}")

            st.markdown("""
            | Cor | Velocidade | Status |
            |---|---:|---|
            | 🔵 | 80+ km/h | Livre / Fluindo |
            | 🟢 | 60–80 km/h | Bom |
            | 🟡 | 40–60 km/h | Moderado |
            | 🟠 | 20–40 km/h | Lento |
            | 🔴 | 5–20 km/h | Muito lento |
            | 🟣 | <5 km/h | Parado / Travado |
            """)
        else:
            st.warning("Nenhum congestionamento na área filtrada.")

        cols_diag = [c for c in ["lat", "lon", "line", "speed", "street"] if c in df_jams_filtered.columns]
        if cols_diag:
            st.caption("Amostra dos dados de congestionamentos")
            st.dataframe(df_jams_filtered[cols_diag].head(5), width="stretch")
    else:
        st.info("Nenhum congestionamento para exibir.")


# ---------------------------------------------------------
# ABA 3 — MAPA DE CALOR
# ---------------------------------------------------------
with tab_calor:
    st.subheader("🔥 Zonas de Concentração de Incidentes")

    if not df_filtered.empty:
        df_heat = df_filtered.copy()

        if {"lat", "lon"}.issubset(df_heat.columns):
            df_heat = df_heat.dropna(subset=["lat", "lon"])
            df_heat = df_heat[
                df_heat["lat"].between(LAT_MIN, LAT_MAX) &
                df_heat["lon"].between(LON_MIN, LON_MAX)
            ]

            if not df_heat.empty:
                m_heat = folium.Map(
                    location=[df_heat["lat"].mean(), df_heat["lon"].mean()],
                    zoom_start=13,
                    tiles="OpenStreetMap"
                )

                heat_data = [[row["lat"], row["lon"]] for _, row in df_heat.iterrows()]
                plugins.HeatMap(
                    heat_data,
                    radius=20,
                    blur=15,
                    min_opacity=0.35,
                    gradient={
                        0.2: "#ffffb2",
                        0.4: "#fecc5c",
                        0.6: "#fd8d3c",
                        0.8: "#f03b20",
                        1.0: "#bd0026",
                    }
                ).add_to(m_heat)

                st_folium(m_heat, width="100%", height=500, key=f"mapa_heat_{len(df_heat)}")

                st.markdown("""
                | Cor | Concentração |
                |---|---|
                | 🟨 | Baixa — poucos registros |
                | 🟧 | Média — atenção |
                | 🟥 | Alta — ponto crítico |
                | 🟫 | Crítica — intervenção prioritária |
                """)

                tipos_no_mapa = df_heat["type"].value_counts().reset_index()
                tipos_no_mapa.columns = ["Tipo", "Qtd"]
                st.dataframe(tipos_no_mapa, hide_index=True, width="stretch")
            else:
                st.info("Nenhum ponto dentro da área de Foz do Iguaçu.")
        else:
            st.info("Sem coordenadas válidas para gerar o mapa de calor.")
    else:
        st.info("Sem dados suficientes para mapa de calor.")


# ---------------------------------------------------------
# ABA 4 — GRÁFICOS
# ---------------------------------------------------------
with tab_graficos:
    if not df_filtered.empty:
        st.markdown(
            f"**{len(df_filtered)} registros analisados** para "
            f"**{selected_date.strftime('%d/%m/%Y')}** no intervalo "
            f"**{hora_range[0]:02d}:00–{hora_range[1]:02d}:59**"
        )
        st.markdown("---")

        df_hist = df_alerts_raw.copy()

        if filtro_tipo and "type" in df_hist.columns:
            df_hist = df_hist[df_hist["type"].isin(filtro_tipo)]
        if filtro_natureza and "subtype" in df_hist.columns:
            df_hist = df_hist[df_hist["subtype"].isin(filtro_natureza)]
        if filtro_rua and "street" in df_hist.columns:
            df_hist = df_hist[df_hist["street"] == filtro_rua]

        DIAS_PT = {
            "Monday": "Segunda",
            "Tuesday": "Terça",
            "Wednesday": "Quarta",
            "Thursday": "Quinta",
            "Friday": "Sexta",
            "Saturday": "Sábado",
            "Sunday": "Domingo",
        }

        CORES_TIPO = {
            "ACIDENTE": "#e74c3c",
            "VIA FECHADA": "#c0392b",
            "PERIGO": "#e67e22",
            "PERIGO CLIMÁTICO": "#3498db",
            "CONGESTIONAMENTO": "#f39c12",
            "ALERTA": "#9b59b6",
        }

        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.subheader("Incidentes por Hora do Dia")
            hora_counts = (
                df_filtered["hour"]
                .value_counts()
                .reindex(range(24), fill_value=0)
                .reset_index()
            )
            hora_counts.columns = ["Hora", "Quantidade"]
            hora_pico = int(hora_counts.loc[hora_counts["Quantidade"].idxmax(), "Hora"])

            fig_hora = px.bar(
                hora_counts,
                x="Hora",
                y="Quantidade",
                color="Quantidade",
                color_continuous_scale="Reds",
                text="Quantidade",
                labels={"Hora": "Hora (UTC-3 / Foz)", "Quantidade": "Nº Incidentes"}
            )
            fig_hora.update_traces(textposition="outside")
            fig_hora.add_vline(
                x=hora_pico,
                line_dash="dash",
                line_color="darkred",
                annotation_text=f"Pico {hora_pico:02d}h"
            )
            fig_hora.update_layout(coloraxis_showscale=False, height=360)
            st.plotly_chart(fig_hora, width="stretch")

        with col_g2:
            st.subheader("Natureza das Ocorrências")

            tem_subtipo = (
                "subtype" in df_filtered.columns and
                df_filtered["subtype"].notna().any() and
                (~df_filtered["subtype"].isin(["nan", ""])).any()
            )

            if tem_subtipo:
                df_sub = df_filtered[
                    df_filtered["subtype"].notna() &
                    (~df_filtered["subtype"].isin(["nan", ""]))
                ].copy()
                df_sub["label"] = df_sub.apply(
                    lambda r: r["subtype"] if r["subtype"] != "" else r["type"], axis=1
                )
                sub_counts = df_sub["label"].value_counts().reset_index()
            else:
                sub_counts = df_filtered["type"].value_counts().reset_index()

            sub_counts.columns = ["Natureza", "Quantidade"]

            fig_pie = px.pie(
                sub_counts,
                names="Natureza",
                values="Quantidade",
                hole=0.38
            )
            fig_pie.update_layout(height=380)
            st.plotly_chart(fig_pie, width="stretch")

        st.markdown("---")

        if "day_of_week" in df_hist.columns and not df_hist.empty:
            st.subheader("Incidentes por Dia da Semana")
            df_dow = df_hist.copy()
            df_dow["Dia"] = df_dow["day_of_week"].map(DIAS_PT)

            dow_tipo = df_dow.groupby(["Dia", "type"]).size().reset_index(name="Quantidade")
            ordem_dias = list(DIAS_PT.values())

            fig_dow = px.bar(
                dow_tipo,
                x="Dia",
                y="Quantidade",
                color="type",
                color_discrete_map=CORES_TIPO,
                category_orders={"Dia": ordem_dias},
                barmode="stack",
                text_auto=True
            )
            fig_dow.update_layout(height=420)
            st.plotly_chart(fig_dow, width="stretch")

        st.markdown("---")

        st.subheader("Vias Críticas — Incidentes por Natureza")
        top_ruas_lista = []
        if "street" in df_hist.columns:
            top_ruas_lista = (
                df_hist[
                    df_hist["street"].notna() &
                    (~df_hist["street"].isin(["NA", "nan", ""]))
                ]["street"]
                .value_counts()
                .head(10)
                .index
                .tolist()
            )

        if top_ruas_lista and "subtype" in df_hist.columns:
            df_rua = df_hist[
                df_hist["street"].isin(top_ruas_lista) &
                df_hist["subtype"].notna() &
                (~df_hist["subtype"].isin(["nan", ""]))
            ].copy()

            rua_sub = df_rua.groupby(["street", "subtype"]).size().reset_index(name="Quantidade")
            ordem_ruas = (
                rua_sub.groupby("street")["Quantidade"]
                .sum()
                .sort_values(ascending=True)
                .index
                .tolist()
            )

            fig_rua = px.bar(
                rua_sub,
                x="Quantidade",
                y="street",
                color="subtype",
                orientation="h",
                barmode="stack",
                category_orders={"street": ordem_ruas}
            )
            fig_rua.update_layout(height=460)
            st.plotly_chart(fig_rua, width="stretch")

        st.markdown("---")

        st.subheader("Quais dias cada rua tem mais problemas?")
        if top_ruas_lista and "day_of_week" in df_hist.columns:
            df_hm = df_hist[df_hist["street"].isin(top_ruas_lista)].copy()
            df_hm["Dia"] = df_hm["day_of_week"].map(DIAS_PT)

            bubble_dow = df_hm.groupby(["street", "Dia"]).size().reset_index(name="Qtd")
            total_dow = bubble_dow.groupby(["street", "Dia"])["Qtd"].sum().reset_index(name="Total")

            vmax_dow = total_dow["Total"].max() if not total_dow.empty else 1

            def nivel_label(v, vmax):
                if v == 0:
                    return "Nenhum"
                elif v <= vmax * 0.25:
                    return "Baixo"
                elif v <= vmax * 0.60:
                    return "Médio"
                return "Alto"

            total_dow["Nível"] = total_dow["Total"].apply(lambda v: nivel_label(v, vmax_dow))

            fig_b1 = px.scatter(
                total_dow,
                x="Dia",
                y="street",
                size="Total",
                color="Nível",
                text="Total",
                size_max=55,
                category_orders={"Dia": list(DIAS_PT.values())}
            )
            fig_b1.update_layout(height=460)
            st.plotly_chart(fig_b1, width="stretch")
    else:
        st.info("Sem incidentes para gerar gráficos no recorte atual.")


# ---------------------------------------------------------
# ABA 5 — DADOS DETALHADOS
# ---------------------------------------------------------
with tab_dados:
    st.subheader("Tabela de Incidentes")

    if not df_filtered.empty:
        colunas_exibir = [
            c for c in [
                "timestamp", "type", "subtype", "street", "lat", "lon",
                "confidence", "reportRating"
            ] if c in df_filtered.columns
        ]

        st.dataframe(
            df_filtered[colunas_exibir].sort_values("timestamp", ascending=False),
            width="stretch"
        )

        csv = df_filtered[colunas_exibir].to_csv(index=False).encode("utf-8")
        st.download_button(
            "Baixar CSV — Incidentes",
            data=csv,
            file_name=f"incidentes_{selected_date}.csv",
            mime="text/csv"
        )
    else:
        st.info("Nenhum dado de incidente disponível.")

    st.subheader("Tabela de Congestionamentos")

    if not df_jams_filtered.empty:
        colunas_jams = [
            c for c in [
                "timestamp", "street", "speed", "length", "delay",
                "type", "subtype", "lat", "lon"
            ] if c in df_jams_filtered.columns
        ]

        df_jams_show = df_jams_filtered[colunas_jams].copy()
        if "speed" in df_jams_show.columns:
            df_jams_show["speed_kmh"] = (df_jams_show["speed"] * 3.6).round(1)

        st.dataframe(
            df_jams_show.sort_values("timestamp", ascending=False),
            width="stretch"
        )

        csv_jams = df_jams_show.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Baixar CSV — Congestionamentos",
            data=csv_jams,
            file_name=f"jams_{selected_date}.csv",
            mime="text/csv"
        )
    else:
        st.info("Nenhum dado de congestionamento disponível.")


# =========================================================
# BLOCO 7 — RODAPÉ CLARO / DESIGN ADAPTADO
# =========================================================

st.markdown("---")
rodape_html = f"""
<div style="background:linear-gradient(135deg,rgba(15,23,42,0.98) 0%,rgba(17,24,39,0.95) 100%);border:1px solid rgba(59,130,246,0.15);border-radius:16px;padding:2rem 2.5rem;margin-top:1rem;text-align:center;font-family:'Inter',sans-serif;">
  <div style="font-size:1.4rem;font-weight:800;color:#f1f5f9;margin-bottom:0.25rem;">🚗 GEO_IA — Monitoramento de Tráfego</div>
  <div style="font-size:0.82rem;color:#64748b;margin-bottom:1.5rem;">Sistema de análise de incidentes e congestionamentos via dados Waze · Foz do Iguaçu, PR</div>
  <div style="border-top:1px solid rgba(255,255,255,0.07);margin-bottom:1.5rem;"></div>
  <div style="margin-bottom:1.2rem;">
    <div style="font-size:1rem;font-weight:700;color:#f1f5f9;margin-bottom:0.2rem;">🏛️ UNILA — Universidade Federal da Integração Latino-Americana</div>
    <div style="font-size:0.78rem;color:#64748b;">Foz do Iguaçu, Paraná · Brasil</div>
  </div>
  <div style="border-top:1px solid rgba(255,255,255,0.07);margin-bottom:1.5rem;"></div>
  <div style="font-size:0.75rem;color:#475569;margin-bottom:0.9rem;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">Grupos &amp; Laboratórios de Pesquisa</div>
  <div style="display:flex;justify-content:center;gap:2rem;flex-wrap:wrap;margin-bottom:1.5rem;">
    <div style="text-align:center;">
      <div style="font-size:1rem;font-weight:700;color:#60a5fa;margin-bottom:0.2rem;">🔬 GPMME</div>
      <div style="font-size:0.78rem;color:#94a3b8;max-width:200px;line-height:1.5;">Grupo de Pesquisa em Mobilidade<br>e Matriz Energética</div>
    </div>
    <div style="width:1px;background:rgba(255,255,255,0.08);align-self:stretch;margin:0 0.25rem;"></div>
    <div style="text-align:center;">
      <div style="font-size:1rem;font-weight:700;color:#34d399;margin-bottom:0.2rem;">🧪 LAGGRA</div>
      <div style="font-size:0.78rem;color:#94a3b8;max-width:220px;line-height:1.5;">Lab. de Geologia, Geotecnia<br>e Recuperação Ambiental</div>
    </div>
    <div style="width:1px;background:rgba(255,255,255,0.08);align-self:stretch;margin:0 0.25rem;"></div>
    <div style="text-align:center;">
      <div style="font-size:1rem;font-weight:700;color:#f472b6;margin-bottom:0.2rem;">💻 LACA</div>
      <div style="font-size:0.78rem;color:#94a3b8;max-width:200px;line-height:1.5;">Laboratório de<br>Computação Aplicada</div>
    </div>
  </div>
  <div style="border-top:1px solid rgba(255,255,255,0.07);margin-bottom:1.2rem;"></div>
  <div style="font-size:0.75rem;color:#475569;margin-bottom:0.5rem;text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">Equipe de Desenvolvimento</div>
  <div style="display:flex;justify-content:center;gap:2rem;flex-wrap:wrap;margin-bottom:1.2rem;">
    <span style="font-size:0.82rem;color:#94a3b8;">👨‍💻 Luis Enrique Santacruz Alvarez</span>
    <span style="font-size:0.82rem;color:#94a3b8;">🎓 Dr. Diego Moraes Flores — ILATIT · UNILA</span>
  </div>
  <div style="border-top:1px solid rgba(255,255,255,0.07);margin-bottom:1rem;"></div>
  <div style="display:flex;justify-content:center;align-items:center;gap:1.5rem;flex-wrap:wrap;font-size:0.73rem;color:#334155;">
    <span>📡 Fonte: <strong style="color:#475569;">Waze for Cities</strong></span>
    <span>·</span>
    <span>🐍 Python · Streamlit · Folium · Plotly</span>
    <span>·</span>
    <span>☁️ Google Drive API</span>
    <span>·</span>
    <span>🕐 {hora_foz_atual.strftime('%d/%m/%Y %H:%M')} (Foz · UTC-3)</span>
  </div>
  <div style="margin-top:0.75rem;font-size:0.68rem;color:#1e293b;">© {hora_foz_atual.year} GPMME / LAGGRA / LACA — UNILA · Foz do Iguaçu · Uso acadêmico e de pesquisa</div>
</div>
"""
st.markdown(rodape_html, unsafe_allow_html=True)
                            
