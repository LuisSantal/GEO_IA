import streamlit as st
import pandas as pd
import plotly.express as px
import io
import re
import ast
import tempfile
import numpy as np
import os

from datetime import datetime
from zoneinfo import ZoneInfo

import folium
from folium import plugins
from streamlit_folium import st_folium


# =========================================================
# BLOCO 1 — CONFIGURAÇÃO BASE DO APP
# =========================================================

st.set_page_config(
    page_title="Waze Foz do Iguaçu",
    page_icon="https://cdn.simpleicons.org/waze",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

.stButton > button[kind="primary"] {
    background: var(--primary) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    box-shadow: var(--shadow-md) !important;
    transition: background 160ms ease, box-shadow 160ms ease, transform 120ms ease !important;
}

.stButton > button[kind="primary"]:hover {
    background: var(--primary-hover) !important;
    box-shadow: var(--shadow-lg) !important;
    transform: translateY(-1px) !important;
}

.stButton > button[kind="primary"]:active {
    transform: translateY(0) !important;
    box-shadow: var(--shadow-sm) !important;
}

.stButton > button[kind="secondary"] {
    background: var(--surface) !important;
    color: var(--primary) !important;
    border: 1.5px solid var(--primary) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
}

.stButton > button[kind="secondary"]:hover {
    background: var(--primary-soft) !important;
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

[data-testid="stExpander"]:hover {
    border-color: #bcd0f0 !important;
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

[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
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

.card-light {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.25rem 1.5rem;
    box-shadow: var(--shadow-sm);
}

.badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 10px;
    border-radius: 99px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.4px;
}
.badge-success { background: var(--success-soft); color: var(--success); border: 1px solid #bbf7d0; }
.badge-warning { background: var(--warning-soft); color: var(--warning); border: 1px solid #fde68a; }
.badge-danger  { background: var(--danger-soft);  color: var(--danger);  border: 1px solid #fecaca; }
.badge-primary { background: var(--primary-soft); color: var(--primary); border: 1px solid #bfdbfe; }
</style>
""", unsafe_allow_html=True)

TIMEZONE_FOZ = ZoneInfo("America/Sao_Paulo")


def get_current_foz_time() -> datetime:
    return datetime.now(TIMEZONE_FOZ).replace(tzinfo=None)


if "app_start_time" not in st.session_state:
    st.session_state.app_start_time = get_current_foz_time()

if "manual_refreshes" not in st.session_state:
    st.session_state.manual_refreshes = 0

session_elapsed_seconds = (get_current_foz_time() - st.session_state.app_start_time).total_seconds()
seconds_until_next_refresh = 600 - (session_elapsed_seconds % 600)
minutes_until_next_refresh = int(seconds_until_next_refresh // 60)
remaining_seconds = int(seconds_until_next_refresh % 60)
session_elapsed_total_seconds = int(session_elapsed_seconds)

GOOGLE_DRIVE_ALERTS_FOLDER_ID_1 = "1xKkqLEusWuNoGzy5-UYuevUbMHAvc-bL"
GOOGLE_DRIVE_JAMS_FOLDER_ID_1 = "192MCefe9vQwYhQcu-uZXekMbgdslTcgC"
GOOGLE_DRIVE_ALERTS_FOLDER_ID_2 = "1kQfYRJz0-EwY4gcsjTTVBCgK9zO5BAR0"
GOOGLE_DRIVE_JAMS_FOLDER_ID_2 = "16bblUG7NQmLMZM7BQUGAa3-GZIFYMka0"


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


def get_incident_severity_color(incident_type: str, incident_subtype: str | None = None) -> str:
    low_severity_subtypes = {
        "ACIDENTE LEVE",
        "TRÂNSITO MODERADO",
        "PERIGO NA VIA",
        "OBJETO NA VIA",
        "ANIMAL NA VIA",
        "VEÍCULO PARADO",
        "CONDIÇÕES CLIMÁTICAS",
    }

    normalized_type = str(incident_type).upper().strip() if incident_type else ""
    normalized_subtype = str(incident_subtype).upper().strip() if incident_subtype else ""
    is_low_severity = normalized_subtype in low_severity_subtypes

    base_color_by_type = {
        "ACIDENTE": "#F44336" if not is_low_severity else "#EF9A9A",
        "VIA FECHADA": "#B71C1C",
        "CONGESTIONAMENTO": "#7B1FA2" if not is_low_severity else "#CE93D8",
        "PERIGO": "#FF9800" if not is_low_severity else "#FFCC80",
        "PERIGO CLIMÁTICO": "#29B6F6",
        "OBRAS": "#78909C",
        "ALERTA": "#FDD835",
    }

    subtype_override_color = {
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

    if normalized_subtype in subtype_override_color:
        return subtype_override_color[normalized_subtype]

    return base_color_by_type.get(normalized_type, "#90A4AE")


# =========================================================
# BLOCO 2 — CONEXÃO, INGESTÃO E NORMALIZAÇÃO DOS DADOS
# =========================================================

@st.cache_resource(show_spinner=False)
def get_google_drive_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    service_account_info = st.secrets["gcp_service_account"]
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build("drive", "v3", credentials=credentials)


def get_latest_hdf_file_id(folder_id: str) -> str | None:
    google_drive_service = get_google_drive_service()
    query = f"'{folder_id}' in parents and name contains '.h5' and trashed=false"

    response = google_drive_service.files().list(
        q=query,
        fields="files(id, name, modifiedTime)",
        orderBy="modifiedTime desc",
        pageSize=20
    ).execute()

    available_files = response.get("files", [])
    if not available_files:
        return None

    latest_file_id = None
    latest_numeric_timestamp = -1

    for file_metadata in available_files:
        timestamp_match = re.search(r"(\d{8,})", file_metadata["name"])
        if timestamp_match:
            numeric_timestamp = int(timestamp_match.group(1))
            if numeric_timestamp > latest_numeric_timestamp:
                latest_numeric_timestamp = numeric_timestamp
                latest_file_id = file_metadata["id"]

    return latest_file_id if latest_file_id else available_files[0]["id"]


@st.cache_data(ttl=600, show_spinner="📥 Baixando dados do Drive...")
def load_hdf_dataframe_from_drive(file_id: str) -> pd.DataFrame:
    from googleapiclient.http import MediaIoBaseDownload

    google_drive_service = get_google_drive_service()
    file_request = google_drive_service.files().get_media(fileId=file_id)

    binary_buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(binary_buffer, file_request)

    download_finished = False
    while not download_finished:
        _, download_finished = downloader.next_chunk()

    binary_buffer.seek(0)
    temporary_file_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".h5") as temporary_file:
            temporary_file.write(binary_buffer.getvalue())
            temporary_file_path = temporary_file.name

        loaded_dataframe = pd.read_hdf(temporary_file_path, key="s")
        return loaded_dataframe

    finally:
        if temporary_file_path and os.path.exists(temporary_file_path):
            os.remove(temporary_file_path)


def normalize_timestamps(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe is None or dataframe.empty:
        return dataframe

    normalized_dataframe = dataframe.copy()

    if "pubMillis" in normalized_dataframe.columns:
        normalized_dataframe["timestamp"] = (
            pd.to_datetime(normalized_dataframe["pubMillis"], unit="ms", utc=True)
            .dt.tz_convert("America/Sao_Paulo")
            .dt.tz_localize(None)
        )
    elif "timestamp" in normalized_dataframe.columns:
        normalized_dataframe["timestamp"] = pd.to_datetime(normalized_dataframe["timestamp"], errors="coerce")
    else:
        normalized_dataframe["timestamp"] = get_current_foz_time()

    normalized_dataframe["date"] = normalized_dataframe["timestamp"].dt.date
    normalized_dataframe["hour"] = normalized_dataframe["timestamp"].dt.hour
    normalized_dataframe["day_of_week"] = normalized_dataframe["timestamp"].dt.day_name()

    return normalized_dataframe


def parse_dictionary_like_value(raw_value):
    if isinstance(raw_value, dict):
        return raw_value
    if isinstance(raw_value, str):
        try:
            return ast.literal_eval(raw_value)
        except Exception:
            return None
    return None


def extract_lat_lon_from_location_field(location_value):
    parsed_value = parse_dictionary_like_value(location_value)
    if isinstance(parsed_value, dict):
        try:
            return float(parsed_value.get("y")), float(parsed_value.get("x"))
        except Exception:
            return None, None
    return None, None


def extract_alert_coordinates(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe is None or dataframe.empty:
        return dataframe

    coordinates_dataframe = dataframe.copy()

    if "lat" in coordinates_dataframe.columns and "lon" in coordinates_dataframe.columns:
        coordinates_dataframe["lat"] = pd.to_numeric(coordinates_dataframe["lat"], errors="coerce")
        coordinates_dataframe["lon"] = pd.to_numeric(coordinates_dataframe["lon"], errors="coerce")
        return coordinates_dataframe

    if "location" in coordinates_dataframe.columns:
        extracted_coordinates = coordinates_dataframe["location"].apply(
            lambda location_value: pd.Series(
                extract_lat_lon_from_location_field(location_value),
                index=["lat", "lon"]
            )
        )
        coordinates_dataframe["lat"] = extracted_coordinates["lat"]
        coordinates_dataframe["lon"] = extracted_coordinates["lon"]

    if "lat" not in coordinates_dataframe.columns and "y" in coordinates_dataframe.columns:
        coordinates_dataframe["lat"] = pd.to_numeric(coordinates_dataframe["y"], errors="coerce")

    if "lon" not in coordinates_dataframe.columns and "x" in coordinates_dataframe.columns:
        coordinates_dataframe["lon"] = pd.to_numeric(coordinates_dataframe["x"], errors="coerce")

    return coordinates_dataframe


def extract_midpoint_from_line_geometry(line_value):
    try:
        line_points = line_value if isinstance(line_value, list) else ast.literal_eval(str(line_value))
        if not line_points:
            return None, None
        midpoint = line_points[len(line_points) // 2]
        return float(midpoint.get("y")), float(midpoint.get("x"))
    except Exception:
        return None, None


def extract_jam_coordinates(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe is None or dataframe.empty:
        return dataframe

    jam_coordinates_dataframe = dataframe.copy()

    if "lat" in jam_coordinates_dataframe.columns and "lon" in jam_coordinates_dataframe.columns:
        jam_coordinates_dataframe["lat"] = pd.to_numeric(jam_coordinates_dataframe["lat"], errors="coerce")
        jam_coordinates_dataframe["lon"] = pd.to_numeric(jam_coordinates_dataframe["lon"], errors="coerce")
        if jam_coordinates_dataframe["lat"].notna().any():
            return jam_coordinates_dataframe

    if "line" in jam_coordinates_dataframe.columns:
        extracted_coordinates = jam_coordinates_dataframe["line"].apply(
            lambda line_value: pd.Series(
                extract_midpoint_from_line_geometry(line_value),
                index=["lat", "lon"]
            )
        )
        jam_coordinates_dataframe["lat"] = extracted_coordinates["lat"]
        jam_coordinates_dataframe["lon"] = extracted_coordinates["lon"]
        if jam_coordinates_dataframe["lat"].notna().any():
            return jam_coordinates_dataframe

    if "location" in jam_coordinates_dataframe.columns:
        extracted_coordinates = jam_coordinates_dataframe["location"].apply(
            lambda location_value: pd.Series(
                extract_lat_lon_from_location_field(location_value),
                index=["lat", "lon"]
            )
        )
        jam_coordinates_dataframe["lat"] = extracted_coordinates["lat"]
        jam_coordinates_dataframe["lon"] = extracted_coordinates["lon"]

    if "lat" not in jam_coordinates_dataframe.columns and "y" in jam_coordinates_dataframe.columns:
        jam_coordinates_dataframe["lat"] = pd.to_numeric(jam_coordinates_dataframe["y"], errors="coerce")

    if "lon" not in jam_coordinates_dataframe.columns and "x" in jam_coordinates_dataframe.columns:
        jam_coordinates_dataframe["lon"] = pd.to_numeric(jam_coordinates_dataframe["x"], errors="coerce")

    return jam_coordinates_dataframe


def normalize_speed_column(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe is None or dataframe.empty:
        return dataframe

    normalized_speed_dataframe = dataframe.copy()

    if "speed" in normalized_speed_dataframe.columns:
        normalized_speed_dataframe["speed"] = pd.to_numeric(normalized_speed_dataframe["speed"], errors="coerce")
        return normalized_speed_dataframe

    for alternative_speed_column in ["speedKMH", "speedkmh", "speed_kmh", "velocity"]:
        if alternative_speed_column in normalized_speed_dataframe.columns:
            normalized_speed_dataframe["speed"] = pd.to_numeric(
                normalized_speed_dataframe[alternative_speed_column],
                errors="coerce"
            ) / 3.6
            return normalized_speed_dataframe

    normalized_speed_dataframe["speed"] = float("nan")
    return normalized_speed_dataframe


INCIDENT_TYPE_TRANSLATION = {
    "ROAD_CLOSED": "VIA FECHADA",
    "ROAD_CLOSED_CONSTRUCTION": "VIA FECHADA",
    "ROAD_CLOSED_EVENT": "VIA FECHADA",
    "HAZARD": "PERIGO",
    "ACCIDENT": "ACIDENTE",
    "JAM": "CONGESTIONAMENTO",
    "WEATHERHAZARD": "PERIGO CLIMÁTICO",
}

INCIDENT_SUBTYPE_TRANSLATION = {
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


def translate_incident_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe is None or dataframe.empty:
        return dataframe

    translated_dataframe = dataframe.copy()

    if "type" in translated_dataframe.columns:
        translated_dataframe["type"] = translated_dataframe["type"].replace(INCIDENT_TYPE_TRANSLATION)

    if "subtype" in translated_dataframe.columns:
        translated_dataframe["subtype"] = translated_dataframe["subtype"].replace(INCIDENT_SUBTYPE_TRANSLATION)

        known_translated_values = set(INCIDENT_SUBTYPE_TRANSLATION.values())
        unknown_subtype_mask = translated_dataframe["subtype"].notna() & ~translated_dataframe["subtype"].isin(known_translated_values)

        translated_dataframe.loc[unknown_subtype_mask, "subtype"] = (
            translated_dataframe.loc[unknown_subtype_mask, "subtype"]
            .astype(str)
            .str.replace(
                r"^(HAZARD_ON_ROAD_|HAZARD_ON_SHOULDER_|HAZARD_WEATHER_|HAZARD_|ACCIDENT_|JAM_|ROAD_CLOSED_)",
                "",
                regex=True
            )
            .str.replace("_", " ", regex=False)
            .str.title()
        )

    return translated_dataframe


@st.cache_data(ttl=600, show_spinner="🔄 Carregando dados do Google Drive...")
def load_all_data():
    latest_alerts_file_id_1 = get_latest_hdf_file_id(GOOGLE_DRIVE_ALERTS_FOLDER_ID_1)
    latest_alerts_file_id_2 = get_latest_hdf_file_id(GOOGLE_DRIVE_ALERTS_FOLDER_ID_2)
    latest_jams_file_id_1 = get_latest_hdf_file_id(GOOGLE_DRIVE_JAMS_FOLDER_ID_1)
    latest_jams_file_id_2 = get_latest_hdf_file_id(GOOGLE_DRIVE_JAMS_FOLDER_ID_2)

    alert_dataframes = []
    if latest_alerts_file_id_1:
        alert_dataframes.append(load_hdf_dataframe_from_drive(latest_alerts_file_id_1))
    if latest_alerts_file_id_2:
        alert_dataframes.append(load_hdf_dataframe_from_drive(latest_alerts_file_id_2))

    if alert_dataframes:
        alerts_dataframe = pd.concat(alert_dataframes, ignore_index=True)
        alert_deduplication_columns = ["uuid"] if "uuid" in alerts_dataframe.columns else ["pubMillis", "street"]
        alerts_dataframe = alerts_dataframe.drop_duplicates(subset=alert_deduplication_columns)
    else:
        alerts_dataframe = pd.DataFrame()

    jam_dataframes = []
    if latest_jams_file_id_1:
        jam_dataframes.append(load_hdf_dataframe_from_drive(latest_jams_file_id_1))
    if latest_jams_file_id_2:
        jam_dataframes.append(load_hdf_dataframe_from_drive(latest_jams_file_id_2))

    if jam_dataframes:
        jams_dataframe = pd.concat(jam_dataframes, ignore_index=True)
        jam_deduplication_columns = ["uuid"] if "uuid" in jams_dataframe.columns else ["pubMillis", "street"]
        jams_dataframe = jams_dataframe.drop_duplicates(subset=jam_deduplication_columns)
    else:
        jams_dataframe = pd.DataFrame()

    if not alerts_dataframe.empty:
        alerts_dataframe = normalize_timestamps(alerts_dataframe)
        alerts_dataframe = extract_alert_coordinates(alerts_dataframe)
        alerts_dataframe = translate_incident_columns(alerts_dataframe)
        if "street" not in alerts_dataframe.columns:
            alerts_dataframe["street"] = "N/A"

    if not jams_dataframe.empty:
        jams_dataframe = normalize_timestamps(jams_dataframe)
        jams_dataframe = extract_jam_coordinates(jams_dataframe)
        jams_dataframe = normalize_speed_column(jams_dataframe)
        if "street" not in jams_dataframe.columns:
            jams_dataframe["street"] = "Via"

    return alerts_dataframe, jams_dataframe


# =========================================================
# BLOCO 3 — MAPAS E VISUALIZAÇÕES GEOESPACIAIS
# =========================================================

FOZ_LATITUDE_MIN, FOZ_LATITUDE_MAX = -25.70, -25.40
FOZ_LONGITUDE_MIN, FOZ_LONGITUDE_MAX = -54.75, -54.45


def filter_to_foz_bounding_box(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe is None or dataframe.empty:
        return dataframe

    bounded_dataframe = dataframe.copy()

    if "lat" not in bounded_dataframe.columns or "lon" not in bounded_dataframe.columns:
        return pd.DataFrame()

    bounded_dataframe["lat"] = pd.to_numeric(bounded_dataframe["lat"], errors="coerce")
    bounded_dataframe["lon"] = pd.to_numeric(bounded_dataframe["lon"], errors="coerce")

    return bounded_dataframe[
        bounded_dataframe["lat"].between(FOZ_LATITUDE_MIN, FOZ_LATITUDE_MAX) &
        bounded_dataframe["lon"].between(FOZ_LONGITUDE_MIN, FOZ_LONGITUDE_MAX)
    ].copy()


def create_folium_map_with_compass(center_latitude: float, center_longitude: float, zoom_level: int = 13) -> folium.Map:
    folium_map = folium.Map(
        location=[center_latitude, center_longitude],
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
    ).add_to(folium_map)

    plugins.Fullscreen(
        position="topleft",
        title="Expandir mapa",
        title_cancel="Sair da tela cheia",
        force_separate_button=True
    ).add_to(folium_map)

    scale_control_script = """
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
    folium_map.get_root().html.add_child(folium.Element(scale_control_script))

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
    folium_map.get_root().html.add_child(folium.Element(compass_html))

    folium.LayerControl(position="topright", collapsed=True).add_to(folium_map)
    return folium_map


def load_json_as_dataframe(dataframe_json: str) -> pd.DataFrame:
    try:
        parsed_dataframe = pd.read_json(io.StringIO(dataframe_json))
        return parsed_dataframe if parsed_dataframe is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def format_time_label(timestamp_value) -> str:
    try:
        if pd.notna(timestamp_value):
            return pd.to_datetime(timestamp_value).strftime("%H:%M")
    except Exception:
        pass
    return "--"


def generate_incidents_map(dataframe_json: str) -> folium.Map | None:
    incidents_dataframe = load_json_as_dataframe(dataframe_json)
    if incidents_dataframe.empty:
        return None

    if ("lat" not in incidents_dataframe.columns or incidents_dataframe["lat"].isna().all()) and "location" in incidents_dataframe.columns:
        def get_location_lat(location_value):
            try:
                parsed_location = ast.literal_eval(location_value) if isinstance(location_value, str) else location_value
                return float(parsed_location.get("y"))
            except Exception:
                return None

        def get_location_lon(location_value):
            try:
                parsed_location = ast.literal_eval(location_value) if isinstance(location_value, str) else location_value
                return float(parsed_location.get("x"))
            except Exception:
                return None

        incidents_dataframe["lat"] = incidents_dataframe["location"].apply(get_location_lat)
        incidents_dataframe["lon"] = incidents_dataframe["location"].apply(get_location_lon)

    if "lat" not in incidents_dataframe.columns and "y" in incidents_dataframe.columns:
        incidents_dataframe["lat"] = pd.to_numeric(incidents_dataframe["y"], errors="coerce")
    if "lon" not in incidents_dataframe.columns and "x" in incidents_dataframe.columns:
        incidents_dataframe["lon"] = pd.to_numeric(incidents_dataframe["x"], errors="coerce")

    if "lat" not in incidents_dataframe.columns or "lon" not in incidents_dataframe.columns:
        return None

    map_incidents_dataframe = filter_to_foz_bounding_box(
        incidents_dataframe.dropna(subset=["lat", "lon"])
    ).head(50)

    if map_incidents_dataframe.empty:
        return None

    incident_map = create_folium_map_with_compass(
        map_incidents_dataframe["lat"].mean(),
        map_incidents_dataframe["lon"].mean()
    )

    for _, incident_row in map_incidents_dataframe.iterrows():
        try:
            incident_type = str(incident_row.get("type", "?"))
            incident_subtype = str(incident_row.get("subtype", ""))
            street_name = str(incident_row.get("street", "N/A"))
            marker_color = get_incident_severity_color(incident_type, incident_row.get("subtype"))
            formatted_time = format_time_label(incident_row.get("timestamp"))
            latitude = float(incident_row["lat"])
            longitude = float(incident_row["lon"])

            popup_html = f"""
            <div style='min-width:200px;font-family:Arial,sans-serif;'>
                <b style='color:{marker_color};font-size:16px;'>🚨 {incident_type}</b><br>
                <b>{incident_subtype}</b><br>
                🛣️ <i>{street_name}</i><br>
                🕒 {formatted_time}<br>
                📍 {latitude:.4f}, {longitude:.4f}
            </div>
            """

            folium.CircleMarker(
                location=[latitude, longitude],
                radius=9,
                popup=folium.Popup(popup_html, max_width=260),
                tooltip=f"{incident_type}: {street_name}",
                color=marker_color,
                fill=True,
                fillColor=marker_color,
                fillOpacity=0.8,
                weight=2
            ).add_to(incident_map)

        except Exception:
            continue

    return incident_map


def generate_jams_map(dataframe_json: str) -> folium.Map | None:
    jams_dataframe = load_json_as_dataframe(dataframe_json)
    if jams_dataframe.empty:
        return None

    if ("lat" not in jams_dataframe.columns or jams_dataframe["lat"].isna().all()) and "line" in jams_dataframe.columns:
        def get_line_midpoint(line_value):
            try:
                line_points = line_value if isinstance(line_value, list) else ast.literal_eval(str(line_value))
                if not line_points:
                    return None, None
                midpoint = line_points[len(line_points) // 2]
                return float(midpoint.get("y")), float(midpoint.get("x"))
            except Exception:
                return None, None

        extracted_coordinates = jams_dataframe["line"].apply(
            lambda line_value: pd.Series(get_line_midpoint(line_value), index=["lat", "lon"])
        )
        jams_dataframe["lat"] = extracted_coordinates["lat"]
        jams_dataframe["lon"] = extracted_coordinates["lon"]

    if ("lat" not in jams_dataframe.columns or jams_dataframe["lat"].isna().all()) and "location" in jams_dataframe.columns:
        def get_location_lat(location_value):
            try:
                parsed_location = ast.literal_eval(location_value) if isinstance(location_value, str) else location_value
                return float(parsed_location.get("y"))
            except Exception:
                return None

        def get_location_lon(location_value):
            try:
                parsed_location = ast.literal_eval(location_value) if isinstance(location_value, str) else location_value
                return float(parsed_location.get("x"))
            except Exception:
                return None

        jams_dataframe["lat"] = jams_dataframe["location"].apply(get_location_lat)
        jams_dataframe["lon"] = jams_dataframe["location"].apply(get_location_lon)

    if "lat" not in jams_dataframe.columns and "y" in jams_dataframe.columns:
        jams_dataframe["lat"] = pd.to_numeric(jams_dataframe["y"], errors="coerce")
    if "lon" not in jams_dataframe.columns and "x" in jams_dataframe.columns:
        jams_dataframe["lon"] = pd.to_numeric(jams_dataframe["x"], errors="coerce")

    if "speed" not in jams_dataframe.columns:
        for alternative_speed_column in ["speedKMH", "speedkmh", "speed_kmh", "velocity"]:
            if alternative_speed_column in jams_dataframe.columns:
                jams_dataframe["speed"] = pd.to_numeric(jams_dataframe[alternative_speed_column], errors="coerce") / 3.6
                break
        else:
            jams_dataframe["speed"] = float("nan")

    if "lat" not in jams_dataframe.columns or "lon" not in jams_dataframe.columns:
        return None

    valid_jams_dataframe = filter_to_foz_bounding_box(
        jams_dataframe.dropna(subset=["lat", "lon"])
    ).head(40)

    if valid_jams_dataframe.empty:
        return None

    jam_map = create_folium_map_with_compass(
        valid_jams_dataframe["lat"].mean(),
        valid_jams_dataframe["lon"].mean()
    )

    for _, jam_row in valid_jams_dataframe.iterrows():
        try:
            speed_meters_per_second = jam_row.get("speed", float("nan"))
            speed_kmh = float(speed_meters_per_second) * 3.6 if pd.notna(speed_meters_per_second) else 0.0
            marker_color = get_congestion_color(speed_kmh)
            street_name = str(jam_row.get("street", "Via"))
            formatted_time = format_time_label(jam_row.get("timestamp"))
            latitude = float(jam_row["lat"])
            longitude = float(jam_row["lon"])
            speed_label = f"{speed_kmh:.0f} km/h"

            popup_html = f"""
            <div style='min-width:180px;font-family:Arial,sans-serif;'>
                <b style='color:{marker_color}'>🚗 {speed_label}</b><br>
                🛣️ <i>{street_name}</i><br>
                🕒 {formatted_time}
            </div>
            """

            folium.CircleMarker(
                location=[latitude, longitude],
                radius=7,
                popup=folium.Popup(popup_html, max_width=220),
                tooltip=f"{speed_label} — {street_name}",
                color=marker_color,
                fill=True,
                fillColor=marker_color,
                fillOpacity=0.7,
                weight=2
            ).add_to(jam_map)

        except Exception:
            continue

    return jam_map


def generate_heatmap(dataframe_json: str) -> folium.Map | None:
    heatmap_dataframe = load_json_as_dataframe(dataframe_json)
    if heatmap_dataframe.empty:
        return None

    if "lat" not in heatmap_dataframe.columns and "y" in heatmap_dataframe.columns:
        heatmap_dataframe["lat"] = pd.to_numeric(heatmap_dataframe["y"], errors="coerce")
    if "lon" not in heatmap_dataframe.columns and "x" in heatmap_dataframe.columns:
        heatmap_dataframe["lon"] = pd.to_numeric(heatmap_dataframe["x"], errors="coerce")

    if "lat" not in heatmap_dataframe.columns or "lon" not in heatmap_dataframe.columns:
        return None

    bounded_heatmap_dataframe = filter_to_foz_bounding_box(
        heatmap_dataframe.dropna(subset=["lat", "lon"])
    )
    if bounded_heatmap_dataframe.empty:
        return None

    heatmap = create_folium_map_with_compass(
        bounded_heatmap_dataframe["lat"].mean(),
        bounded_heatmap_dataframe["lon"].mean()
    )

    heat_points = [[row["lat"], row["lon"]] for _, row in bounded_heatmap_dataframe.iterrows()]
    plugins.HeatMap(
        heat_points,
        radius=15,
        blur=10,
        min_opacity=0.35
    ).add_to(heatmap)

    return heatmap


# =========================================================
# BLOCO EXTRA — PIPELINE CIENTÍFICO
# =========================================================

def build_daily_series(
    alerts_dataframe: pd.DataFrame,
    jams_dataframe: pd.DataFrame,
    selected_category: str = "TODOS",
    categoria: str | None = None
) -> pd.Series:
    if categoria is not None:
        selected_category = categoria

    source_frames = []

    if alerts_dataframe is not None and not alerts_dataframe.empty:
        alerts_series_dataframe = alerts_dataframe.copy()
        alerts_series_dataframe["origem"] = "ALERTA"
        alerts_series_dataframe["categoria_artigo"] = (
            alerts_series_dataframe["type"]
            if "type" in alerts_series_dataframe.columns
            else "ALERTA"
        )
        source_frames.append(
            alerts_series_dataframe[["timestamp", "categoria_artigo", "origem"]]
        )

    if jams_dataframe is not None and not jams_dataframe.empty:
        jams_series_dataframe = jams_dataframe.copy()
        jams_series_dataframe["origem"] = "JAM"
        jams_series_dataframe["categoria_artigo"] = "CONGESTIONAMENTO"
        source_frames.append(
            jams_series_dataframe[["timestamp", "categoria_artigo", "origem"]]
        )

    if not source_frames:
        return pd.Series(dtype=float)

    combined_series_base = pd.concat(source_frames, ignore_index=True)
    combined_series_base["timestamp"] = pd.to_datetime(
        combined_series_base["timestamp"],
        errors="coerce"
    )
    combined_series_base = combined_series_base.dropna(subset=["timestamp"]).copy()
    combined_series_base["date"] = combined_series_base["timestamp"].dt.floor("D")

    if selected_category != "TODOS":
        combined_series_base = combined_series_base[
            combined_series_base["categoria_artigo"] == selected_category
        ]

    daily_occurrence_series = combined_series_base.groupby("date").size().sort_index()

    if daily_occurrence_series.empty:
        return pd.Series(dtype=float)

    full_date_index = pd.date_range(
        daily_occurrence_series.index.min(),
        daily_occurrence_series.index.max(),
        freq="D"
    )

    daily_occurrence_series = daily_occurrence_series.reindex(
        full_date_index,
        fill_value=0
    )
    daily_occurrence_series.index.name = "date"
    daily_occurrence_series.name = "ocorrencias"

    return daily_occurrence_series


def run_stl_analysis(time_series: pd.Series, period: int = 7):
    try:
        from statsmodels.tsa.seasonal import STL
        stl_model = STL(time_series, period=period, robust=True)
        stl_result = stl_model.fit()
        return stl_result
    except Exception:
        return None


def run_pelt_analysis(time_series: pd.Series, model: str = "l2", min_size: int = 7, jump: int = 1, pen: float = 3.0):
    try:
        import ruptures as rpt
        signal_values = time_series.values.astype(float)
        pelt_model = rpt.Pelt(model=model, min_size=min_size, jump=jump).fit(signal_values)
        breakpoints = pelt_model.predict(pen=pen)
        return breakpoints
    except Exception:
        return []


def build_descriptive_table(alerts_dataframe: pd.DataFrame, jams_dataframe: pd.DataFrame) -> pd.DataFrame:
    descriptive_blocks = []

    if alerts_dataframe is not None and not alerts_dataframe.empty:
        processed_alerts = alerts_dataframe.copy()
        processed_alerts["timestamp"] = pd.to_datetime(processed_alerts["timestamp"], errors="coerce")
        processed_alerts = processed_alerts.dropna(subset=["timestamp"])
        processed_alerts["date"] = processed_alerts["timestamp"].dt.date
        processed_alerts["hour"] = processed_alerts["timestamp"].dt.hour

        daily_counts = processed_alerts.groupby(["date", "type"]).size().reset_index(name="n")
        hourly_peaks = processed_alerts.groupby(["type", "hour"]).size().reset_index(name="n_hora")
        hourly_peak_index = hourly_peaks.groupby("type")["n_hora"].idxmax()
        peak_hour_by_type = hourly_peaks.loc[hourly_peak_index][["type", "hour"]].rename(columns={"hour": "Hora_Pico"})

        alert_summary = daily_counts.groupby("type")["n"].agg(
            Total_Alertas="sum",
            Media_Diaria="mean",
            Desvio_Padrao="std"
        ).reset_index().rename(columns={"type": "Tipo"})

        alert_summary = alert_summary.merge(
            peak_hour_by_type,
            left_on="Tipo",
            right_on="type",
            how="left"
        ).drop(columns=["type"], errors="ignore")

        descriptive_blocks.append(alert_summary)

    if jams_dataframe is not None and not jams_dataframe.empty:
        processed_jams = jams_dataframe.copy()
        processed_jams["timestamp"] = pd.to_datetime(processed_jams["timestamp"], errors="coerce")
        processed_jams = processed_jams.dropna(subset=["timestamp"])
        processed_jams["date"] = processed_jams["timestamp"].dt.date
        processed_jams["hour"] = processed_jams["timestamp"].dt.hour

        daily_jam_counts = processed_jams.groupby("date").size().reset_index(name="n")
        jam_hourly_peak = processed_jams.groupby("hour").size().reset_index(name="n_hora")
        peak_hour = int(jam_hourly_peak.loc[jam_hourly_peak["n_hora"].idxmax(), "hour"]) if not jam_hourly_peak.empty else None

        jam_summary = pd.DataFrame([{
            "Tipo": "CONGESTIONAMENTO",
            "Total_Alertas": int(daily_jam_counts["n"].sum()) if not daily_jam_counts.empty else 0,
            "Media_Diaria": float(daily_jam_counts["n"].mean()) if not daily_jam_counts.empty else 0.0,
            "Desvio_Padrao": float(daily_jam_counts["n"].std()) if not daily_jam_counts.empty else 0.0,
            "Hora_Pico": peak_hour
        }])
        descriptive_blocks.append(jam_summary)

    if not descriptive_blocks:
        return pd.DataFrame(columns=["Tipo", "Total_Alertas", "Media_Diaria", "Desvio_Padrao", "Hora_Pico"])

    descriptive_table = pd.concat(descriptive_blocks, ignore_index=True)
    descriptive_table["Media_Diaria"] = descriptive_table["Media_Diaria"].round(2)
    descriptive_table["Desvio_Padrao"] = descriptive_table["Desvio_Padrao"].round(2)
    return descriptive_table


# =========================================================
# BLOCO 4 — SIDEBAR, CARGA OPERACIONAL E FILTROS
# =========================================================

current_foz_datetime = get_current_foz_time()

st.sidebar.header("⚙️ Controles")
st.sidebar.markdown("### ⏳ Status da Sessão")
st.sidebar.markdown(
    f"🕒 **Hora atual (Foz):** `{current_foz_datetime.strftime('%d/%m/%Y %H:%M:%S')}`"
)
st.sidebar.metric("⏳ Tempo online", f"{session_elapsed_total_seconds // 3600}h:{(session_elapsed_total_seconds % 3600) // 60:02d}m")
st.sidebar.metric("⏳ Próximo ciclo", f"{minutes_until_next_refresh}:{remaining_seconds:02d}")
st.sidebar.metric("🔄 Atualizações", st.session_state.manual_refreshes)

if st.sidebar.button("🔄 ATUALIZAR DADOS AGORA", width="stretch", type="primary"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.session_state.manual_refreshes += 1
    st.rerun()

st.sidebar.divider()

try:
    raw_alerts_dataframe, raw_jams_dataframe = load_all_data()
except Exception as error:
    st.error(f"❌ Erro ao conectar com o Google Drive: {error}")
    st.markdown("""
    **Verifique:**
    - As credenciais `gcp_service_account` estão configuradas em **Settings → Secrets**
    - A Service Account tem acesso às pastas do Drive
    - Os arquivos `.h5` existem nas pastas configuradas
    """)
    st.stop()

for base_dataframe in [raw_alerts_dataframe, raw_jams_dataframe]:
    if not base_dataframe.empty and "timestamp" in base_dataframe.columns:
        if "hour" not in base_dataframe.columns:
            base_dataframe["hour"] = pd.to_datetime(base_dataframe["timestamp"], errors="coerce").dt.hour
        if "date" not in base_dataframe.columns:
            base_dataframe["date"] = pd.to_datetime(base_dataframe["timestamp"], errors="coerce").dt.date


def apply_base_time_filter(dataframe: pd.DataFrame, selected_date, selected_hour_range: tuple[int, int]) -> pd.DataFrame:
    if dataframe is None or dataframe.empty:
        return pd.DataFrame()
    if "date" not in dataframe.columns or "hour" not in dataframe.columns:
        return pd.DataFrame()

    return dataframe[
        (dataframe["date"] == selected_date) &
        (dataframe["hour"].between(selected_hour_range[0], selected_hour_range[1]))
    ].copy()


def get_clean_unique_values(series: pd.Series, invalid_values=None):
    if series is None:
        return []
    invalid_values = set(invalid_values or [])
    normalized_values = series.dropna().astype(str).str.strip()
    normalized_values = normalized_values[~normalized_values.isin(invalid_values)]
    return sorted(normalized_values.unique().tolist())


def classify_traffic_status(mean_speed_kmh: float) -> str:
    if mean_speed_kmh < 20:
        return "🔴 Crítico"
    elif mean_speed_kmh < 40:
        return "🟠 Lento"
    elif mean_speed_kmh < 60:
        return "🟡 Moderado"
    return "🟢 Fluindo"


st.sidebar.subheader("🔍 Filtros")
today_foz_date = current_foz_datetime.date()

available_dates = set()
if not raw_alerts_dataframe.empty and "date" in raw_alerts_dataframe.columns:
    available_dates.update(pd.to_datetime(raw_alerts_dataframe["date"]).dt.date.unique())
if not raw_jams_dataframe.empty and "date" in raw_jams_dataframe.columns:
    available_dates.update(pd.to_datetime(raw_jams_dataframe["date"]).dt.date.unique())

if available_dates:
    minimum_available_date = min(available_dates)
    maximum_available_date = max(available_dates)
    default_selected_date = today_foz_date if today_foz_date in available_dates else maximum_available_date
else:
    minimum_available_date = maximum_available_date = default_selected_date = today_foz_date

selected_date = st.sidebar.date_input(
    "📅 Data",
    value=default_selected_date,
    min_value=minimum_available_date,
    max_value=max(maximum_available_date, today_foz_date),
)

selected_hour_range = st.sidebar.slider("🕒 Horário", min_value=0, max_value=23, value=(0, 23))

alerts_filtered_by_date = apply_base_time_filter(raw_alerts_dataframe, selected_date, selected_hour_range)
jams_filtered_by_date = apply_base_time_filter(raw_jams_dataframe, selected_date, selected_hour_range)

available_incident_types = (
    get_clean_unique_values(alerts_filtered_by_date["type"])
    if not alerts_filtered_by_date.empty and "type" in alerts_filtered_by_date.columns
    else []
)

selected_incident_types = st.sidebar.multiselect(
    "🚨 Tipo",
    options=available_incident_types,
    default=available_incident_types
)

incident_subtype_base = alerts_filtered_by_date.copy()
if selected_incident_types and "type" in incident_subtype_base.columns:
    incident_subtype_base = incident_subtype_base[incident_subtype_base["type"].isin(selected_incident_types)]

available_incident_subtypes = (
    get_clean_unique_values(incident_subtype_base["subtype"], invalid_values=["nan", ""])
    if not incident_subtype_base.empty and "subtype" in incident_subtype_base.columns
    else []
)

selected_incident_subtypes = st.sidebar.multiselect(
    "🔍 Natureza",
    options=available_incident_subtypes,
    default=available_incident_subtypes
)

street_filter_base = incident_subtype_base.copy()
if selected_incident_subtypes and "subtype" in street_filter_base.columns:
    street_filter_base = street_filter_base[street_filter_base["subtype"].isin(selected_incident_subtypes)]

available_streets = (
    get_clean_unique_values(street_filter_base["street"], invalid_values=["NA", "nan", "", "N/A"])
    if not street_filter_base.empty and "street" in street_filter_base.columns
    else []
)

selected_street = st.sidebar.selectbox("🛣️ Rua", options=["(Todas)"] + available_streets, index=0)
selected_street = "" if selected_street == "(Todas)" else selected_street

minimum_speed_kmh = 0.0
maximum_speed_kmh = 120.0

if not jams_filtered_by_date.empty and "speed" in jams_filtered_by_date.columns:
    speed_values_kmh = jams_filtered_by_date["speed"].dropna() * 3.6
    if not speed_values_kmh.empty:
        minimum_speed_kmh = max(0.0, float(speed_values_kmh.min()))
        maximum_speed_kmh = max(5.0, float(speed_values_kmh.max()))

selected_speed_range_kmh = st.sidebar.slider(
    "🚗 Velocidade (km/h)",
    min_value=0.0,
    max_value=max(120.0, maximum_speed_kmh),
    value=(minimum_speed_kmh, max(minimum_speed_kmh, min(120.0, maximum_speed_kmh))),
    step=5.0,
)

if (
    not jams_filtered_by_date.empty
    and "speed" in jams_filtered_by_date.columns
    and jams_filtered_by_date["speed"].notna().any()
):
    mean_speed_kmh = jams_filtered_by_date["speed"].mean() * 3.6
    total_jams_in_period = len(jams_filtered_by_date)
    traffic_status_label = classify_traffic_status(mean_speed_kmh)

    st.sidebar.markdown("---")
    st.sidebar.markdown("**📊 Congestionamentos em** " + selected_date.strftime("%d/%m"))
    st.sidebar.metric("Vel. Média", f"{mean_speed_kmh:.1f} km/h", delta=traffic_status_label)
    st.sidebar.metric("Total de Jams", total_jams_in_period)
else:
    st.sidebar.info(f"Sem dados de congestionamento em {selected_date.strftime('%d/%m')}.")

filtered_alerts_dataframe = apply_base_time_filter(raw_alerts_dataframe, selected_date, selected_hour_range)

if not filtered_alerts_dataframe.empty:
    if selected_incident_types and "type" in filtered_alerts_dataframe.columns:
        filtered_alerts_dataframe = filtered_alerts_dataframe[filtered_alerts_dataframe["type"].isin(selected_incident_types)]
    if selected_incident_subtypes and "subtype" in filtered_alerts_dataframe.columns:
        filtered_alerts_dataframe = filtered_alerts_dataframe[filtered_alerts_dataframe["subtype"].isin(selected_incident_subtypes)]
    if selected_street and "street" in filtered_alerts_dataframe.columns:
        filtered_alerts_dataframe = filtered_alerts_dataframe[filtered_alerts_dataframe["street"] == selected_street]

filtered_jams_dataframe = apply_base_time_filter(raw_jams_dataframe, selected_date, selected_hour_range)

if not filtered_jams_dataframe.empty and "speed" in filtered_jams_dataframe.columns:
    filtered_jams_dataframe = filtered_jams_dataframe[
        (filtered_jams_dataframe["speed"].fillna(0) * 3.6).between(
            selected_speed_range_kmh[0],
            selected_speed_range_kmh[1]
        )
    ]

dashboard_alerts_base = filtered_alerts_dataframe.copy()
dashboard_jams_base = filtered_jams_dataframe.copy()


# =========================================================
# UPGRADE — ALGORITMO MULTICRITÉRIO (MCDA) E MODELO PREDITIVO
# =========================================================

def calculate_road_criticality(alerts_dataframe, jams_dataframe):
    if jams_dataframe.empty:
        return pd.DataFrame(columns=["street", "Volume_Jams", "Atraso_Medio_Seg", "Criticidade_Index"])

    aggregation_rules = {"Volume_Jams": ("street", "count")}
    if "delay" in jams_dataframe.columns:
        aggregation_rules["Atraso_Medio_Seg"] = ("delay", "mean")
    if "length" in jams_dataframe.columns:
        aggregation_rules["Comprimento_Medio_M"] = ("length", "mean")

    street_criticality_dataframe = jams_dataframe.groupby("street").agg(**aggregation_rules).reset_index()

    if "Atraso_Medio_Seg" not in street_criticality_dataframe.columns:
        street_criticality_dataframe["Atraso_Medio_Seg"] = 0.0
    if "Comprimento_Medio_M" not in street_criticality_dataframe.columns:
        street_criticality_dataframe["Comprimento_Medio_M"] = 0.0

    maximum_jam_volume = street_criticality_dataframe["Volume_Jams"].max() or 1
    maximum_average_delay = street_criticality_dataframe["Atraso_Medio_Seg"].max() or 1

    street_criticality_dataframe["Criticidade_Index"] = (
        (street_criticality_dataframe["Volume_Jams"] / maximum_jam_volume) * 0.4 +
        (street_criticality_dataframe["Atraso_Medio_Seg"] / maximum_average_delay) * 0.6
    ) * 100

    return street_criticality_dataframe.sort_values("Criticidade_Index", ascending=False)


def predict_traffic_delay_impact(queue_length_meters: float) -> float:
    angular_coefficient = 0.15
    intercept_seconds = 12.0
    return (queue_length_meters * angular_coefficient) + intercept_seconds


road_criticality_dataframe = calculate_road_criticality(dashboard_alerts_base, dashboard_jams_base)


# =========================================================
# BLOCO 5 — CABEÇALHO, RESUMO, KPIs E INDICADORES
# =========================================================

def classify_risk_level(total_incidents: int):
    if total_incidents >= 15:
        return "Crítico", "🔴", "Volume muito alto de incidentes no período filtrado."
    elif total_incidents >= 10:
        return "Alto", "🟠", "Quantidade elevada de ocorrências; atenção operacional recomendada."
    elif total_incidents >= 5:
        return "Moderado", "🟡", "Ocorrências acima do nível de normalidade para o recorte atual."
    return "Baixo", "🟢", "Baixa pressão operacional no período filtrado."


def classify_flow_status(mean_speed_kmh: float):
    if mean_speed_kmh < 20:
        return "Travado", "🔴", "Fluxo muito comprometido, com forte retenção nas vias."
    elif mean_speed_kmh < 40:
        return "Lento", "🟠", "Tráfego com perda relevante de fluidez."
    elif mean_speed_kmh < 60:
        return "Moderado", "🟡", "Fluxo estável, mas com redução perceptível de velocidade."
    return "Fluindo", "🟢", "Boas condições de circulação no recorte selecionado."


def classify_overall_road_status(total_incidents: int) -> str:
    if total_incidents >= 15:
        return "🚫 Crítico"
    elif total_incidents >= 5:
        return "⚠️ Moderado"
    return "✅ Normal"


def build_selection_label(selected_values, total_available, singular_name, plural_name):
    if not selected_values or len(selected_values) == total_available:
        return "Todos" if plural_name == "tipos" else "Todas"
    if len(selected_values) <= 2:
        return ", ".join(selected_values)
    return f"{len(selected_values)} {plural_name}"


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
      <img src="https://cdn.simpleicons.org/waze/33CCC5" width="36" height="36"
           style="vertical-align:middle;margin-right:8px;" alt="Waze for Cities">
      Monitoramento de Tráfego
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
      🕒 Hora local: <strong style="color:#94a3b8;">{current_foz_datetime.strftime('%H:%M:%S')}</strong>
      &nbsp;·&nbsp;
      🔄 Atualização automática a cada 10 minutes
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
      <span>💻 <strong style="color:#64748b;">LACA</strong> — Laboratório de Computação Aplicada</span>
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

st.markdown("""
<div style="
    background:#FFFFFF;
    border:1px solid #E2E8F0;
    border-radius:12px;
    padding:16px 18px;
    margin-bottom:16px;
    box-shadow:0 1px 4px rgba(15,23,42,0.04);
">
    <div style="font-size:15px;font-weight:700;color:#0F172A;margin-bottom:6px;">
        Sobre o Sistema
    </div>
    <div style="font-size:14px;line-height:1.7;color:#475569;">
        Este sistema mostra o monitoramento de incidentes viários e congestionamentos em Foz do Iguaçu com base em dados do Waze.
        Os painéis reúnem mapas, filtros e indicadores para apoiar análises espaciais, temporais e históricas da mobilidade urbana.
        Os dados podem ser explorados por tipo de ocorrência, natureza, via, horário e intensidade do tráfego.
    </div>
</div>
""", unsafe_allow_html=True)

selected_type_label = build_selection_label(selected_incident_types, len(available_incident_types), "tipo", "tipos")
selected_subtype_label = build_selection_label(selected_incident_subtypes, len(available_incident_subtypes), "natureza", "naturezas")

filter_col_1, filter_col_2, filter_col_3, filter_col_4, filter_col_5 = st.columns(5)
filter_col_1.metric("📅 Data", selected_date.strftime("%d/%m/%Y"))
filter_col_2.metric("🚨 Tipo", selected_type_label)
filter_col_3.metric("🔍 Natureza", selected_subtype_label)
filter_col_4.metric("Road", selected_street if selected_street else "Todas")
filter_col_5.metric("🕒 Horário", f"{selected_hour_range[0]:02d}h – {selected_hour_range[1]:02d}h")

st.caption(
    f"🔍 Filtros ativos → {len(filtered_alerts_dataframe)} incidente(s) exibidos em "
    f"{selected_date.strftime('%d/%m/%Y')} | Congestionamentos: {len(filtered_jams_dataframe)}"
)

st.markdown("---")
st.subheader("📊 Resumo Estatístico")

total_incidents_in_period = len(filtered_alerts_dataframe)
total_accidents_in_period = (
    len(filtered_alerts_dataframe[filtered_alerts_dataframe["type"] == "ACIDENTE"])
    if not filtered_alerts_dataframe.empty and "type" in filtered_alerts_dataframe.columns
    else 0
)

mean_speed_in_period_kmh = (
    filtered_jams_dataframe["speed"].mean() * 3.6
    if not filtered_jams_dataframe.empty
    and "speed" in filtered_jams_dataframe.columns
    and filtered_jams_dataframe["speed"].notna().any()
    else 0
)

overall_road_status = classify_overall_road_status(total_incidents_in_period)

kpi_col_1, kpi_col_2, kpi_col_3, kpi_col_4 = st.columns(4)
kpi_col_1.metric("Total Alertas", total_incidents_in_period)
kpi_col_2.metric("Acidentes", total_accidents_in_period)
kpi_col_3.metric("Vel. Média", f"{mean_speed_in_period_kmh:.1f} km/h")
kpi_col_4.metric("Status da Via", overall_road_status)

most_critical_street = road_criticality_dataframe.iloc[0]["street"] if not road_criticality_dataframe.empty else "Nenhuma"
st.caption(f"🔴 Gargalo Operacional Prioritário (MCDA): **{most_critical_street}**")

st.markdown("---")
st.subheader("📈 Indicadores de Gravidade")

risk_level_name, risk_level_icon, risk_level_description = classify_risk_level(total_incidents_in_period)
flow_status_name, flow_status_icon, flow_status_description = classify_flow_status(mean_speed_in_period_kmh)

risk_col, flow_col = st.columns(2)

with risk_col:
    with st.container(border=True):
        st.markdown(f"### {risk_level_icon} Risco operacional")
        st.metric("Classificação", risk_level_name)
        st.metric("Incidentes no período", total_incidents_in_period)
        st.caption(risk_level_description)
        st.write(f"🚨 Acidentes: {total_accidents_in_period}")
        st.write(f"📍 Status geral: {overall_road_status}")
        st.caption("Faixas: 0–4 = Baixo · 5–9 = Moderado · 10–14 = Alto · 15+ = Crítico")

with flow_col:
    with st.container(border=True):
        st.markdown(f"### {flow_status_icon} Condição do tráfego")
        st.metric("Classificação", flow_status_name)
        st.metric("Velocidade média", f"{mean_speed_in_period_kmh:.1f} km/h")
        st.caption(flow_status_description)
        st.write(f"🚗 Média observada: {mean_speed_in_period_kmh:.1f} km/h")
        st.write(f"📍 Total de jams: {len(filtered_jams_dataframe)}")
        st.caption("Faixas: <20 = Travado · 20–39 = Lento · 40–59 = Moderado · 60+ = Fluindo")

st.caption(
    "Os indicadores acima resumem o comportamento do período filtrado: "
    "o risco operacional considera o volume de incidentes, enquanto a condição "
    "do tráfego é baseada na velocidade média observada nos congestionamentos."
)

st.markdown("---")
# =========================================================
# BLOCO EXTRA — ANÁLISE TEMPORAL ANUAL DE BURACOS (PLANILHA)
# =========================================================

ANNUAL_YEARS_DEFAULT = [2024, 2025, 2026]
TOP_STREETS_PER_YEAR = 5
MAX_MARKERS_PER_STREET = 200
NOMINATIM_SLEEP_SECONDS = 1.2
LOCAL_ALERT_CSV_PATH = "Waze for Cities Data _ tabelas alertas_20240101_20260306.csv"

POTHOLE_SUBTYPE_VALUES = {
    "BURACO NA VIA",
    "HAZARD_ON_ROAD_POT_HOLE"
}


def standardize_alert_spreadsheet_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe is None or dataframe.empty:
        return pd.DataFrame()

    standardized_dataframe = dataframe.copy()
    standardized_dataframe.columns = [str(column).strip() for column in standardized_dataframe.columns]

    rename_map = {}
    for column_name in standardized_dataframe.columns:
        lower_name = column_name.lower().strip()

        if lower_name == "street":
            rename_map[column_name] = "street"
        elif lower_name == "city":
            rename_map[column_name] = "city"
        elif lower_name == "location":
            rename_map[column_name] = "location"
        elif lower_name == "subtype":
            rename_map[column_name] = "subtype"
        elif lower_name == "type":
            rename_map[column_name] = "type"
        elif lower_name == "date":
            rename_map[column_name] = "Date"
        elif lower_name == "pubmillis":
            rename_map[column_name] = "pubMillis"

    standardized_dataframe = standardized_dataframe.rename(columns=rename_map)
    return standardized_dataframe


def parse_portuguese_date(date_value):
    if pd.isna(date_value):
        return pd.NaT

    date_text = str(date_value).strip()

    month_map = {
        'jan.': 'Jan', 'fev.': 'Feb', 'mar.': 'Mar', 'abr.': 'Apr',
        'maio': 'May', 'mai.': 'May', 'jun.': 'Jun', 'jul.': 'Jul', 'ago.': 'Aug',
        'set.': 'Sep', 'out.': 'Oct', 'nov.': 'Nov', 'dez.': 'Dec'
    }

    for pt_abbreviation, en_month in month_map.items():
        date_text = date_text.replace(pt_abbreviation, en_month)

    return pd.to_datetime(date_text, format='%d de %b de %Y', errors='coerce')


def normalize_spreadsheet_timestamps(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe is None or dataframe.empty:
        return pd.DataFrame()

    normalized_dataframe = dataframe.copy()

    if "pubMillis" in normalized_dataframe.columns:
        normalized_dataframe["timestamp"] = pd.to_datetime(
            normalized_dataframe["pubMillis"],
            unit="ms",
            errors="coerce",
            utc=True
        ).dt.tz_convert("America/Sao_Paulo").dt.tz_localize(None)

    elif "Date" in normalized_dataframe.columns:
        normalized_dataframe["timestamp"] = normalized_dataframe["Date"].apply(parse_portuguese_date)

    elif "timestamp" in normalized_dataframe.columns:
        normalized_dataframe["timestamp"] = pd.to_datetime(normalized_dataframe["timestamp"], errors="coerce")

    else:
        normalized_dataframe["timestamp"] = pd.NaT

    normalized_dataframe = normalized_dataframe.dropna(subset=["timestamp"]).copy()

    if normalized_dataframe.empty:
        return normalized_dataframe

    normalized_dataframe["date"] = normalized_dataframe["timestamp"].dt.date
    normalized_dataframe["hour"] = normalized_dataframe["timestamp"].dt.hour
    normalized_dataframe["day_of_week"] = normalized_dataframe["timestamp"].dt.day_name()
    normalized_dataframe["year"] = normalized_dataframe["timestamp"].dt.year

    return normalized_dataframe


def extract_wkt_point_coordinates(location_value):
    if pd.isna(location_value):
        return None, None

    location_text = str(location_value)
    point_match = re.search(r'Point\(([-+]?\d+\.?\d*)\s+([-+]?\d+\.?\d*)\)', location_text)

    if point_match:
        longitude = float(point_match.group(1))
        latitude = float(point_match.group(2))
        return latitude, longitude

    return None, None


def extract_spreadsheet_coordinates(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe is None or dataframe.empty:
        return pd.DataFrame()

    coordinates_dataframe = dataframe.copy()

    if "location" in coordinates_dataframe.columns:
        extracted_coordinates = coordinates_dataframe["location"].apply(
            lambda location_value: pd.Series(
                extract_wkt_point_coordinates(location_value),
                index=["latitude", "longitude"]
            )
        )
        coordinates_dataframe["latitude"] = extracted_coordinates["latitude"]
        coordinates_dataframe["longitude"] = extracted_coordinates["longitude"]

    return coordinates_dataframe


def normalize_pothole_subtype_labels(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe is None or dataframe.empty:
        return pd.DataFrame()

    normalized_dataframe = dataframe.copy()

    if "subtype" in normalized_dataframe.columns:
        normalized_dataframe["subtype"] = normalized_dataframe["subtype"].replace({
            "HAZARD_ON_ROAD_POT_HOLE": "BURACO NA VIA"
        })

    return normalized_dataframe


def sample_street_points(dataframe: pd.DataFrame, max_points: int) -> pd.DataFrame:
    if dataframe is None or dataframe.empty:
        return pd.DataFrame()
    if len(dataframe) <= max_points:
        return dataframe.copy()
    return dataframe.sample(n=max_points, random_state=42).copy()


@st.cache_data(ttl=3600, show_spinner="📄 Carregando planilha histórica de alertas...")
def load_alert_spreadsheet_for_annual_analysis(csv_path: str = LOCAL_ALERT_CSV_PATH) -> pd.DataFrame:
    spreadsheet_dataframe = pd.read_csv(csv_path)
    spreadsheet_dataframe = standardize_alert_spreadsheet_columns(spreadsheet_dataframe)
    spreadsheet_dataframe = normalize_spreadsheet_timestamps(spreadsheet_dataframe)
    spreadsheet_dataframe = normalize_pothole_subtype_labels(spreadsheet_dataframe)
    spreadsheet_dataframe = extract_spreadsheet_coordinates(spreadsheet_dataframe)

    if "street" not in spreadsheet_dataframe.columns:
        spreadsheet_dataframe["street"] = pd.NA
    if "city" not in spreadsheet_dataframe.columns:
        spreadsheet_dataframe["city"] = "Foz do Iguaçu"

    return spreadsheet_dataframe


@st.cache_data(ttl=86400, show_spinner=False)
def get_street_geometry_from_nominatim(street_name: str, city_name: str, country_name: str = "Brazil"):
    search_query = f"{street_name}, {city_name}, {country_name}"
    request_url = "https://nominatim.openstreetmap.org/search"
    request_params = {
        "q": search_query,
        "format": "json",
        "limit": 1,
        "polygon_geojson": 1
    }
    request_headers = {
        "User-Agent": "WazeFozAnnualStreetAnalysis/1.0"
    }

    try:
        response = requests.get(request_url, params=request_params, headers=request_headers, timeout=20)
        response.raise_for_status()
        response_data = response.json()

        if not response_data:
            return None

        geojson_data = response_data[0].get("geojson")
        if not geojson_data:
            return None

        geometry_type = geojson_data.get("type")

        if geometry_type == "LineString":
            return [[coordinate[1], coordinate[0]] for coordinate in geojson_data["coordinates"]]

        if geometry_type == "MultiLineString":
            merged_coordinates = []
            for segment in geojson_data["coordinates"]:
                merged_coordinates.extend([[coordinate[1], coordinate[0]] for coordinate in segment])
            return merged_coordinates if merged_coordinates else None

        return None

    except Exception:
        return None


def build_top_streets_by_year(dataframe: pd.DataFrame, year_value: int, top_n: int = 5) -> pd.DataFrame:
    if dataframe is None or dataframe.empty:
        return pd.DataFrame(columns=["street", "city", "pothole_count"])

    year_dataframe = dataframe[dataframe["year"] == year_value].copy()
    if year_dataframe.empty:
        return pd.DataFrame(columns=["street", "city", "pothole_count"])

    if "subtype" not in year_dataframe.columns:
        return pd.DataFrame(columns=["street", "city", "pothole_count"])

    potholes_dataframe = year_dataframe[
        year_dataframe["subtype"].astype(str).str.upper().isin(POTHOLE_SUBTYPE_VALUES)
    ].copy()

    if potholes_dataframe.empty:
        return pd.DataFrame(columns=["street", "city", "pothole_count"])

    potholes_dataframe = potholes_dataframe.dropna(subset=["street"]).copy()
    potholes_dataframe["street"] = potholes_dataframe["street"].astype(str).str.strip()
    potholes_dataframe["city"] = potholes_dataframe["city"].fillna("Foz do Iguaçu").astype(str).str.strip()

    potholes_dataframe = potholes_dataframe[
        potholes_dataframe["street"].notna() &
        (~potholes_dataframe["street"].isin(["", "nan", "N/A", "NA"]))
    ]

    if potholes_dataframe.empty:
        return pd.DataFrame(columns=["street", "city", "pothole_count"])

    top_streets_dataframe = (
        potholes_dataframe
        .groupby(["street", "city"])
        .size()
        .reset_index(name="pothole_count")
        .sort_values("pothole_count", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )

    return top_streets_dataframe


def build_annual_pothole_map(dataframe: pd.DataFrame, year_value: int, top_n: int = 5):
    top_streets_dataframe = build_top_streets_by_year(dataframe, year_value, top_n=top_n)

    if top_streets_dataframe.empty:
        return None, top_streets_dataframe

    if dataframe is None or dataframe.empty:
        return None, top_streets_dataframe

    required_columns = {"year", "subtype"}
    if not required_columns.issubset(dataframe.columns):
        return None, top_streets_dataframe

    annual_dataframe = dataframe[
        (dataframe["year"] == year_value) &
        (dataframe["subtype"].astype(str).str.upper().isin(POTHOLE_SUBTYPE_VALUES))
    ].copy()

    if annual_dataframe.empty:
        return None, top_streets_dataframe

    if "city" not in annual_dataframe.columns:
        annual_dataframe["city"] = "Foz do Iguaçu"

    coordinate_columns = [
        column_name
        for column_name in ["latitude", "longitude"]
        if column_name in annual_dataframe.columns
    ]

    if len(coordinate_columns) == 2:
        annual_dataframe["latitude"] = pd.to_numeric(annual_dataframe["latitude"], errors="coerce")
        annual_dataframe["longitude"] = pd.to_numeric(annual_dataframe["longitude"], errors="coerce")
        annual_dataframe = annual_dataframe.dropna(subset=coordinate_columns).copy()

    street_geometry_registry = {}
    map_bounds = []

    for _, street_row in top_streets_dataframe.iterrows():
        street_name = street_row["street"]
        city_name = street_row["city"]
        pothole_count = int(street_row["pothole_count"])

        street_geometry = get_street_geometry_from_nominatim(street_name, city_name)
        if street_geometry and len(street_geometry) >= 2:
            street_geometry_registry[(street_name, city_name)] = {
                "geometry": street_geometry,
                "pothole_count": pothole_count
            }
            map_bounds.extend(street_geometry)

    if street_geometry_registry:
        initial_key = list(street_geometry_registry.keys())[0]
        initial_point = street_geometry_registry[initial_key]["geometry"][0]
        annual_map = folium.Map(
            location=[initial_point[0], initial_point[1]],
            zoom_start=13,
            tiles="OpenStreetMap"
        )
    else:
        if len(coordinate_columns) < 2 or annual_dataframe.empty:
            return None, top_streets_dataframe

        fallback_dataframe = annual_dataframe.dropna(subset=["latitude", "longitude"]).copy()
        if fallback_dataframe.empty:
            return None, top_streets_dataframe

        annual_map = folium.Map(
            location=[fallback_dataframe["latitude"].mean(), fallback_dataframe["longitude"].mean()],
            zoom_start=13,
            tiles="OpenStreetMap"
        )

    for (street_name, city_name), geometry_data in street_geometry_registry.items():
        street_group = folium.FeatureGroup(
            name=f"Rua: {street_name} ({city_name})",
            show=True
        )

        folium.PolyLine(
            locations=geometry_data["geometry"],
            color="blue",
            weight=5,
            opacity=0.75,
            tooltip=(
                f"<b>Rua:</b> {street_name}<br>"
                f"<b>Cidade:</b> {city_name}<br>"
                f"<b>Buracos:</b> {geometry_data['pothole_count']}"
            )
        ).add_to(street_group)

        if len(coordinate_columns) == 2:
            street_points_dataframe = annual_dataframe[
                (annual_dataframe["street"] == street_name) &
                (annual_dataframe["city"] == city_name)
            ].dropna(subset=["latitude", "longitude"]).copy()
        else:
            street_points_dataframe = pd.DataFrame()

        sampled_street_points = sample_street_points(street_points_dataframe, MAX_MARKERS_PER_STREET)

        marker_cluster = MarkerCluster(
            name=f"Buracos em {street_name}",
            disableClusteringAtZoom=17
        ).add_to(street_group)

        for _, point_row in sampled_street_points.iterrows():
            popup_text = (
                f"Rua: {point_row.get('street', 'N/D')}<br>"
                f"Data: {point_row.get('Date', point_row.get('date', 'N/D'))}<br>"
                f"Tipo: {point_row.get('subtype', 'N/D')}"
            )

            folium.CircleMarker(
                location=[point_row["latitude"], point_row["longitude"]],
                radius=4,
                color="darkred",
                fill=True,
                fill_color="red",
                fill_opacity=0.75,
                popup=popup_text
            ).add_to(marker_cluster)

        street_group.add_to(annual_map)

    if map_bounds:
        annual_map.fit_bounds(map_bounds)
    else:
        if len(coordinate_columns) == 2 and not annual_dataframe.empty:
            valid_points = annual_dataframe.dropna(subset=["latitude", "longitude"]).copy()
            if not valid_points.empty:
                annual_map.fit_bounds(valid_points[["latitude", "longitude"]].values.tolist())

    folium.LayerControl(collapsed=False).add_to(annual_map)
    return annual_map, top_streets_dataframe

# =========================================================
# BLOCO 6 — VISUALIZAÇÕES PRINCIPAIS
# =========================================================
# =========================================================
# COMPATIBILIZAÇÃO DE NOMES PARA O BLOCO 6
# =========================================================
df_filtered = filtered_alerts_dataframe.copy() if "filtered_alerts_dataframe" in locals() else pd.DataFrame()
df_jams_filtered = filtered_jams_dataframe.copy() if "filtered_jams_dataframe" in locals() else pd.DataFrame()

df_alerts_raw = raw_alerts_dataframe.copy() if "raw_alerts_dataframe" in locals() else pd.DataFrame()
df_jams_raw = raw_jams_dataframe.copy() if "raw_jams_dataframe" in locals() else pd.DataFrame()

hora_range = selected_hour_range if "selected_hour_range" in locals() else (0, 23)
filtro_tipo = selected_incident_types if "selected_incident_types" in locals() else []
filtro_natureza = selected_incident_subtypes if "selected_incident_subtypes" in locals() else []
filtro_rua = selected_street if "selected_street" in locals() and selected_street else None

df_criticidade_vias = road_criticality_dataframe.copy() if "road_criticality_dataframe" in locals() else pd.DataFrame()
selected_date = selected_date if "selected_date" in locals() else datetime.now().date()
st.subheader("🗺️ Visualizações")

(
    tab_inc,
    tab_jams,
    tab_calor,
    tab_temporal_danos,
    tab_temporal_anual,
    tab_graficos,
    tab_pipeline,
    tab_criticidade,
    tab_predicao,
    tab_dados
) = st.tabs(
    [
        "Incidentes",
        "Congestionamentos",
        "Mapa de Calor",
        "📅 Análise Temporal",
        "🗺️ Análisis Temporal Anual",
        "Gráficos",
        "🧪 Pipeline Científico",
        "📊 Criticidade (MCDA)",
        "🔮 Modelo Preditivo",
        "Dados"
    ]
)

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
            | 💗 | Acidente leve / Baixa gravidade |
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

with tab_calor:
    st.subheader("🔥 Zonas de Concentração de Incidentes")

    if not df_filtered.empty:
        df_heat = df_filtered.copy()

        if {"lat", "lon"}.issubset(df_heat.columns):
            df_heat = df_heat.dropna(subset=["lat", "lon"])
            df_heat = df_heat[
    df_heat["lat"].between(FOZ_LATITUDE_MIN, FOZ_LATITUDE_MAX) &
    df_heat["lon"].between(FOZ_LONGITUDE_MIN, FOZ_LONGITUDE_MAX)
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

with tab_temporal_danos:
    st.subheader("📅 Análise Temporal de Patologias Viárias")
    st.markdown("""
    Esta seção exibe o perfil de distribuição e reincidência de anomalias viárias nos arquivos ativos carregados atualmente.
    """)
    if not df_alerts_raw.empty:
        subtipos = clean_unique_values(df_alerts_raw["subtype"], invalid_values=["nan", ""])
        subtipo_sel = st.selectbox("Selecione a natureza do dano:", subtipos, key="sel_dano_temporal")

        df_sub = df_alerts_raw[df_alerts_raw["subtype"] == subtipo_sel]
        if not df_sub.empty:
            fig_temp = px.histogram(
                df_sub,
                x="hour",
                nbins=24,
                color_discrete_sequence=['#dc2626'],
                title=f"Distribuição Horária Total de: {subtipo_sel}",
                labels={"hour": "Hora do Dia (Recorte Atual)", "count": "Volume de Alertas"}
            )
            st.plotly_chart(fig_temp, use_container_width=True)
        else:
            st.info("Sem registros para a patologia selecionada na data ativa.")
    else:
        st.warning("Base de dados de alertas vazia ou indisponível.")

with tab_temporal_anual:
    st.subheader("🗺️ Análisis Temporal Anual — Top ruas com mais buracos")
    st.caption(
        "Esta aba usa somente a planilha histórica de alertas para identificar, por ano, "
        "as ruas com maior número de reportes de BURACO NA VIA e exibi-las em mapa com geometrias."
    )

    col_anual_1, col_anual_2 = st.columns([1, 1])

    with col_anual_1:
        anos_selecionados = st.multiselect(
            "Selecione os anos para análise",
            options=ANNUAL_YEARS_DEFAULT,
            default=ANNUAL_YEARS_DEFAULT,
            key="annual_pothole_years"
        )

    with col_anual_2:
        top_n_ruas = st.slider(
            "Número de ruas por ano",
            min_value=3,
            max_value=10,
            value=5,
            step=1,
            key="annual_top_streets_slider"
        )

    try:
        df_alertas_planilha_anual = load_alert_spreadsheet_for_annual_analysis(LOCAL_ALERT_CSV_PATH)
    except FileNotFoundError:
        st.error(
            f"Não foi possível localizar a planilha local em: `{LOCAL_ALERT_CSV_PATH}`. "
            "Ajuste o caminho do arquivo CSV no código."
        )
        st.stop()
    except Exception as erro_planilha:
        st.error(f"Erro ao carregar a planilha histórica: {erro_planilha}")
        st.stop()

    if df_alertas_planilha_anual.empty:
        st.warning("A planilha foi carregada, mas não há dados válidos para análise anual.")
    else:
        df_buracos_historico = df_alertas_planilha_anual.copy()

        if "subtype" not in df_buracos_historico.columns:
            st.warning("A planilha não possui a coluna `subtype/Subtype`, necessária para identificar buracos.")
        else:
            df_buracos_historico = df_buracos_historico[
                df_buracos_historico["subtype"].astype(str).str.upper().isin(POTHOLE_SUBTYPE_VALUES)
            ].copy()

            if df_buracos_historico.empty:
                st.info("Não foram encontrados registros de 'BURACO NA VIA' na planilha histórica.")
            else:
                anos_disponiveis_historico = sorted(
                    df_buracos_historico["year"].dropna().astype(int).unique().tolist()
                )

                if not anos_disponiveis_historico:
                    st.info("Não há anos válidos na planilha para análise.")
                else:
                    anos_para_renderizar = [
                        ano for ano in anos_selecionados
                        if ano in anos_disponiveis_historico
                    ]

                    if not anos_para_renderizar:
                        st.info("Nenhum dos anos selecionados possui dados de buracos na planilha.")
                    else:
                        for ano_analise in anos_para_renderizar:
                            st.markdown("---")
                            st.markdown(f"### Ano {ano_analise}")

                            mapa_anual, top_ruas_ano = build_annual_pothole_map(
                                df_buracos_historico,
                                ano_analise,
                                top_n=top_n_ruas
                            )

                            col_resumo_1, col_resumo_2 = st.columns([2, 1])

                            with col_resumo_1:
                                if top_ruas_ano.empty:
                                    st.info(f"Sem ruas classificadas para {ano_analise}.")
                                else:
                                    top_ruas_ano_exibir = top_ruas_ano.copy()
                                    top_ruas_ano_exibir.columns = ["Rua", "Cidade", "Contagem de Buracos"]

                                    st.dataframe(
                                        top_ruas_ano_exibir,
                                        hide_index=True,
                                        use_container_width=True
                                    )

                                    fig_top_ruas_ano = px.bar(
                                        top_ruas_ano_exibir.sort_values("Contagem de Buracos", ascending=True),
                                        x="Contagem de Buracos",
                                        y="Rua",
                                        orientation="h",
                                        color="Contagem de Buracos",
                                        color_continuous_scale="magma",
                                        title=f"Top {top_n_ruas} ruas com mais reportes de buracos — {ano_analise}"
                                    )
                                    fig_top_ruas_ano.update_layout(height=360, coloraxis_showscale=False)
                                    st.plotly_chart(fig_top_ruas_ano, use_container_width=True)

                            with col_resumo_2:
                                total_buracos_ano = int(
                                    df_buracos_historico[df_buracos_historico["year"] == ano_analise].shape[0]
                                )
                                total_representado_top = int(
                                    top_ruas_ano["pothole_count"].sum()
                                ) if not top_ruas_ano.empty else 0

                                st.metric("Ano analisado", ano_analise)
                                st.metric("Buracos no ano", total_buracos_ano)
                                st.metric("Top ruas somadas", total_representado_top)

                            if mapa_anual is not None:
                                st_folium(
                                    mapa_anual,
                                    width="100%",
                                    height=560,
                                    key=f"annual_pothole_map_{ano_analise}"
                                )
                            else:
                                st.warning(
                                    f"Não foi possível montar o mapa de {ano_analise}. "
                                    "Talvez faltem geometrias do Nominatim ou coordenadas válidas na planilha."
                                )

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
                    lambda r: r["subtype"] if r["subtype"] != "" else r["type"],
                    axis=1
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

    serie = build_daily_series(
    df_alerts_raw,
    df_jams_raw,
    selected_category=categoria_artigo
)

    if serie.empty:
        st.info("Sem dados suficientes para montar a série temporal.")
    else:
        st.markdown("### Série diária")
        df_serie = serie.reset_index()
        df_serie.columns = ["Data", "Ocorrências"]

        fig_ts = px.line(
            df_serie,
            x="Data",
            y="Ocorrências",
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
            "Baixar CSV — Tabela 1",
            data=csv_desc,
            file_name="tabela_1_estatisticas_descritivas.csv",
            mime="text/csv"
        )
    else:
        st.info("Sem dados suficientes para a tabela descritiva.")

with tab_criticidade:
    st.subheader("📊 Classificação Hierárquica de Infraestrutura Viária Crítica")
    st.markdown("""
    Análise multicritério ponderando **volume de congestionamentos** e **atraso médio (s)**.
    Permite à **Foztrans** priorizar envio de agentes ou investimentos nas vias de maior peso operacional.
    """)

    if not df_criticidade_vias.empty:
        col_t1, col_t2 = st.columns([3, 2])

        with col_t1:
            fig_crit = px.bar(
                df_criticidade_vias.head(10),
                x="Criticidade_Index",
                y="street",
                orientation="h",
                title="Top 10 Vias Críticas — Intervenção Prioritária",
                labels={"Criticidade_Index": "Índice de Criticidade (0–100)", "street": "Logradouro"},
                color="Criticidade_Index",
                color_continuous_scale="Oranges"
            )
            fig_crit.update_layout(height=400)
            st.plotly_chart(fig_crit, use_container_width=True)

        with col_t2:
            st.markdown("#### Ranking de Prioridade Viária")
            st.dataframe(
                df_criticidade_vias[["street", "Volume_Jams", "Atraso_Medio_Seg", "Criticidade_Index"]].head(10),
                hide_index=True,
                column_config={
                    "street": "Logradouro",
                    "Volume_Jams": "Qtd Retenções",
                    "Atraso_Medio_Seg": "Atraso Médio (s)",
                    "Criticidade_Index": "Índice Geral (0–100)"
                }
            )
    else:
        st.info("Dados insuficientes para o ranking multicritério.")

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
        atraso_est = predict_traffic_delay_impact(extensao_sim)
        minutos_est = atraso_est / 60
        st.metric("Atraso Estimado", f"{minutos_est:.2f} min")
        st.caption("Fórmula: *Atraso (s) = Comprimento × 0,15 + 12*")

    with col_p2:
        sim_x = np.linspace(50, 5000, 100)
        sim_y = [predict_traffic_delay_impact(l) / 60 for l in sim_x]
        df_sim = pd.DataFrame({"Comprimento (m)": sim_x, "Atraso Estimado (min)": sim_y})

        fig_pred = px.line(
            df_sim,
            x="Comprimento (m)",
            y="Atraso Estimado (min)",
            title="Curva de Impacto: Extensão de Fila vs Atraso"
        )
        fig_pred.add_scatter(
            x=[extensao_sim],
            y=[minutos_est],
            mode="markers+text",
            name="Cenário atual",
            text=["◀ Selecionado"],
            textposition="top right",
            marker=dict(size=12, color="red")
        )
        st.plotly_chart(fig_pred, use_container_width=True)

    st.markdown("---")
    st.markdown("### 📅 Vias com Maior Propensão ao Congestionamento por Dia da Semana")
    st.caption("Baseado no histórico completo de congestionamentos carregados — independente do filtro de data.")

    DIAS_PT_PRED = {
        "Monday": "Segunda",
        "Tuesday": "Terça",
        "Wednesday": "Quarta",
        "Thursday": "Quinta",
        "Friday": "Sexta",
        "Saturday": "Sábado",
        "Sunday": "Domingo"
    }
    ORDEM_DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

    df_jams_hist = df_jams_raw.copy() if not df_jams_raw.empty else pd.DataFrame()

    if not df_jams_hist.empty and "street" in df_jams_hist.columns and "day_of_week" in df_jams_hist.columns:
        df_jams_hist = df_jams_hist[
            df_jams_hist["street"].notna() &
            (~df_jams_hist["street"].isin(["NA", "nan", "Via", ""]))
        ].copy()
        df_jams_hist["Dia"] = df_jams_hist["day_of_week"].map(DIAS_PT_PRED)

        top_vias_pred = df_jams_hist["street"].value_counts().head(15).index.tolist()
        df_prop = df_jams_hist[df_jams_hist["street"].isin(top_vias_pred)]

        heatmap_data = (
            df_prop.groupby(["street", "Dia"]).size()
            .reset_index(name="Ocorrências")
        )

        total_por_via = heatmap_data.groupby("street")["Ocorrências"].transform("sum")
        heatmap_data["Propensão (%)"] = (heatmap_data["Ocorrências"] / total_por_via * 100).round(1)

        col_h1, col_h2 = st.columns([3, 2])

        with col_h1:
            pivot = heatmap_data.pivot_table(
                index="street",
                columns="Dia",
                values="Propensão (%)",
                aggfunc="sum"
            ).reindex(columns=[d for d in ORDEM_DIAS if d in heatmap_data["Dia"].unique()], fill_value=0)

            fig_heat = px.imshow(
                pivot,
                color_continuous_scale="YlOrRd",
                aspect="auto",
                title="Mapa de Propensão: Via × Dia da Semana (% de ocorrências históricas)",
                labels={"color": "Propensão (%)", "x": "Dia", "y": "Via"}
            )
            fig_heat.update_layout(height=480)
            st.plotly_chart(fig_heat, use_container_width=True)

        with col_h2:
            st.markdown("#### 🔎 Filtro por Dia da Semana")
            dia_selecionado = st.selectbox(
                "Ver vias mais propensas em:",
                ORDEM_DIAS,
                key="pred_dia"
            )

            df_dia = heatmap_data[heatmap_data["Dia"] == dia_selecionado].sort_values(
                "Propensão (%)", ascending=False
            ).head(10)

            if not df_dia.empty:
                fig_dia = px.bar(
                    df_dia,
                    x="Propensão (%)",
                    y="street",
                    orientation="h",
                    color="Propensão (%)",
                    color_continuous_scale="Reds",
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
            pior_dia,
            hide_index=True,
            column_config={
                "street": "Via / Avenida",
                "Dia": "Pior Dia",
                "Propensão (%)": "% no Dia",
                "Ocorrências": "Total de Registros"
            }
        )
    else:
        st.info("Histórico de congestionamentos insuficiente para análise de propensão por via e dia.")

    st.markdown("---")
    st.markdown("### 📆 Comparador Mensal: 2025 vs 2026")
    st.caption("Selecione um dia da semana e uma categoria para comparar a evolução mês a mês entre os dois anos.")

    MESES_PT = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    DIAS_PT_CMP = {
        "Monday": "Segunda",
        "Tuesday": "Terça",
        "Wednesday": "Quarta",
        "Thursday": "Quinta",
        "Friday": "Sexta",
        "Saturday": "Sábado",
        "Sunday": "Domingo"
    }

    frames_cmp = []

    if not df_alerts_raw.empty:
        df_a_cmp = df_alerts_raw.copy()
        df_a_cmp["categoria"] = df_a_cmp.get("type", pd.Series("ALERTA", index=df_a_cmp.index))
        df_a_cmp["origem"] = "alerta"
        frames_cmp.append(df_a_cmp[[c for c in ["timestamp", "categoria", "origem", "street", "day_of_week"] if c in df_a_cmp.columns]])

    if not df_jams_raw.empty:
        df_j_cmp = df_jams_raw.copy()
        df_j_cmp["categoria"] = "CONGESTIONAMENTO"
        df_j_cmp["origem"] = "jams"
        frames_cmp.append(df_j_cmp[[c for c in ["timestamp", "categoria", "origem", "street", "day_of_week"] if c in df_j_cmp.columns]])

    if frames_cmp:
        df_cmp_all = pd.concat(frames_cmp, ignore_index=True)
        df_cmp_all["timestamp"] = pd.to_datetime(df_cmp_all["timestamp"], errors="coerce")
        df_cmp_all = df_cmp_all.dropna(subset=["timestamp"])
        df_cmp_all["ano"] = df_cmp_all["timestamp"].dt.year
        df_cmp_all["mes"] = df_cmp_all["timestamp"].dt.month
        df_cmp_all["Dia"] = df_cmp_all["day_of_week"].map(DIAS_PT_CMP) if "day_of_week" in df_cmp_all.columns else "Todos"
        df_cmp_all["mes_nome"] = df_cmp_all["mes"].map(MESES_PT)

        anos_disp = sorted(df_cmp_all["ano"].dropna().unique().astype(int).tolist())
        cats_disp = sorted(df_cmp_all["categoria"].dropna().unique().tolist())
        dias_disp = ["Todos"] + ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

        col_c1, col_c2, col_c3, col_c4 = st.columns(4)

        with col_c1:
            ano_a = st.selectbox("Ano A:", anos_disp, index=0, key="cmp_ano_a")
        with col_c2:
            ano_b_opts = [a for a in anos_disp if a != ano_a]
            ano_b = st.selectbox("Ano B:", ano_b_opts if ano_b_opts else anos_disp, key="cmp_ano_b")
        with col_c3:
            dia_cmp = st.selectbox("Dia da Semana:", dias_disp, key="cmp_dia")
        with col_c4:
            cat_cmp = st.multiselect(
                "Categorias:",
                cats_disp,
                default=cats_disp[:3] if len(cats_disp) >= 3 else cats_disp,
                key="cmp_cat"
            )

        df_f = df_cmp_all[df_cmp_all["categoria"].isin(cat_cmp)] if cat_cmp else df_cmp_all.copy()
        if dia_cmp != "Todos":
            df_f = df_f[df_f["Dia"] == dia_cmp]

        df_ano_a = df_f[df_f["ano"] == ano_a]
        df_ano_b = df_f[df_f["ano"] == ano_b]

        def agg_mensal(df_in, ano_label):
            if df_in.empty:
                return pd.DataFrame(columns=["mes", "mes_nome", "Total", "Ano"])
            grp = df_in.groupby(["mes", "mes_nome", "categoria"]).size().reset_index(name="Total")
            grp["Ano"] = str(ano_label)
            return grp

        res_a = agg_mensal(df_ano_a, ano_a)
        res_b = agg_mensal(df_ano_b, ano_b)
        df_comp = pd.concat([res_a, res_b], ignore_index=True)

        if not df_comp.empty:
            df_comp = df_comp.sort_values("mes")
            ordem_meses = [MESES_PT[m] for m in sorted(df_comp["mes"].unique())]

            total_mes = df_comp.groupby(["mes", "mes_nome", "Ano"])["Total"].sum().reset_index()
            total_mes = total_mes.sort_values("mes")

            fig_linha = px.line(
                total_mes,
                x="mes_nome",
                y="Total",
                color="Ano",
                markers=True,
                title=f"Evolução Mensal Total — {ano_a} vs {ano_b}" + (f" · {dia_cmp}" if dia_cmp != "Todos" else ""),
                labels={"mes_nome": "Mês", "Total": "Nº Ocorrências", "Ano": "Ano"},
                color_discrete_map={str(ano_a): "#2563EB", str(ano_b): "#DC2626"},
                category_orders={"mes_nome": ordem_meses}
            )
            fig_linha.update_layout(height=380)
            st.plotly_chart(fig_linha, use_container_width=True)

            fig_bar = px.bar(
                df_comp,
                x="mes_nome",
                y="Total",
                color="Ano",
                facet_col="categoria",
                facet_col_wrap=3,
                barmode="group",
                title="Comparativo por Categoria e Mês",
                labels={"mes_nome": "Mês", "Total": "Ocorrências"},
                color_discrete_map={str(ano_a): "#2563EB", str(ano_b): "#DC2626"},
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
                    x="mes_nome",
                    y="Variação (%)",
                    color="Cor",
                    color_discrete_map={"Aumento 📈": "#DC2626", "Redução 📉": "#16A34A"},
                    title=f"Variação % de {ano_a} → {ano_b} por Mês",
                    labels={"mes_nome": "Mês", "Variação (%)": "Variação (%)"},
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
# BLOCO 7 — RODAPÉ
# =========================================================

st.markdown("---")

footer_html = f"""
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
    © {current_foz_datetime.year} GPMME / LAGGRA / LACA — UNILA · Foz do Iguaçu · Uso acadêmico e de pesquisa
  </div>
</div>
"""
st.markdown(footer_html, unsafe_allow_html=True)
