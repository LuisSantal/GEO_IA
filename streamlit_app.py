import streamlit as st
import pandas as pd
import plotly.express as px
import io
import re
import ast
import tempfile
import numpy as np  # suporte matemático para modelo preditivo
import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import folium
from folium import plugins
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

# =========================================================
# BLOCO 1 — CONFIGURAÇÃO BASE DO APP
# =========================================================

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Waze Foz do Iguaçu",
    page_icon="https://cdn.simpleicons.org/waze",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Mapeamentos globais para suporte estatístico plurianual (Evita NameError nas abas)
MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

DIAS_PT = {
    "Monday": "Segunda", "Tuesday": "Terça", "Wednesday": "Quarta",
    "Thursday": "Quinta", "Friday": "Sexta", "Saturday": "Sábado", "Sunday": "Domingo"
}

DIAS_PT_CMP = {
    "Monday": "Segunda", "Tuesday": "Terça", "Wednesday": "Quarta",
    "Thursday": "Quinta", "Friday": "Sexta", "Saturday": "Sábado", "Sunday": "Domingo"
}

CORES_TIPO = {
    "ACIDENTE":         "#e74c3c",
    "VIA FECHADA":      "#c0392b",
    "PERIGO":           "#e67e22",
    "PERIGO CLIMÁTICO": "#3498db",
    "CONGESTIONAMENTO": "#f39c12",
    "ALERTA":           "#9b59b6",
}

# 2. TOKENS VISUAIS E CSS GLOBAL
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --bg:           #f0f4f8;
    --surface:      #ffffff;
    --surface-soft: #f8fafc;
    --surface-2:    #e8edf2;
    --text:         #1e293b;
    --text-strong:  #0f172a;
    --text-muted:   #475569;
    --text-faint:   #94a3b8;
    --border:       #dde3ea;
    --primary:      #2563eb;
    --primary-dark: #1d4ed8;
    --primary-soft: #eff6ff;
    --primary-hover:#1e40af;
    --success:      #16a34a;
    --success-soft: #f0fdf4;
    --warning:      #d97706;
    --warning-soft: #fffbeb;
    --danger:       #dc2626;
    --danger-soft:  #fef2f2;
    --purple:       #7c3aed;
    --radius:       12px;
    --shadow-sm:    0 1px 3px rgba(15,23,42,0.07), 0 1px 2px rgba(15,23,42,0.04);
    --shadow-md:    0 4px 12px rgba(15,23,42,0.10), 0 2px 6px rgba(15,23,42,0.06);
    --shadow-lg:    0 10px 30px rgba(15,23,42,0.12), 0 4px 10px rgba(15,23,42,0.07);
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    -webkit-font-smoothing: antialiased !important;
}

body { color: var(--text); }

.stApp {
    background: var(--bg) !important;
    color: var(--text) !important;
}

.main .block-container {
    background: transparent !important;
    padding-top: 1.5rem !important;
}

[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
    box-shadow: 2px 0 8px rgba(15,23,42,0.05) !important;
}

[data-testid="stSidebar"] * {
    color: var(--text) !important;
}

[data-testid="stSidebar"] .stMarkdown h3,
[data-testid="stSidebar"] .stMarkdown h4 {
    color: var(--text-strong) !important;
    font-weight: 700 !important;
}

[data-testid="stSidebar"] [data-testid="stMetricValue"] {
    color: var(--primary) !important;
    font-weight: 700 !important;
}

[data-testid="metric-container"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 1rem 1.2rem !important;
    box-shadow: var(--shadow-sm) !important;
    transition: box-shadow 160ms ease !important;
}

[data-testid="metric-container"]:hover {
    box-shadow: var(--shadow-md) !important;
}

[data-testid="metric-container"] label {
    color: var(--text-muted) !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.9px !important;
}

[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--text-strong) !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
}

[data-testid="stMetricDelta"] {
    font-size: 0.78rem !important;
    font-weight: 500 !important;
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
    padding: 8px 18px !important;
    transition: color 140ms ease, background 140ms ease !important;
}

.stTabs [data-baseweb="tab"]:hover {
    background: var(--surface-2) !important;
    color: var(--text) !important;
}

.stTabs [aria-selected="true"] {
    background: var(--primary) !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(37,99,235,0.30) !important;
}

[data-testid="stDataFrame"] {
    border-radius: var(--radius) !important;
    overflow: hidden !important;
    border: 1px solid var(--border) !important;
    background: var(--surface) !important;
    box-shadow: var(--shadow-sm) !important;
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
    box-shadow: var(--shadow-sm) !important;
}

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] > div,
[data-testid="stMultiSelect"] > div {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
}

[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
    background: var(--primary) !important;
    border-color: var(--primary) !important;
}

hr { border-color: var(--border) !important; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--surface-soft); border-radius: 3px; }
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

# 4. ESTADO DA SESSÃO
if "app_start_time" not in st.session_state:
    st.session_state.app_start_time = now_foz()

if "manual_refreshes" not in st.session_state:
    st.session_state.manual_refreshes = 0

tempo_sessao = (now_foz() - st.session_state.app_start_time).total_seconds()
tempo_prox_refresh = 600 - (tempo_sessao % 600)
minutos_restantes = int(tempo_prox_refresh // 60)
segundos_restantes = int(tempo_prox_refresh % 60)
tempo_total = int(tempo_sessao)

# 5. CONFIGURAÇÕES DE FONTE DE DADOS
FOLDER_ALERTS_ID  = "1xKkqLEusWuNoGzy5-UYuevUbMHAvc-bL"
FOLDER_JAMS_ID    = "192MCefe9vQwYhQcu-uZXekMbgdslTcgC"
FOLDER_ALERTS_ID2 = "1kQfYRJz0-EwY4gcsjTTVBCgK9zO5BAR0"
FOLDER_JAMS_ID2   = "16bblUG7NQmLMZM7BQUGAa3-GZIFYMka0"
LOCAL_CSV_PATH    = "Waze for Cities Data _ tabelas alertas_20240101_20260306.csv"

# =========================================================
# BLOCO 2 — CONEXÃO, INGESTÃO E ESTIMADOR PROBABILÍSTICO
# =========================================================

@st.cache_resource(show_spinner=False)
def get_drive_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    try:
        creds_info = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(
            creds_info,
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        return build("drive", "v3", credentials=creds)
    except Exception:
        return None

def get_latest_h5_id(folder_id: str) -> str | None:
    service = get_drive_service()
    if not service: return None
    try:
        query = f"'{folder_id}' in parents and name contains '.h5' and trashed=false"

        results = service.files().list(
            q=query,
            fields="files(id, name, modifiedTime)",
            orderBy="modifiedTime desc",
            pageSize=5
        ).execute()

        files = results.get("files", [])
        return files[0]["id"] if files else None
    except Exception:
        return None

def load_hdf_from_drive(file_id: str) -> pd.DataFrame:
    from googleapiclient.http import MediaIoBaseDownload

    service = get_drive_service()
    if not service: return pd.DataFrame()
    try:
        request = service.files().get_media(fileId=file_id)

        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        buffer.seek(0)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".h5") as tmp:
            tmp.write(buffer.getvalue())
            tmp_path = tmp.name

        df = pd.read_hdf(tmp_path, key="s")
        os.remove(tmp_path)
        return df
    except Exception:
        return pd.DataFrame()

def parse_pt_date(date_str):
    if not isinstance(date_str, str): return pd.NaT
    meses = {
        'jan.': 1, 'fev.': 2, 'mar.': 3, 'abr.': 4,
        'maio': 5, 'mai.': 5, 'jun.': 6, 'jul.': 7, 'ago.': 8,
        'set.': 9, 'out.': 10, 'nov.': 11, 'dez.': 12
    }
    try:
        match = re.search(r'(\d+)\s+de\s+([a-z\.]+)\s+de\s+(\d+)', date_str.lower())
        if match:
            dia, mes_nome, ano = match.groups()
            mes = meses.get(mes_nome, 1)
            return datetime(int(ano), int(mes), int(dia))
    except Exception:
        pass
    return pd.to_datetime(date_str, errors='coerce')

def extract_wkt_coordinates(location_str):
    if pd.isna(location_str):
        return None, None
    match = re.search(r'Point\(([-\s\d\.]+)\)', str(location_str), re.IGNORECASE)
    if match:
        try:
            coords = match.group(1).strip().split()
            return float(coords[1]), float(coords[0])
        except Exception: pass
    return None, None

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
    elif "Date" in df.columns:
        df["timestamp"] = df["Date"].apply(parse_pt_date)
    elif "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    else:
        df["timestamp"] = now_foz()

    df["date"]        = df["timestamp"].dt.date
    df["hour"]        = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.day_name()
    df["month"]       = df["timestamp"].dt.month
    df["year"]        = df["timestamp"].dt.year

    return df

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

    return df

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

@st.cache_data(ttl=600, show_spinner="🔄 Executando Cruzamento Histórico (MHDH)...")
def load_all_data():
    df_alerts = pd.DataFrame()
    df_jams = pd.DataFrame()

    alerts_id  = get_latest_h5_id(FOLDER_ALERTS_ID)
    jams_id    = get_latest_h5_id(FOLDER_JAMS_ID)

    frames_alerts = []
    if alerts_id: frames_alerts.append(load_hdf_from_drive(alerts_id))
    
    alerts_id2 = get_latest_h5_id(FOLDER_ALERTS_ID2)
    if alerts_id2: frames_alerts.append(load_hdf_from_drive(alerts_id2))

    if frames_alerts:
        df_alerts = pd.concat(frames_alerts, ignore_index=True)
        dedup_cols = ["uuid"] if "uuid" in df_alerts.columns else ["pubMillis", "street"]
        df_alerts = df_alerts.drop_duplicates(subset=dedup_cols)
        df_alerts = normalize_timestamps(df_alerts)

    frames_jams = []
    if jams_id: frames_jams.append(load_hdf_from_drive(jams_id))
    jams_id2 = get_latest_h5_id(FOLDER_JAMS_ID2)
    if jams_id2: frames_jams.append(load_hdf_from_drive(jams_id2))

    if frames_jams:
        df_jams = pd.concat(frames_jams, ignore_index=True)
        dedup_cols = ["uuid"] if "uuid" in df_jams.columns else ["pubMillis", "street"]
        df_jams = df_jams.drop_duplicates(subset=dedup_cols)

    prob_matrix = {}
    if not df_alerts.empty and "hour" in df_alerts.columns:
        grp = df_alerts.groupby(["type", "day_of_week", "hour"]).size().unstack(fill_value=0)
        for idx, row in grp.iterrows():
            total = row.sum()
            prob_matrix[idx] = row.values / total if total > 0 else np.ones(24)/24.0

    if os.path.exists(LOCAL_CSV_PATH):
        try:
            df_local_csv = pd.read_csv(LOCAL_CSV_PATH)
            
            coords_wkt = df_local_csv["Location"].apply(lambda x: pd.Series(extract_wkt_coordinates(x), index=["lat", "lon"]))
            df_local_csv["lat"] = coords_wkt["lat"]
            df_local_csv["lon"] = coords_wkt["lon"]
            
            df_local_csv = normalize_timestamps(df_local_csv)
            df_local_csv = df_local_csv.rename(columns={'Street': 'street', 'Type': 'type', 'Subtype': 'subtype'})
            df_local_csv = translate_dataframe(df_local_csv)

            hours_estimated = []
            for _, row in df_local_csv.iterrows():
                t_val = row.get("type", "HAZARD")
                d_val = row.get("day_of_week", "Monday")
                if (t_val, d_val) in prob_matrix:
                    hours_estimated.append(int(np.random.choice(range(24), p=prob_matrix[(t_val, d_val)])))
                else:
                    hours_estimated.append(int(np.random.choice(range(24))))
            
            df_local_csv["hour"] = hours_estimated
            df_local_csv["timestamp"] = df_local_csv.apply(
                lambda r: datetime.combine(r["date"], datetime.min.time().replace(hour=int(r["hour"]))) if pd.notna(r["date"]) else r["timestamp"], axis=1
            )
            df_alerts = pd.concat([df_alerts, df_local_csv], ignore_index=True) if not df_alerts.empty else df_local_csv
        except Exception:
            pass

    if not df_alerts.empty:
        dedup = ["uuid"] if "uuid" in df_alerts.columns else ["timestamp", "street"]
        df_alerts = df_alerts.drop_duplicates(subset=[c for c in dedup if c in df_alerts.columns])
        df_alerts = normalize_timestamps(df_alerts)
        df_alerts = extract_coordinates(df_alerts)
        if "street" not in df_alerts.columns:
            df_alerts["street"] = "N/A"

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

def generate_incidents_map(df_json: str) -> folium.Map | None:
    df = _load_json_df(df_json)
    if df.empty or "lat" not in df.columns or "lon" not in df.columns:
        return None

    df_map = filter_bbox_foz(df.dropna(subset=["lat", "lon"])).head(50)
    if df_map.empty:
        return None

    m = create_folium_map_with_compass(df_map["lat"].mean(), df_map["lon"].mean())

    for _, row in df_map.iterrows():
        try:
            tipo    = str(row.get("type", "?"))
            subtipo = str(row.get("subtype", ""))
            rua     = str(row.get("street", "N/A"))
            color   = get_danger_color(tipo, row.get("subtype"))
            ts      = _safe_time_label(row.get("timestamp"))
            lat_val = float(row["lat"])
            lon_val = float(row["lon"])

            popup_html = f"""
            <div style='min-width:200px;font-family:Arial,sans-serif;'>
                <b style='color:{color};font-size:16px;'>🚨 {tipo}</b><br>
                <b>{subtipo}</b><br>
                # 🛣️ <i>{rua}</i><br>
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

def generate_jams_map(df_json: str) -> folium.Map | None:
    df = _load_json_df(df_json)
    if df.empty or "lat" not in df.columns or "lon" not in df.columns:
        return None

    df_valid = filter_bbox_foz(df.dropna(subset=["lat", "lon"])).head(40)
    if df_valid.empty:
        return None

    m = create_folium_map_with_compass(df_valid["lat"].mean(), df_valid["lon"].mean())

    for _, row in df_valid.iterrows():
        try:
            speed_raw = row.get("speed", float("nan"))
            speed_kmh = float(speed_raw) * 3.6 if pd.notna(speed_raw) else 0.0
            color     = get_congestion_color(speed_kmh)
            rua       = str(row.get("street", "Via"))
            ts        = _safe_time_label(row.get("timestamp"))
            lat_val   = float(row["lat"])
            lon_val   = float(row["lon"])
            spd_str   = f"{speed_kmh:.0f} km/h"

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

def generate_heatmap(df_json: str) -> folium.Map | None:
    df = _load_json_df(df_json)
    if df.empty or "lat" not in df.columns or "lon" not in df.columns:
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
# BLOCO EXTRA — PIPELINE CIENTÍFICO E MCDA
# =========================================================

def build_daily_series(df_alerts: pd.DataFrame, df_jams: pd.DataFrame, categoria: str = "TODOS") -> pd.Series:
    frames = []

    if df_alerts is not None and not df_alerts.empty:
        da = df_alerts.copy()
        da["origem"] = "ALERTA"
        da["categoria_artigo"] = da["type"] if "type" in da.columns else "ALERTA"
        frames.append(da[["timestamp", "categoria_artigo", "origem"]])

    if df_jams is not None and not df_jams.empty:
        dj = df_jams.copy()
        dj["origem"] = "JAM"
        dj["categoria_artigo"] = "CONGESTIONAMENTO"
        frames.append(dj[["timestamp", "categoria_artigo", "origem"]])

    if not frames:
        return pd.Series(dtype=float)

    base = pd.concat(frames, ignore_index=True)
    base["timestamp"] = pd.to_datetime(base["timestamp"], errors="coerce")
    base = base.dropna(subset=["timestamp"]).copy()
    base["date"] = base["timestamp"].dt.floor("D")

    if categoria != "TODOS":
        base = base[base["categoria_artigo"] == categoria]

    serie = base.groupby("date").size().sort_index()
    if serie.empty:
        return pd.Series(dtype=float)

    idx = pd.date_range(serie.index.min(), serie.index.max(), freq="D")
    serie = serie.reindex(idx, fill_value=0)
    serie.index.name = "date"
    return serie

def run_stl_analysis(serie: pd.Series, period: int = 7):
    try:
        from statsmodels.tsa.seasonal import STL
        stl = STL(serie, period=period, robust=True)
        res = stl.fit()
        return res
    except Exception:
        return None

def run_pelt_analysis(serie: pd.Series, model: str = "l2", min_size: int = 7, jump: int = 1, pen: float = 3.0):
    try:
        import ruptures as rpt
        signal = serie.values.astype(float)
        algo = rpt.Pelt(model=model, min_size=min_size, jump=jump).fit(signal)
        bkps = algo.predict(pen=pen)
        return bkps
    except Exception:
        return []

def calculate_road_criticism(df_alerts, df_jams):
    """Índice de criticidade viária (MCDA) ponderando volume de retenções e atraso médio."""
    if df_jams.empty:
        return pd.DataFrame(columns=["street", "Volume_Jams", "Atraso_Medio_Seg", "Criticidade_Index"])

    agg = {}
    agg["Volume_Jams"] = ("street", "count")
    if "delay" in df_jams.columns:
        agg["Atraso_Medio_Seg"] = ("delay", "mean")
    if "length" in df_jams.columns:
        agg["Comprimento_Medio_M"] = ("length", "mean")

    grouped = df_jams.groupby("street").agg(**agg).reset_index()

    if "Atraso_Medio_Seg" not in grouped.columns:
        grouped["Atraso_Medio_Seg"] = 0.0
    if "Comprimento_Medio_M" not in grouped.columns:
        grouped["Comprimento_Medio_M"] = 0.0

    max_vol   = grouped["Volume_Jams"].max() or 1
    max_delay = grouped["Atraso_Medio_Seg"].max() or 1

    grouped["Criticidade_Index"] = (
        (grouped["Volume_Jams"]     / max_vol)   * 0.4 +
        (grouped["Atraso_Medio_Seg"] / max_delay) * 0.6
    ) * 100

    return grouped.sort_values("Criticidade_Index", ascending=False)

def build_descriptive_table(df_alerts: pd.DataFrame, df_jams: pd.DataFrame) -> pd.DataFrame:
    blocos = []

    if df_alerts is not None and not df_alerts.empty:
        da = df_alerts.copy()
        da["timestamp"] = pd.to_datetime(da["timestamp"], errors="coerce")
        da = da.dropna(subset=["timestamp"])
        da["date"] = da["timestamp"].dt.date
        da["hour"] = da["timestamp"].dt.hour

        diarios = da.groupby(["date", "type"]).size().reset_index(name="n")
        pico = da.groupby(["type", "hour"]).size().reset_index(name="n_hora")
        pico_idx = pico.groupby("type")["n_hora"].idxmax()
        pico = pico.loc[pico_idx][["type", "hour"]].rename(columns={"hour": "Hora_Pico"})

        resumo = diarios.groupby("type")["n"].agg(
            Total_Alertas="sum",
            Media_Diaria="mean",
            Desvio_Padrao="std"
        ).reset_index().rename(columns={"type": "Tipo"})
        resumo = resumo.merge(pico, left_on="Tipo", right_on="type", how="left").drop(columns=["type"], errors="ignore")
        blocos.append(resumo)

    if df_jams_filtered is not None and not df_jams_filtered.empty:
        dj = df_jams_filtered.copy()
        dj["timestamp"] = pd.to_datetime(dj["timestamp"], errors="coerce")
        dj = dj.dropna(subset=["timestamp"])
        dj["date"] = dj["timestamp"].dt.date
        dj["hour"] = dj["timestamp"].dt.hour
        diarios = dj.groupby("date").size().reset_index(name="n")
        pico = dj.groupby("hour").size().reset_index(name="n_hora")
        hora_pico = int(pico.loc[pico["n_hora"].idxmax(), "hour"]) if not pico.empty else None

        resumo_jam = pd.DataFrame([{
            "Tipo": "CONGESTIONAMENTO",
            "Total_Alertas": int(diarios["n"].sum()) if not diarios.empty else 0,
            "Media_Diaria": float(diarios["n"].mean()) if not diarios.empty else 0.0,
            "Desvio_Padrao": float(diarios["n"].std()) if not diarios.empty else 0.0,
            "Hora_Pico": hora_pico
        }])
        blocos.append(resumo_jam)

    if not blocos:
        return pd.DataFrame(columns=["Tipo", "Total_Alertas", "Media_Diaria", "Desvio_Padrao", "Hora_Pico"])

    out = pd.concat(blocos, ignore_index=True)
    out["Media_Diaria"] = out["Media_Diaria"].round(2)
    out["Desvio_Padrao"] = out["Desvio_Padrao"].round(2)
    return out

# =========================================================
# BLOCO 4 — SIDEBAR, CARGA OPERACIONAL E FILTROS
# =========================================================

# DECLARAÇÃO DE FUNÇÕES DO BLOCO 4 NO INÍCIO PARA EVITAR SUTIS EXCEÇÕES DE NAMEERROR
def apply_base_time_filter(df: pd.DataFrame, selected_date, hora_range: tuple[int, int]) -> pd.DataFrame:
    if df is None or df.empty: return pd.DataFrame()
    df = df.copy()
    if "date" not in df.columns or "hour" not in df.columns: return pd.DataFrame()
    
    df_date_col = pd.to_datetime(df["date"]).dt.date
    target_date = pd.to_datetime(selected_date).date()
    return df[(df_date_col == target_date) & (df["hour"].between(hora_range[0], hora_range[1]))].copy()

def clean_unique_values(series: pd.Series, invalid_values=None):
    if series is None:
        return []
    invalid_values = set(invalid_values or [])
    values = series.dropna().astype(str).str.strip()
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

st.sidebar.header("⚙️ Controles")
st.sidebar.markdown("### ⏳ Status da Sessão")

hora_foz_atual = now_foz()

try:
    df_alerts_raw, df_jams_raw = load_all_data()
except Exception as e:
    st.error(f"❌ Erro ao conectar com o Google Drive: {e}")
    st.stop()

st.sidebar.subheader("🔍 Filtros")
today_foz = hora_foz_atual.date()

all_dates = set()
if not df_alerts_raw.empty and "date" in df_alerts_raw.columns: 
    all_dates.update(pd.to_datetime(df_alerts_raw["date"]).dt.date.unique())
if not df_jams_raw.empty and "date" in df_jams_raw.columns: 
    all_dates.update(pd.to_datetime(df_jams_raw["date"]).dt.date.unique())

if all_dates:
    min_date     = min(all_dates)
    max_date     = max(all_dates)
    default_date = max(all_dates) if max(all_dates) in all_dates else today_foz
else:
    min_date = max_date = default_date = today_foz

# Recebe os seletores estruturados de data antes de acionar a filtragem base
selected_date = st.sidebar.date_input("📅 Data", value=default_date, min_value=min_date, max_value=max_date)
hora_range = st.sidebar.slider("🕒 Horário", min_value=0, max_value=23, value=(0, 23))

alerts_date_base = apply_base_time_filter(df_alerts_raw, selected_date, hora_range)
jams_date_base   = apply_base_time_filter(df_jams_raw,   selected_date, hora_range)

tipos_na_data = clean_unique_values(alerts_date_base["type"]) if not alerts_date_base.empty else []
filtro_tipo = st.sidebar.multiselect("🚨 Tipo", options=tipos_na_data, default=tipos_na_data)

natureza_base = alerts_date_base.copy()
if filtro_tipo and "type" in natureza_base.columns:
    natureza_base = natureza_base[natureza_base["type"].isin(filtro_tipo)]

naturezas_na_data = clean_unique_values(natureza_base["subtype"], invalid_values=["nan", ""]) if not natureza_base.empty else []
filtro_natureza = st.sidebar.multiselect("🔍 Natureza", options=naturezas_na_data, default=naturezas_na_data)

rua_base = natureza_base.copy()
if filtro_natureza and "subtype" in rua_base.columns:
    rua_base = rua_base[rua_base["subtype"].isin(filtro_natureza)]

ruas_na_data = clean_unique_values(rua_base["street"], invalid_values=["NA", "nan", "", "N/A"]) if not rua_base.empty else []
filtro_rua = st.sidebar.selectbox("🛣️ Rua", options=["(Todas)"] + ruas_na_data, index=0)
filtro_rua = "" if filtro_rua == "(Todas)" else filtro_rua

vel_range = st.sidebar.slider("🚗 Velocidade (km/h)", min_value=0.0, max_value=120.0, value=(0.0, 120.0), step=5.0)

if (
    not jams_date_base.empty
    and "speed" in jams_date_base.columns
    and jams_date_base["speed"].notna().any()
):
    media_vel   = jams_date_base["speed"].mean() * 3.6
    total_jams  = len(jams_date_base)
    status_label = classify_traffic_status(media_vel)

    st.sidebar.markdown("---")
    st.sidebar.markdown("**📊 Congestionamentos em** " + selected_date.strftime("%d/%m"))
    st.sidebar.metric("Vel. Média", f"{media_vel:.1f} km/h", delta=status_label)
    st.sidebar.metric("Total de Jams", total_jams)
else:
    st.sidebar.info(f"Sem dados de congestionamento em {selected_date.strftime('%d/%m')}.")

df_filtered = apply_base_time_filter(df_alerts_raw, selected_date, hora_range)

if not df_filtered.empty:
    if filtro_tipo and "type" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["type"].isin(filtro_tipo)]
    if filtro_natureza and "subtype" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["subtype"].isin(filtro_natureza)]
    if filtro_rua and "street" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["street"] == filtro_rua]

df_jams_filtered = apply_base_time_filter(df_jams_raw, selected_date, hora_range)

if not df_jams_filtered.empty and "speed" in df_jams_filtered.columns:
    df_jams_filtered = df_jams_filtered[
        (df_jams_filtered["speed"].fillna(0) * 3.6).between(vel_range[0], vel_range[1])
    ]

base_alertas_dashboard = df_filtered.copy()
base_jams_dashboard    = df_jams_filtered.copy()

if not base_jams_dashboard.empty:
    df_criticidade_vias = calculate_road_criticism(base_alertas_dashboard, base_jams_dashboard)
else:
    df_criticidade_vias = pd.DataFrame(columns=["street", "Volume_Jams", "Atraso_Medio_Seg", "Criticidade_Index"])

# =========================================================
# BLOCO 5 — CABEÇALHO, RESUMO, KPIs E INDICADORES
# =========================================================

st.markdown(f"<h1>Monitoramento de Tráfego — Foz do Iguaçu (Unificado)</h1>", unsafe_allow_html=True)
col_f1, col_f2, col_f3 = st.columns(3)
col_f1.metric("📅 Data Ativa", selected_date.strftime("%d/%m/%Y"))
col_f2.metric("Incidentes Carregados (H5 + Planilha)", len(df_filtered))
col_f3.metric("Retenções Ativas (Jams)", len(df_jams_filtered))

# =========================================================
# BLOCO 6 — VISUALIZAÇÕES PRINCIPAIS
# =========================================================
tab_inc, tab_jams, tab_calor, tab_temporal_danos, tab_graficos, tab_pipeline, tab_predicao, tab_dados = st.tabs(
    [
        "Incidentes",
        "Congestionamentos",
        "Mapa de Calor",
        "📅 Análise Geométrica de Danos",
        "Gráficos",
        "🧪 Pipeline Científico",
        "🔮 Modelo Preditivo",
        "Dados"
    ]
)

with tab_inc:
    st.caption("📍 Centro: -25.54, -54.58 · Norte ↑ · Clique nos pontos para detalhes")

    if not df_filtered.empty:
        m_inc = generate_incidents_map(df_filtered.to_json(date_format="iso"))

        if ST_FOLIUM_AVAILABLE and m_inc:
            st_folium(m_inc, width="100%", height=500, key=f"mapa_inc_{len(df_filtered)}")

            st.markdown("""
            | Cor | Tipo / Natureza |
            |---|---|
            | 🔴 | Acidente grave / Alta gravidade |
            | 💗 | Acidente leve / Baixa gravidade |
            | 🟥 | Via fechada / Obras / Bloqueio total |
            | 🟧 | Perigo / Buraco na via / Risco moderado |
            | 🟨 | Alerta / Semáforo / Atenção |
            | 🟦 | Perigo climático / Condições adversas |
            | 🟪 | Congestionamento / Trânsito parado |
            """)
        elif not ST_FOLIUM_AVAILABLE:
            st.error("⚠️ O componente 'streamlit-folium' não pôde ser carregado. Certifique-se de adicioná-lo ao seu arquivo requirements.txt.")
        else:
            st.info("Nenhum incidente mapeável dentro do recorte geográfico de Foz do Iguaçu.")
    else:
        st.info("Nenhum incidente para os filtros aplicados nesta data.")

with tab_jams:
    st.caption("🚦 Escala métrica · Livre → Parado")

    if not df_jams_filtered.empty:
        m_jam = generate_jams_map(df_jams_filtered.to_json(date_format="iso"))

        if ST_FOLIUM_AVAILABLE and m_jam:
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
        elif not ST_FOLIUM_AVAILABLE:
            st.error("⚠️ O componente 'streamlit-folium' não pôde ser carregado.")
        else:
            st.info("Nenhum congestionamento ativo no mapa para este recorte.")
    else:
        st.info("Nenhum congestionamento para exibir.")

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

                if ST_FOLIUM_AVAILABLE:
                    st_folium(m_heat, width="100%", height=500, key=f"mapa_heat_{len(df_heat)}")
                else:
                    st.error("⚠️ O componente 'streamlit-folium' não pôde ser carregado.")

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

with tab_temporal_danos:
    st.subheader("📅 Estudo Espacial Plurianual e Geometria Viária (2024 - 2026)")
    st.markdown("""
    Esta seção analisa de forma geoespacial e estatística as **Top 5 vias urbanas com maior recorrência de buracos**. 
    O sistema realiza requisições dinâmicas de infraestrutura ao ecossistema *OpenStreetMap (Nominatim)* para reconstruir as polilinhas das vias.
    """)

    def get_street_geometry_nominatim(street_name: str, city: str):
        search_query = f'{street_name}, {city}, Brazil'
        url = 'https://nominatim.openstreetmap.org/search'
        params = {'q': search_query, 'format': 'json', 'limit': 1, 'polygon_geojson': 1}
        headers = {'User-Agent': 'GeoIA_Streamlit_Academic/2.0'}
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and 'geojson' in data[0]:
                    geojson = data[0]['geojson']
                    if geojson['type'] == 'LineString':
                        return [[c[1], c[0]] for c in geojson['coordinates']]
                    elif geojson['type'] == 'MultiLineString':
                        coords = []
                        for segment in geojson['coordinates']:
                            coords.extend([[c[1], c[0]] for c in segment])
                        return coords
        except Exception: pass
        return None

    if df_alerts_raw.empty:
        st.warning("A base de dados de alertas não foi carregada corretamente.")
    else:
        df_base_danos = df_alerts_raw.copy()
        df_all_potholes = df_base_danos[
            df_base_danos['subtype'].isin(['BURACO NA VIA', 'HAZARD_ON_ROAD_POT_HOLE', 'Buraco Na Via'])
        ].copy()

        if df_all_potholes.empty:
            st.info("Nenhum registro de 'BURACO NA VIA' identificado para processamento plurianual.")
        else:
            df_all_potholes['ano_item'] = pd.to_datetime(df_all_potholes['timestamp']).dt.year
            ano_selecionado = st.selectbox("Selecione o Ano Fiscal para Visualização:", [2024, 2025, 2026], index=2)
            df_potholes_year = df_all_potholes[df_all_potholes['ano_item'] == ano_selecionado].copy()

            if df_potholes_year.empty:
                st.warning(f"Não foram encontrados dados consolidados para o ano de {ano_selecionado}.")
            else:
                df_potholes_year = df_potholes_year.dropna(subset=['lat', 'lon'])

                st.markdown(f"### 📊 Ranking das Top 5 Vias Afetadas — {ano_selecionado}")
                top_streets = df_potholes_year['street'].value_counts().nlargest(5).reset_index()
                top_streets.columns = ['Rua', 'Contagem de Buracos']

                if top_streets.empty or top_streets['Rua'].isnull().all():
                    st.info(f"Nenhum nome de rua válido identificado em {ano_selecionado}.")
                else:
                    col_chart, col_table = st.columns([3, 2])
                    with col_chart:
                        fig_bar_top = px.bar(
                            top_streets, 
                            x='Contagem de Buracos', 
                            y='Rua', 
                            orientation='h',
                            color='Contagem de Buracos',
                            color_continuous_scale='magma',
                            title=f'Top 5 Ruas com Mais Reportes de Buracos - {ano_selecionado}'
                        )
                        fig_bar_top.update_layout(height=350, showlegend=False, coloraxis_showscale=False)
                        st.plotly_chart(fig_bar_top, use_container_width=True)
                        
                    with col_table:
                        st.markdown("#### Quantitativo Crítico Acumulado")
                        st.dataframe(top_streets, hide_index=True, use_container_width=True)

                st.markdown(f"### 🗺️ Malha Vetorial de Severidade Viária — {ano_selecionado}")
                st.caption("Abaixo, o mapa reconstrói a geometria das ruas principais e agrupa os clusters de reclamações gerados pela população.")

                df_potholes_year['city_field'] = df_potholes_year.get('city', 'Foz do Iguaçu')
                top_streets_geo = (
                    df_potholes_year.dropna(subset=['street'])
                    .groupby(['street', 'city_field'])
                    .size()
                    .nlargest(5)
                    .reset_index(name='PotholeCount')
                )

                street_geometries_to_plot = {}
                for _, row_geo in top_streets_geo.iterrows():
                    s_name = row_geo['street']
                    c_name = row_geo['city_field']
                    p_count = row_geo['PotholeCount']
                    geom = get_street_geometry_nominatim(s_name, c_name)
                    if geom and len(geom) >= 2:
                        street_geometries_to_plot[(s_name, c_name)] = {'geometry': geom, 'pothole_count': p_count}

                if not street_geometries_to_plot:
                    m_yearly = folium.Map(location=[df_potholes_year["lat"].mean(), df_potholes_year["lon"].mean()], zoom_start=13)
                else:
                    first_key = list(street_geometries_to_plot.keys())[0]
                    first_coords = street_geometries_to_plot[first_key]['geometry'][0]
                    m_yearly = folium.Map(location=[first_coords[0], first_coords[1]], zoom_start=13, tiles='OpenStreetMap')

                all_coords = []
                for (s_name, c_name), data_geo in street_geometries_to_plot.items():
                    geo_coords = data_geo['geometry']
                    p_count = data_geo['pothole_count']
                    all_coords.extend(geo_coords)

                    street_group = folium.FeatureGroup(name=f"Eixo: {s_name} ({p_count} un)", show=True)
                    folium.PolyLine(locations=geo_coords, color='#2563eb', weight=6, opacity=0.85, tooltip=f"<b>Via:</b> {s_name}<br><b>Alertas:</b> {p_count}").add_to(street_group)

                    df_single_street = df_potholes_year[df_potholes_year['street'] == s_name].head(200)
                    cluster = MarkerCluster(name=f"Clusters em {s_name}", disableClusteringAtZoom=16).add_to(street_group)

                    for _, row_point in df_single_street.iterrows():
                        popup_txt = f"<b>Via:</b> {row_point['street']}<br><b>Data:</b> {row_point.get('Date', selected_date)}"
                        folium.CircleMarker(location=[row_point['lat'], row_point['lon']], radius=4, color='#991b1b', fill=True, fillColor='#ef4444', fillOpacity=0.8, popup=folium.Popup(popup_txt, max_width=200)).add_to(cluster)

                    street_group.add_to(m_yearly)

                if all_coords:
                    m_yearly.fit_bounds(all_coords)
                
                if ST_FOLIUM_AVAILABLE:
                    st_folium(m_yearly, width="100%", height=550, key=f"mapa_geom_anual_{ano_selecionado}")
                else:
                    st.error("⚠️ O componente 'streamlit-folium' não pôde ser carregado.")

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
                hora_counts, x="Hora", y="Quantidade",
                color="Quantidade", color_continuous_scale="Reds", text="Quantidade",
                labels={"Hora": "Hora (UTC-3 / Foz)", "Quantidade": "Nº Incidentes"}
            )
            fig_hora.update_traces(textposition="outside")
            fig_hora.add_vline(x=hora_pico, line_dash="dash", line_color="darkred", annotation_text=f"Pico {hora_pico:02d}h")
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

            fig_pie = px.pie(sub_counts, names="Natureza", values="Quantidade", hole=0.38)
            fig_pie.update_layout(height=380)
            st.plotly_chart(fig_pie, width="stretch")

        st.markdown("---")

        if "day_of_week" in df_hist.columns and not df_hist.empty:
            st.subheader("Incidentes por Dia da Semana")
            df_dow = df_hist.copy()
            df_dow["Dia"] = df_dow["day_of_week"].map(DIAS_PT)

            dow_tipo   = df_dow.groupby(["Dia", "type"]).size().reset_index(name="Quantidade")
            ordem_dias = list(DIAS_PT.values())

            fig_dow = px.bar(
                dow_tipo, x="Dia", y="Quantidade", color="type",
                color_discrete_map=CORES_TIPO,
                category_orders={"Dia": ordem_dias},
                barmode="stack", text_auto=True
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

            rua_sub    = df_rua.groupby(["street", "subtype"]).size().reset_index(name="Quantidade")
            ordem_ruas = (
                rua_sub.groupby("street")["Quantidade"]
                .sum()
                .sort_values(ascending=True)
                .index
                .tolist()
            )

            fig_rua = px.bar(
                rua_sub, x="Quantidade", y="street", color="subtype",
                orientation="h", barmode="stack",
                category_orders={"street": ordem_ruas}
            )
            fig_rua.update_layout(height=460)
            st.plotly_chart(fig_rua, width="stretch")

        st.markdown("---")
        st.subheader("Quais dias cada rua tem mais problemas?")
        if top_ruas_lista and "day_of_week" in df_hist.columns:
            df_hm     = df_hist[df_hist["street"].isin(top_ruas_lista)].copy()
            df_hm["Dia"] = df_hm["day_of_week"].map(DIAS_PT)

            bubble_dow = df_hm.groupby(["street", "Dia"]).size().reset_index(name="Qtd")
            total_dow  = bubble_dow.groupby(["street", "Dia"])["Qtd"].sum().reset_index(name="Total")
            vmax_dow = total_dow["Total"].max() if not total_dow.empty else 1

            def nivel_label(v, vmax):
                if v == 0: return "Nenhum"
                elif v <= vmax * 0.25: return "Baixo"
                elif v <= vmax * 0.60: return "Médio"
                return "Alto"

            total_dow["Nível"] = total_dow["Total"].apply(lambda v: nivel_label(v, vmax_dow))

            fig_b1 = px.scatter(
                total_dow, x="Dia", y="street", size="Total",
                color="Nível", text="Total", size_max=55,
                category_orders={"Dia": list(DIAS_PT.values())}
            )
            fig_b1.update_layout(height=460)
            st.plotly_chart(fig_b1, width="stretch")
    else:
        st.info("Sem incidentes para gerar gráficos no recorte atual.")

with tab_pipeline:
    st.subheader("🧪 Pipeline Científico para o Artigo")
    st.caption("Geração de séries, decomposição STL, detecção de rupturas (PELT) e tabelas descritivas para apoio à redação acadêmica.")

    col_p1, col_p2, col_p3 = st.columns(3)
    categorias_disp = ["TODOS"]
    if not df_alerts_raw.empty and "type" in df_alerts_raw.columns:
        categorias_disp += sorted(df_alerts_raw["type"].dropna().astype(str).unique().tolist())
    categorias_disp = list(dict.fromkeys(categorias_disp + ["CONGESTIONAMENTO"]))

    with col_p1:
        categoria_artigo = st.selectbox("Categoria analisada", categorias_disp, index=0, key="pipe_categoria")
    with col_p2:
        periodo_stl = st.selectbox("Periodicidade STL", [7, 30], index=0, key="pipe_stl_period")
    with col_p3:
        penalidade_pelt = st.slider("Penalidade PELT", min_value=1.0, max_value=20.0, value=5.0, step=0.5, key="pipe_pelt_pen")

    serie = build_daily_series(df_alerts_raw, df_jams_raw, categoria=categoria_artigo)

    if serie.empty:
        st.info("Sem dados suficientes para montar a série temporal.")
    else:
        st.markdown("### Série diária")
        df_serie = serie.reset_index()
        df_serie.columns = ["Data", "Ocorrências"]

        fig_ts = px.line(
            df_serie, x="Data", y="Ocorrências",
            title=f"Série diária de ocorrências — {categoria_artigo}",
            markers=False
        )
        fig_ts.update_layout(height=360)
        st.plotly_chart(fig_ts, use_container_width=True)

        st.markdown("### Decomposição STL")
        res_stl = run_stl_analysis(serie, period=periodo_stl)

        if res_stl is not None:
            from plotly.subplots import make_subplots
            import plotly.graph_objects as go

            fig_stl = make_subplots(
                rows=4, cols=1, shared_xaxes=True,
                subplot_titles=["Observed", "Trend", "Seasonal", "Residual"],
                vertical_spacing=0.04
            )
            x_vals = serie.index

            fig_stl.add_trace(go.Scatter(x=x_vals, y=res_stl.observed, name="Observed", line=dict(color="#2563EB")), row=1, col=1)
            fig_stl.add_trace(go.Scatter(x=x_vals, y=res_stl.trend, name="Trend", line=dict(color="#DC2626")), row=2, col=1)
            fig_stl.add_trace(go.Scatter(x=x_vals, y=res_stl.seasonal, name="Seasonal", line=dict(color="#16A34A")), row=3, col=1)
            fig_stl.add_trace(go.Scatter(x=x_vals, y=res_stl.resid, name="Residual", mode="lines", line=dict(color="#7C3AED")), row=4, col=1)

            fig_stl.update_layout(height=900, showlegend=False, title=f"STL — {categoria_artigo} (period={periodo_stl})")
            st.plotly_chart(fig_stl, use_container_width=True)
        else:
            st.warning("Não foi possível executar a STL. Verifique se `statsmodels` está instalado.")

        st.markdown("### Rupturas estruturais — PELT")
        bkps = run_pelt_analysis(serie, model="l2", min_size=7, jump=1, pen=penalidade_pelt)

        fig_pelt = px.line(df_serie, x="Data", y="Ocorrências", title="Mudanças estruturais detectadas por PELT")
        for b in bkps[:-1]:
            if 0 <= b - 1 < len(df_serie):
                data_bkp = df_serie.iloc[b - 1]["Data"]
                fig_pelt.add_vline(x=data_bkp, line_dash="dash", line_color="red")
        fig_pelt.update_layout(height=360)
        st.plotly_chart(fig_pelt, use_container_width=True)

        if bkps:
            datas_ruptura = []
            for b in bkps[:-1]:
                if 0 <= b - 1 < len(df_serie):
                    datas_ruptura.append(pd.to_datetime(df_serie.iloc[b - 1]["Data"]).strftime("%Y-%m-%d"))
            st.write("Datas estimadas de ruptura:", datas_ruptura if datas_ruptura else "Nenhuma ruptura relevante.")

    st.markdown("---")
    st.markdown("### Tabela 1 — Estatísticas descritivas")
    tabela_desc = build_descriptive_table(df_alerts_raw, df_jams_raw)
    if not tabela_desc.empty:
        st.dataframe(tabela_desc, hide_index=True, use_container_width=True)
        csv_desc = tabela_desc.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Baixar CSV — Tabela 1", data=csv_desc,
            file_name="tabela_1_estatisticas_descritivas.csv",
            mime="text/csv"
        )
    else:
        st.info("Sem dados suficientes para a tabela descritiva.")

with tab_predicao:
    st.subheader("🔮 Simulador Preditivo de Impacto e Propensão ao Congestionamento")
    st.markdown("""
    Combinação de **regressão inferencial** (impacto temporal por extensão de fila) com análise histórica de
    **propensão ao congestionamento por via e dia da semana**, fundamentada nos dados reais do dataset WazeFoz.
    """)

    st.markdown("### 🧮 Simulador de Atraso por Extensão de Fila")
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        extensao_sim = st.slider("Extensão da fila (metros):", 50, 5000, 500, 50, key="slider_pred_ext")
        atraso_est   = predict_traffic_delay_impact(extensao_sim)
        minutos_est  = atraso_est / 60
        st.metric("Atraso Estimado", f"{minutos_est:.2f} min")
        st.caption("Fórmula: *Atraso (s) = Comprimento × 0,15 + 12*")

    with col_p2:
        sim_x  = np.linspace(50, 5000, 100)
        sim_y  = [predict_traffic_delay_impact(l) / 60 for l in sim_x]
        df_sim = pd.DataFrame({"Comprimento (m)": sim_x, "Atraso Estimado (min)": sim_y})
        fig_pred = px.line(df_sim, x="Comprimento (m)", y="Atraso Estimado (min)", title="Curva de Impacto: Extensão de Fila vs Atraso")
        fig_pred.add_scatter(
            x=[extensao_sim], y=[minutos_est],
            mode="markers+text", name="Cenário atual",
            text=["◀ Selecionado"], textposition="top right",
            marker=dict(size=12, color="red")
        )
        st.plotly_chart(fig_pred, use_container_width=True)

    st.markdown("---")
    st.markdown("### 📅 Vias com Maior Propensão ao Congestionamento por Dia da Semana")
    st.caption("Baseado no histórico completo de congestionamentos carregados — independente do filtro de data.")

    if not df_jams_hist.empty and "street" in df_jams_hist.columns and "day_of_week" in df_jams_hist.columns:
        df_jams_hist = df_jams_hist[
            df_jams_hist["street"].notna() &
            (~df_jams_hist["street"].isin(["NA", "nan", "Via", ""]))
        ].copy()
        df_jams_hist["Dia"] = df_jams_hist["day_of_week"].map(DIAS_PT_CMP)

        top_vias_pred = df_jams_hist["street"].value_counts().head(15).index.tolist()
        df_prop = df_jams_hist[df_jams_hist["street"].isin(top_vias_pred)]

        heatmap_data = df_prop.groupby(["street", "Dia"]).size().reset_index(name="Ocorrências")
        total_por_via = heatmap_data.groupby("street")["Ocorrências"].transform("sum")
        heatmap_data["Propensão (%)"] = (heatmap_data["Ocorrências"] / total_por_via * 100).round(1)

        col_h1, col_h2 = st.columns([3, 2])

        with col_h1:
            pivot = heatmap_data.pivot_table(
                index="street", columns="Dia", values="Propensão (%)", aggfunc="sum"
            ).reindex(columns=[d for d in ORDEM_DIAS if d in heatmap_data["Dia"].unique()], fill_value=0)

            fig_heat = px.imshow(
                pivot, color_continuous_scale="YlOrRd", aspect="auto",
                title="Mapa de Propensão: Via × Dia da Semana (% de ocorrências históricas)",
                labels={"color": "Propensão (%)", "x": "Dia", "y": "Via"}
            )
            fig_heat.update_layout(height=480)
            st.plotly_chart(fig_heat, use_container_width=True)

        with col_h2:
            dia_selecionado = st.selectbox("Ver vias mais propensas em:", ORDEM_DIAS, key="pred_dia")
            df_dia = heatmap_data[heatmap_data["Dia"] == dia_selecionado].sort_values("Propensão (%)", ascending=False).head(10)

            if not df_dia.empty:
                fig_dia = px.bar(
                    df_dia, x="Propensão (%)", y="street", orientation="h",
                    color="Propensão (%)", color_continuous_scale="Reds",
                    title=f"Top 10 — {dia_selecionado}",
                    labels={"street": "Via", "Propensão (%)": "% do tráfego semanal"}
                )
                fig_dia.update_layout(height=380, coloraxis_showscale=False)
                st.plotly_chart(fig_dia, use_container_width=True)
            else:
                st.info(f"Sem dados históricos para {dia_selecionado}.")

        st.markdown("#### 📋 Pior Dia da Semana por Via")
        pior_dia = (
            heatmap_data.loc[heatmap_data.groupby("street")["Propensão (%)"].idxmax()]
            [["street", "Dia", "Propensão (%)", "Ocorrências"]]
            .sort_values("Ocorrências", ascending=False)
            .head(15)
            .reset_index(drop=True)
        )
        st.dataframe(
            pior_dia, hide_index=True,
            column_config={
                "street":        "Via / Avenida",
                "Dia":           "Pior Dia",
                "Propensão (%)": "% no Dia",
                "Ocorrências":   "Total de Registros"
            }
        )
    else:
        st.info("Histórico de congestionamentos insuficiente para análise de propensão por via e dia.")

    st.markdown("---")
    st.markdown("### 2025 vs 2026")
    st.caption("Selecione um dia da semana e uma categoria para comparar a evolução mês a mês entre os dois anos.")

    frames_cmp = []
    if not df_alerts_raw.empty:
        df_a_cmp = df_alerts_raw.copy()
        df_a_cmp["categoria"] = df_a_cmp.get("type", pd.Series("ALERTA", index=df_a_cmp.index))
        df_a_cmp["origem"] = "alerta"
        frames_cmp.append(df_a_cmp[[c for c in ["timestamp","categoria","origem","street","day_of_week"] if c in df_a_cmp.columns]])

    if not df_jams_raw.empty:
        df_j_cmp = df_jams_raw.copy()
        df_j_cmp["categoria"] = "CONGESTIONAMENTO"
        df_j_cmp["origem"] = "jams"
        frames_cmp.append(df_j_cmp[[c for c in ["timestamp","categoria","origem","street","day_of_week"] if c in df_j_cmp.columns]])

    if frames_cmp:
        df_cmp_all = pd.concat(frames_cmp, ignore_index=True)
        df_cmp_all["timestamp"] = pd.to_datetime(df_cmp_all["timestamp"], errors="coerce")
        df_cmp_all = df_cmp_all.dropna(subset=["timestamp"])
        df_cmp_all["ano"]  = df_cmp_all["timestamp"].dt.year
        df_cmp_all["mes"]  = df_cmp_all["timestamp"].dt.month
        df_cmp_all["Dia"]  = df_cmp_all["day_of_week"].map(DIAS_PT_CMP) if "day_of_week" in df_cmp_all.columns else "Todos"
        df_cmp_all["mes_nome"] = df_cmp_all["mes"].map(MESES_PT)

        anos_disp = sorted(df_cmp_all["ano"].dropna().unique().astype(int).tolist())
        cats_disp = sorted(df_cmp_all["categoria"].dropna().unique().tolist())
        dias_disp = ["Todos"] + ["Segunda","Terça","Quarta","Quinta","Sexta","Sábado","Domingo"]

        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        with col_c1:
            ano_a = st.selectbox("Ano A:", anos_disp, index=0, key="cmp_ano_a")
        with col_c2:
            ano_b_opts = [a for a in anos_disp if a != ano_a]
            ano_b = st.selectbox("Ano B:", ano_b_opts if ano_b_opts else anos_disp, key="cmp_ano_b")
        with col_c3:
            dia_cmp = st.selectbox("Dia da Semana:", dias_disp, key="cmp_dia")
        with col_c4:
            cat_cmp = st.multiselect("Categorias:", cats_disp, default=cats_disp[:3] if len(cats_disp) >= 3 else cats_disp, key="cmp_cat")

        df_f = df_cmp_all[df_cmp_all["categoria"].isin(cat_cmp)] if cat_cmp else df_cmp_all.copy()
        if dia_cmp != "Todos":
            df_f = df_f[df_f["Dia"] == dia_cmp]

        df_ano_a = df_f[df_f["ano"] == ano_a]
        df_ano_b = df_f[df_f["ano"] == ano_b]

        def agg_mensal(df_in, ano_label):
            if df_in.empty: return pd.DataFrame(columns=["mes","mes_nome","Total","Ano"])
            grp = df_in.groupby(["mes","mes_nome","categoria"]).size().reset_index(name="Total")
            grp["Ano"] = str(ano_label)
            return grp

        res_a = agg_mensal(df_ano_a, ano_a)
        res_b = agg_mensal(df_ano_b, ano_b)
        df_comp = pd.concat([res_a, res_b], ignore_index=True)

        if not df_comp.empty:
            df_comp = df_comp.sort_values("mes")
            ordem_meses = [MESES_PT[m] for m in sorted(df_comp["mes"].unique())]

            total_mes = df_comp.groupby(["mes","mes_nome","Ano"])["Total"].sum().reset_index()
            total_mes = total_mes.sort_values("mes")

            fig_linha = px.line(
                total_mes, x="mes_nome", y="Total", color="Ano", markers=True,
                title=f"Evolução Mensal Total — {ano_a} vs {ano_b}" + (f" · {dia_cmp}" if dia_cmp != "Todos" else ""),
                labels={"mes_nome":"Mês","Total":"Nº Ocorrências","Ano":"Ano"},
                color_discrete_map={str(ano_a):"#2563EB", str(ano_b):"#DC2626"},
                category_orders={"mes_nome": ordem_meses}
            )
            fig_linha.update_layout(height=380)
            st.plotly_chart(fig_linha, use_container_width=True)

            fig_bar = px.bar(
                df_comp, x="mes_nome", y="Total", color="Ano",
                facet_col="categoria", facet_col_wrap=3, barmode="group",
                title="Comparativo por Categoria e Mês",
                labels={"mes_nome":"Mês","Total":"Ocorrências"},
                color_discrete_map={str(ano_a):"#2563EB", str(ano_b):"#DC2626"},
                category_orders={"mes_nome": ordem_meses}
            )
            fig_bar.update_layout(height=420)
            fig_bar.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
            st.plotly_chart(fig_bar, use_container_width=True)

            st.markdown("#### 📈 Variação Percentual Mês a Mês (Crescimento / Decrescimento)")
            pivot_var = total_mes.pivot_table(index="mes_nome", columns="Ano", values="Total").reindex(ordem_meses)
            pivot_var.columns = [str(c) for c in pivot_var.columns]
            col_a_str, col_b_str = str(ano_a), str(ano_b)

            if col_a_str in pivot_var.columns and col_b_str in pivot_var.columns:
                pivot_var["Variação (%)"] = (
                    (pivot_var[col_b_str] - pivot_var[col_a_str]) / pivot_var[col_a_str].replace(0, np.nan) * 100
                ).round(1)
                pivot_var = pivot_var.reset_index()
                pivot_var["Cor"] = pivot_var["Variação (%)"].apply(lambda v: "Aumento 📈" if v >= 0 else "Redução 📉")

                fig_var = px.bar(
                    pivot_var.dropna(subset=["Variação (%)"]),
                    x="mes_nome", y="Variação (%)", color="Cor",
                    color_discrete_map={"Aumento 📈":"#DC2626","Redução 📉":"#16A34A"},
                    title=f"Variação % de {ano_a} → {ano_b} por Mês",
                    labels={"mes_nome":"Mês","Variação (%)":"Variação (%)"},
                    text="Variação (%)",
                    category_orders={"mes_nome": ordem_meses}
                )
                fig_var.update_traces(texttemplate="%{text}%", textposition="outside")
                fig_var.add_hline(y=0, line_dash="dash", line_color="gray")
                fig_var.update_layout(height=360, showlegend=True)
                st.plotly_chart(fig_var, use_container_width=True)

            st.markdown("#### 📋 Tabela Resumo Comparativa")
            tbl = pivot_var[["mes_nome", col_a_str, col_b_str, "Variação (%)"]].copy() if "Variação (%)" in pivot_var.columns else pivot_var
            if "Variação (%)" in tbl.columns:
                tbl.columns = ["Mês", str(ano_a), str(ano_b), "Δ (%)"]
            st.dataframe(tbl, hide_index=True, use_container_width=True)
        else:
            st.info("Sem dados suficientes para o comparativo mensal com os filtros selecionados.")
    else:
        st.info("Nenhum dado histórico disponível para comparação.")

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
            "Baixar CSV — Incidentes", data=csv,
            file_name=f"incidentes_{selected_date}.csv", mime="text/csv"
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
            "Baixar CSV — Congestionamentos", data=csv_jams,
            file_name=f"jams_{selected_date}.csv", mime="text/csv"
        )
    else:
        st.info("Nenhum dado de congestionamento disponível.")

# =========================================================
# BLOCO 7 — RODAPÉ
# =========================================================

st.markdown("---")
rodape_html = f"""
<div style="
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-top: 1rem;
    text-align: center;
    font-family: 'Inter', sans-serif;
    box-shadow: 0 2px 12px rgba(15,23,42,0.07);
">
  <div style="font-size:1.4rem;font-weight:800;color:#0F172A;margin-bottom:0.25rem;
              display:flex;align-items:center;justify-content:center;gap:10px;">
    <img src="https://cdn.simpleicons.org/waze/00C9D4" width="32" height="32" alt="Waze for Cities">
    GEO_IA — Monitoramento de Tráfego
  </div>
  <div style="font-size:0.82rem;color:#475569;margin-bottom:1.5rem;">
    Sistema de análise de incidentes e congestionamentos via dados Waze for Cities · Foz do Iguaçu, PR
  </div>

  <div style="border-top:1px solid #E2E8F0;margin-bottom:1.5rem;"></div>

  <div style="margin-bottom:1.2rem;">
    <div style="font-size:1rem;font-weight:700;color:#0F172A;margin-bottom:0.2rem;">
      🏛️ UNILA — Universidade Federal da Integração Latino-Americana
    </div>
    <div style="font-size:0.78rem;color:#64748B;">Foz do Iguaçu, Paraná · Brasil</div>
  </div>

  <div style="border-top:1px solid #E2E8F0;margin-bottom:1.5rem;"></div>

  <div style="font-size:0.75rem;color:#94A3B8;margin-bottom:0.9rem;
              text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">
    Grupos &amp; Laboratórios de Pesquisa
  </div>

  <div style="display:flex;justify-content:center;gap:2rem;flex-wrap:wrap;margin-bottom:1.5rem;">
    <div style="text-align:center;">
      <div style="font-size:1rem;font-weight:700;color:#2563EB;margin-bottom:0.2rem;">🔬 GPMME</div>
      <div style="font-size:0.78rem;color:#475569;max-width:200px;line-height:1.5;">
        Grupo de Pesquisa em Mobilidade<br>e Matriz Energética
      </div>
    </div>
    <div style="width:1px;background:#E2E8F0;align-self:stretch;margin:0 0.25rem;"></div>
    <div style="text-align:center;">
      <div style="font-size:1rem;font-weight:700;color:#059669;margin-bottom:0.2rem;">🧪 LAGGRA</div>
      <div style="font-size:0.78rem;color:#475569;max-width:220px;line-height:1.5;">
        Lab. de Geologia, Geotecnia<br>e Recuperação Ambiental
      </div>
    </div>
    <div style="width:1px;background:#E2E8F0;align-self:stretch;margin:0 0.25rem;"></div>
    <div style="text-align:center;">
      <div style="font-size:1rem;font-weight:700;color:#7C3AED;margin-bottom:0.2rem;">💻 LACA</div>
      <div style="font-size:0.78rem;color:#475569;max-width:200px;line-height:1.5;">
        Laboratório de<br>Computação Aplicada
      </div>
    </div>
  </div>

  <div style="border-top:1px solid #E2E8F0;margin-bottom:1.2rem;"></div>

  <div style="font-size:0.75rem;color:#94A3B8;margin-bottom:0.9rem;
              text-transform:uppercase;letter-spacing:0.8px;font-weight:600;">
    Equipe de Desenvolvimento
  </div>
  <div style="display:flex;justify-content:center;gap:2rem;flex-wrap:wrap;margin-bottom:1.2rem;">
    <span style="font-size:0.82rem;color:#334155;">👨‍💻 Luis Enrique Santacruz Alvarez</span>
    <span style="font-size:0.82rem;color:#334155;">🎓 Dr. Diego Moraes Flores — ILATIT · UNILA</span>
  </div>

  <div style="border-top:1px solid #E2E8F0;margin-bottom:1rem;"></div>

  <div style="display:flex;justify-content:center;align-items:center;gap:1.5rem;
              flex-wrap:wrap;font-size:0.73rem;color:#64748B;">
    <span>📡 Fonte:
      <img src="https://cdn.simpleicons.org/waze/00C9D4" width="14" height="14"
           style="vertical-align:middle;margin:0 2px;">
      <strong style="color:#0F172A;">Waze for Cities</strong>
    </span>
    <span>·</span>
    <span>🐍 Python · Streamlit · Folium · Plotly</span>
    <span>·</span>
    <span>☁️ Google Drive API</span>
    <span>·</span>
    <span>Local: Foz do Iguaçu (UTC-3)</span>
  </div>
  <div style="margin-top:0.75rem;font-size:0.68rem;color:#94A3B8;">
    © {hora_foz_atual.year} GPMME / LAGGRA / LACA — UNILA · Foz do Iguaçu · Uso acadêmico e de pesquisa
  </div>
</div>
"""
st.markdown(rodape_html, unsafe_allow_html=True)
