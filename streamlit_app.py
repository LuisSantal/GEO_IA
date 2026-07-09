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

def build_daily_series(alerts_dataframe: pd.DataFrame, jams_dataframe: pd.DataFrame, selected_category: str = "TODOS") -> pd.Series:
    source_frames = []

    if alerts_dataframe is not None and not alerts_dataframe.empty:
        alerts_series_dataframe = alerts_dataframe.copy()
        alerts_series_dataframe["origem"] = "ALERTA"
        alerts_series_dataframe["categoria_artigo"] = alerts_series_dataframe["type"] if "type" in alerts_series_dataframe.columns else "ALERTA"
        source_frames.append(alerts_series_dataframe[["timestamp", "categoria_artigo", "origem"]])

    if jams_dataframe is not None and not jams_dataframe.empty:
        jams_series_dataframe = jams_dataframe.copy()
        jams_series_dataframe["origem"] = "JAM"
        jams_series_dataframe["categoria_artigo"] = "CONGESTIONAMENTO"
        source_frames.append(jams_series_dataframe[["timestamp", "categoria_artigo", "origem"]])

    if not source_frames:
        return pd.Series(dtype=float)

    combined_series_base = pd.concat(source_frames, ignore_index=True)
    combined_series_base["timestamp"] = pd.to_datetime(combined_series_base["timestamp"], errors="coerce")
    combined_series_base = combined_series_base.dropna(subset=["timestamp"]).copy()
    combined_series_base["date"] = combined_series_base["timestamp"].dt.floor("D")

    if selected_category != "TODOS":
        combined_series_base = combined_series_base[combined_series_base["categoria_artigo"] == selected_category]

    daily_occurrence_series = combined_series_base.groupby("date").size().sort_index()
    if daily_occurrence_series.empty:
        return pd.Series(dtype=float)

    full_date_index = pd.date_range(daily_occurrence_series.index.min(), daily_occurrence_series.index.max(), freq="D")
    daily_occurrence_series = daily_occurrence_series.reindex(full_date_index, fill_value=0)
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
# BLOCO 6 — VISUALIZAÇÕES PRINCIPAIS
# =========================================================

st.subheader("🗺️ Visualizações")

(
    incidents_tab,
    jams_tab,
    heatmap_tab,
    temporal_analysis_tab,
    charts_tab,
    scientific_pipeline_tab,
    criticality_tab,
    predictive_model_tab,
    data_tab
) = st.tabs(
    [
        "Incidentes",
        "Congestionamentos",
        "Mapa de Calor",
        "📅 Análise Temporal",
        "Gráficos",
        "🧪 Pipeline Científico",
        "📊 Criticidade (MCDA)",
        "🔮 Modelo Preditivo",
        "Dados"
    ]
)

with incidents_tab:
    st.caption("📍 Centro: -25.54, -54.58 · Norte ↑ · Clique nos pontos para detalhes")

    if not filtered_alerts_dataframe.empty:
        incidents_map = generate_incidents_map(filtered_alerts_dataframe.to_json(date_format="iso"))

        if incidents_map:
            st_folium(incidents_map, width="100%", height=500, key=f"mapa_inc_{len(filtered_alerts_dataframe)}")

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

with jams_tab:
    st.caption("🚦 Escala métrica · Livre → Parado")

    if not filtered_jams_dataframe.empty:
        jams_map = generate_jams_map(filtered_jams_dataframe.to_json(date_format="iso"))

        if jams_map:
            st_folium(jams_map, width="100%", height=500, key=f"mapa_jam_{len(filtered_jams_dataframe)}")

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

        jam_diagnostic_columns = [column for column in ["lat", "lon", "line", "speed", "street"] if column in filtered_jams_dataframe.columns]
        if jam_diagnostic_columns:
            st.caption("Amostra dos dados de congestionamentos")
            st.dataframe(filtered_jams_dataframe[jam_diagnostic_columns].head(5), width="stretch")
    else:
        st.info("Nenhum congestionamento para exibir.")

with heatmap_tab:
    st.subheader("🔥 Zonas de Concentração de Incidentes")

    if not filtered_alerts_dataframe.empty:
        heatmap_source_dataframe = filtered_alerts_dataframe.copy()

        if {"lat", "lon"}.issubset(heatmap_source_dataframe.columns):
            heatmap_source_dataframe = heatmap_source_dataframe.dropna(subset=["lat", "lon"])
            heatmap_source_dataframe = heatmap_source_dataframe[
                heatmap_source_dataframe["lat"].between(FOZ_LATITUDE_MIN, FOZ_LATITUDE_MAX) &
                heatmap_source_dataframe["lon"].between(FOZ_LONGITUDE_MIN, FOZ_LONGITUDE_MAX)
            ]

            if not heatmap_source_dataframe.empty:
                incidents_heatmap = folium.Map(
                    location=[heatmap_source_dataframe["lat"].mean(), heatmap_source_dataframe["lon"].mean()],
                    zoom_start=13,
                    tiles="OpenStreetMap"
                )

                heat_points = [[row["lat"], row["lon"]] for _, row in heatmap_source_dataframe.iterrows()]
                plugins.HeatMap(
                    heat_points,
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
                ).add_to(incidents_heatmap)

                st_folium(incidents_heatmap, width="100%", height=500, key=f"mapa_heat_{len(heatmap_source_dataframe)}")

                st.markdown("""
                | Cor | Concentração |
                |---|---|
                | 🟨 | Baixa — poucos registros |
                | 🟧 | Média — atenção |
                | 🟥 | Alta — ponto crítico |
                | 🟫 | Crítica — intervenção prioritária |
                """)

                heatmap_type_counts = heatmap_source_dataframe["type"].value_counts().reset_index()
                heatmap_type_counts.columns = ["Tipo", "Qtd"]
                st.dataframe(heatmap_type_counts, hide_index=True, width="stretch")
            else:
                st.info("Nenhum ponto dentro da área de Foz do Iguaçu.")
        else:
            st.info("Sem coordenadas válidas para gerar o mapa de calor.")
    else:
        st.info("Sem dados suficientes para mapa de calor.")

with temporal_analysis_tab:
    st.subheader("📅 Análise Temporal de Patologias Viárias")
    st.markdown("""
    Esta seção exibe o perfil de distribuição e reincidência de anomalias viárias nos arquivos ativos carregados atualmente.
    """)
    if not raw_alerts_dataframe.empty:
        available_damage_subtypes = get_clean_unique_values(raw_alerts_dataframe["subtype"], invalid_values=["nan", ""])
        selected_damage_subtype = st.selectbox("Selecione a natureza do dano:", available_damage_subtypes, key="sel_dano_temporal")

        selected_damage_dataframe = raw_alerts_dataframe[raw_alerts_dataframe["subtype"] == selected_damage_subtype]
        if not selected_damage_dataframe.empty:
            hourly_damage_histogram = px.histogram(
                selected_damage_dataframe,
                x="hour",
                nbins=24,
                color_discrete_sequence=['#dc2626'],
                title=f"Distribuição Horária Total de: {selected_damage_subtype}",
                labels={"hour": "Hora do Dia (Recorte Atual)", "count": "Volume de Alertas"}
            )
            st.plotly_chart(hourly_damage_histogram, use_container_width=True)
        else:
            st.info("Sem registros para a patologia selecionada na data ativa.")
    else:
        st.warning("Base de dados de alertas vazia ou indisponível.")

with charts_tab:
    if not filtered_alerts_dataframe.empty:
        st.markdown(
            f"**{len(filtered_alerts_dataframe)} registros analisados** para "
            f"**{selected_date.strftime('%d/%m/%Y')}** no intervalo "
            f"**{selected_hour_range[0]:02d}:00–{selected_hour_range[1]:02d}:59**"
        )
        st.markdown("---")

        historical_alerts_dataframe = raw_alerts_dataframe.copy()

        if selected_incident_types and "type" in historical_alerts_dataframe.columns:
            historical_alerts_dataframe = historical_alerts_dataframe[historical_alerts_dataframe["type"].isin(selected_incident_types)]
        if selected_incident_subtypes and "subtype" in historical_alerts_dataframe.columns:
            historical_alerts_dataframe = historical_alerts_dataframe[historical_alerts_dataframe["subtype"].isin(selected_incident_subtypes)]
        if selected_street and "street" in historical_alerts_dataframe.columns:
            historical_alerts_dataframe = historical_alerts_dataframe[historical_alerts_dataframe["street"] == selected_street]

        weekdays_translation_pt = {
            "Monday": "Segunda",
            "Tuesday": "Terça",
            "Wednesday": "Quarta",
            "Thursday": "Quinta",
            "Friday": "Sexta",
            "Saturday": "Sábado",
            "Sunday": "Domingo",
        }

        incident_type_colors = {
            "ACIDENTE": "#e74c3c",
            "VIA FECHADA": "#c0392b",
            "PERIGO": "#e67e22",
            "PERIGO CLIMÁTICO": "#3498db",
            "CONGESTIONAMENTO": "#f39c12",
            "ALERTA": "#9b59b6",
        }

        chart_col_1, chart_col_2 = st.columns(2)

        with chart_col_1:
            st.subheader("Incidentes por Hora do Dia")
            incidents_by_hour = (
                filtered_alerts_dataframe["hour"]
                .value_counts()
                .reindex(range(24), fill_value=0)
                .reset_index()
            )
            incidents_by_hour.columns = ["Hora", "Quantidade"]
            peak_hour = int(incidents_by_hour.loc[incidents_by_hour["Quantidade"].idxmax(), "Hora"])

            incidents_by_hour_chart = px.bar(
                incidents_by_hour,
                x="Hora",
                y="Quantidade",
                color="Quantidade",
                color_continuous_scale="Reds",
                text="Quantidade",
                labels={"Hora": "Hora (UTC-3 / Foz)", "Quantidade": "Nº Incidentes"}
            )
            incidents_by_hour_chart.update_traces(textposition="outside")
            incidents_by_hour_chart.add_vline(
                x=peak_hour,
                line_dash="dash",
                line_color="darkred",
                annotation_text=f"Pico {peak_hour:02d}h"
            )
            incidents_by_hour_chart.update_layout(coloraxis_showscale=False, height=360)
            st.plotly_chart(incidents_by_hour_chart, width="stretch")

        with chart_col_2:
            st.subheader("Natureza das Ocorrências")

            has_valid_subtype = (
                "subtype" in filtered_alerts_dataframe.columns and
                filtered_alerts_dataframe["subtype"].notna().any() and
                (~filtered_alerts_dataframe["subtype"].isin(["nan", ""])).any()
            )

            if has_valid_subtype:
                valid_subtype_dataframe = filtered_alerts_dataframe[
                    filtered_alerts_dataframe["subtype"].notna() &
                    (~filtered_alerts_dataframe["subtype"].isin(["nan", ""]))
                ].copy()
                valid_subtype_dataframe["label"] = valid_subtype_dataframe.apply(
                    lambda row: row["subtype"] if row["subtype"] != "" else row["type"],
                    axis=1
                )
                incident_nature_counts = valid_subtype_dataframe["label"].value_counts().reset_index()
            else:
                incident_nature_counts = filtered_alerts_dataframe["type"].value_counts().reset_index()

            incident_nature_counts.columns = ["Natureza", "Quantidade"]

            incident_nature_pie_chart = px.pie(
                incident_nature_counts,
                names="Natureza",
                values="Quantidade",
                hole=0.38
            )
            incident_nature_pie_chart.update_layout(height=380)
            st.plotly_chart(incident_nature_pie_chart, width="stretch")

        st.markdown("---")

        if "day_of_week" in historical_alerts_dataframe.columns and not historical_alerts_dataframe.empty:
            st.subheader("Incidentes por Dia da Semana")
            weekday_dataframe = historical_alerts_dataframe.copy()
            weekday_dataframe["Dia"] = weekday_dataframe["day_of_week"].map(weekdays_translation_pt)

            incidents_by_weekday_and_type = weekday_dataframe.groupby(["Dia", "type"]).size().reset_index(name="Quantidade")
            weekday_order = list(weekdays_translation_pt.values())

            incidents_by_weekday_chart = px.bar(
                incidents_by_weekday_and_type,
                x="Dia",
                y="Quantidade",
                color="type",
                color_discrete_map=incident_type_colors,
                category_orders={"Dia": weekday_order},
                barmode="stack",
                text_auto=True
            )
            incidents_by_weekday_chart.update_layout(height=420)
            st.plotly_chart(incidents_by_weekday_chart, width="stretch")

        st.markdown("---")
        st.subheader("Vias Críticas — Incidentes por Natureza")

        top_streets = []
        if "street" in historical_alerts_dataframe.columns:
            top_streets = (
                historical_alerts_dataframe[
                    historical_alerts_dataframe["street"].notna() &
                    (~historical_alerts_dataframe["street"].isin(["NA", "nan", ""]))
                ]["street"]
                .value_counts()
                .head(10)
                .index
                .tolist()
            )

        if top_streets and "subtype" in historical_alerts_dataframe.columns:
            street_subtype_dataframe = historical_alerts_dataframe[
                historical_alerts_dataframe["street"].isin(top_streets) &
                historical_alerts_dataframe["subtype"].notna() &
                (~historical_alerts_dataframe["subtype"].isin(["nan", ""]))
            ].copy()

            incidents_by_street_and_subtype = street_subtype_dataframe.groupby(
                ["street", "subtype"]
            ).size().reset_index(name="Quantidade")

            street_order = (
                incidents_by_street_and_subtype.groupby("street")["Quantidade"]
                .sum()
                .sort_values(ascending=True)
                .index
                .tolist()
            )

            critical_streets_chart = px.bar(
                incidents_by_street_and_subtype,
                x="Quantidade",
                y="street",
                color="subtype",
                orientation="h",
                barmode="stack",
                category_orders={"street": street_order}
            )
            critical_streets_chart.update_layout(height=460)
            st.plotly_chart(critical_streets_chart, width="stretch")

        st.markdown("---")
        st.subheader("Quais dias cada rua tem mais problemas?")

        if top_streets and "day_of_week" in historical_alerts_dataframe.columns:
            street_weekday_dataframe = historical_alerts_dataframe[
                historical_alerts_dataframe["street"].isin(top_streets)
            ].copy()
            street_weekday_dataframe["Dia"] = street_weekday_dataframe["day_of_week"].map(weekdays_translation_pt)

            street_weekday_counts = street_weekday_dataframe.groupby(["street", "Dia"]).size().reset_index(name="Qtd")
            total_counts_by_street_weekday = street_weekday_counts.groupby(["street", "Dia"])["Qtd"].sum().reset_index(name="Total")
            maximum_weekday_volume = total_counts_by_street_weekday["Total"].max() if not total_counts_by_street_weekday.empty else 1

            def classify_weekday_intensity(total_value, maximum_value):
                if total_value == 0:
                    return "Nenhum"
                elif total_value <= maximum_value * 0.25:
                    return "Baixo"
                elif total_value <= maximum_value * 0.60:
                    return "Médio"
                return "Alto"

            total_counts_by_street_weekday["Nível"] = total_counts_by_street_weekday["Total"].apply(
                lambda total_value: classify_weekday_intensity(total_value, maximum_weekday_volume)
            )

            street_weekday_bubble_chart = px.scatter(
                total_counts_by_street_weekday,
                x="Dia",
                y="street",
                size="Total",
                color="Nível",
                text="Total",
                size_max=55,
                category_orders={"Dia": list(weekdays_translation_pt.values())}
            )
            street_weekday_bubble_chart.update_layout(height=460)
            st.plotly_chart(street_weekday_bubble_chart, width="stretch")
    else:
        st.info("Sem incidentes para gerar gráficos no recorte atual.")

with scientific_pipeline_tab:
    st.subheader("🧪 Pipeline Científico para o Artigo")
    st.caption("Geração de séries, decomposição STL, detecção de rupturas (PELT) e tabelas descritivas para apoio à redação acadêmica.")

    pipeline_col_1, pipeline_col_2, pipeline_col_3 = st.columns(3)
    available_pipeline_categories = ["TODOS"]

    if not raw_alerts_dataframe.empty and "type" in raw_alerts_dataframe.columns:
        available_pipeline_categories += sorted(raw_alerts_dataframe["type"].dropna().astype(str).unique().tolist())

    available_pipeline_categories = list(dict.fromkeys(available_pipeline_categories + ["CONGESTIONAMENTO"]))

    with pipeline_col_1:
        selected_pipeline_category = st.selectbox("Categoria analisada", available_pipeline_categories, index=0, key="pipe_categoria")
    with pipeline_col_2:
        selected_stl_period = st.selectbox("Periodicidade STL", [7, 30], index=0, key="pipe_stl_period")
    with pipeline_col_3:
        selected_pelt_penalty = st.slider("Penalidade PELT", min_value=1.0, max_value=20.0, value=5.0, step=0.5, key="pipe_pelt_pen")

    daily_series = build_daily_series(raw_alerts_dataframe, raw_jams_dataframe, selected_category=selected_pipeline_category)

    if daily_series.empty:
        st.info("Sem dados suficientes para montar a série temporal.")
    else:
        st.markdown("### Série diária")
        daily_series_dataframe = daily_series.reset_index()
        daily_series_dataframe.columns = ["Data", "Ocorrências"]

        daily_series_chart = px.line(
            daily_series_dataframe,
            x="Data",
            y="Ocorrências",
            title=f"Série diária de ocorrências — {selected_pipeline_category}",
            markers=False
        )
        daily_series_chart.update_layout(height=360)
        st.plotly_chart(daily_series_chart, use_container_width=True)

        st.markdown("### Decomposição STL")
        stl_result = run_stl_analysis(daily_series, period=selected_stl_period)

        if stl_result is not None:
            from plotly.subplots import make_subplots
            import plotly.graph_objects as go

            stl_chart = make_subplots(
                rows=4, cols=1, shared_xaxes=True,
                subplot_titles=["Observed", "Trend", "Seasonal", "Residual"],
                vertical_spacing=0.04
            )
            series_dates = daily_series.index

            stl_chart.add_trace(go.Scatter(x=series_dates, y=stl_result.observed, name="Observed", line=dict(color="#2563EB")), row=1, col=1)
            stl_chart.add_trace(go.Scatter(x=series_dates, y=stl_result.trend, name="Trend", line=dict(color="#DC2626")), row=2, col=1)
            stl_chart.add_trace(go.Scatter(x=series_dates, y=stl_result.seasonal, name="Seasonal", line=dict(color="#16A34A")), row=3, col=1)
            stl_chart.add_trace(go.Scatter(x=series_dates, y=stl_result.resid, name="Residual", mode="lines", line=dict(color="#7C3AED")), row=4, col=1)

            stl_chart.update_layout(height=900, showlegend=False, title=f"STL — {selected_pipeline_category} (period={selected_stl_period})")
            st.plotly_chart(stl_chart, use_container_width=True)
        else:
            st.warning("Não foi possível executar a STL. Verifique se `statsmodels` está instalado.")

        st.markdown("### Rupturas estruturais — PELT")
        pelt_breakpoints = run_pelt_analysis(daily_series, model="l2", min_size=7, jump=1, pen=selected_pelt_penalty)

        pelt_chart = px.line(daily_series_dataframe, x="Data", y="Ocorrências", title="Mudanças estruturais detectadas por PELT")
        for breakpoint_index in pelt_breakpoints[:-1]:
            if 0 <= breakpoint_index - 1 < len(daily_series_dataframe):
                breakpoint_date = daily_series_dataframe.iloc[breakpoint_index - 1]["Data"]
                pelt_chart.add_vline(x=breakpoint_date, line_dash="dash", line_color="red")
        pelt_chart.update_layout(height=360)
        st.plotly_chart(pelt_chart, use_container_width=True)

        if pelt_breakpoints:
            estimated_break_dates = []
            for breakpoint_index in pelt_breakpoints[:-1]:
                if 0 <= breakpoint_index - 1 < len(daily_series_dataframe):
                    estimated_break_dates.append(
                        pd.to_datetime(daily_series_dataframe.iloc[breakpoint_index - 1]["Data"]).strftime("%Y-%m-%d")
                    )
            st.write("Datas estimadas de ruptura:", estimated_break_dates if estimated_break_dates else "Nenhuma ruptura relevante.")

    st.markdown("---")
    st.markdown("### Tabela 1 — Estatísticas descritivas")
    descriptive_statistics_table = build_descriptive_table(raw_alerts_dataframe, raw_jams_dataframe)

    if not descriptive_statistics_table.empty:
        st.dataframe(descriptive_statistics_table, hide_index=True, use_container_width=True)
        descriptive_statistics_csv = descriptive_statistics_table.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Baixar CSV — Tabela 1",
            data=descriptive_statistics_csv,
            file_name="tabela_1_estatisticas_descritivas.csv",
            mime="text/csv"
        )
    else:
        st.info("Sem dados suficientes para a tabela descritiva.")

with criticality_tab:
    st.subheader("📊 Classificação Hierárquica de Infraestrutura Viária Crítica")
    st.markdown("""
    Análise multicritério ponderando **volume de congestionamentos** e **atraso médio (s)**.
    Permite à **Foztrans** priorizar envio de agentes ou investimentos nas vias de maior peso operacional.
    """)

    if not road_criticality_dataframe.empty:
        criticality_col_1, criticality_col_2 = st.columns([3, 2])

        with criticality_col_1:
            road_criticality_chart = px.bar(
                road_criticality_dataframe.head(10),
                x="Criticidade_Index",
                y="street",
                orientation="h",
                title="Top 10 Vias Críticas — Intervenção Prioritária",
                labels={"Criticidade_Index": "Índice de Criticidade (0–100)", "street": "Logradouro"},
                color="Criticidade_Index",
                color_continuous_scale="Oranges"
            )
            road_criticality_chart.update_layout(height=400)
            st.plotly_chart(road_criticality_chart, use_container_width=True)

        with criticality_col_2:
            st.markdown("#### Ranking de Prioridade Viária")
            st.dataframe(
                road_criticality_dataframe[["street", "Volume_Jams", "Atraso_Medio_Seg", "Criticidade_Index"]].head(10),
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

with predictive_model_tab:
    st.subheader("🔮 Simulador Preditivo de Impacto e Propensão ao Congestionamento")
    st.markdown("""
    Combinação de **regressão inferencial** (impacto temporal por extensão de fila) com análise histórica de
    **propensão ao congestionamento por via e dia da semana**, fundamentada nos dados reais do dataset WazeFoz.
    """)

    st.markdown("### 🧮 Simulador de Atraso por Extensão de Fila")
    prediction_col_1, prediction_col_2 = st.columns(2)

    with prediction_col_1:
        selected_queue_length_meters = st.slider("Extensão da fila (metros):", 50, 5000, 500, 50, key="slider_pred_ext")
        estimated_delay_seconds = predict_traffic_delay_impact(selected_queue_length_meters)
        estimated_delay_minutes = estimated_delay_seconds / 60
        st.metric("Atraso Estimado", f"{estimated_delay_minutes:.2f} min")
        st.caption("Fórmula: *Atraso (s) = Comprimento × 0,15 + 12*")

    with prediction_col_2:
        simulation_lengths = np.linspace(50, 5000, 100)
        simulation_delay_minutes = [predict_traffic_delay_impact(queue_length) / 60 for queue_length in simulation_lengths]
        simulation_dataframe = pd.DataFrame({
            "Comprimento (m)": simulation_lengths,
            "Atraso Estimado (min)": simulation_delay_minutes
        })

        delay_prediction_chart = px.line(
            simulation_dataframe,
            x="Comprimento (m)",
            y="Atraso Estimado (min)",
            title="Curva de Impacto: Extensão de Fila vs Atraso"
        )
        delay_prediction_chart.add_scatter(
            x=[selected_queue_length_meters],
            y=[estimated_delay_minutes],
            mode="markers+text",
            name="Cenário atual",
            text=["◀ Selecionado"],
            textposition="top right",
            marker=dict(size=12, color="red")
        )
        st.plotly_chart(delay_prediction_chart, use_container_width=True)

    st.markdown("---")
    st.markdown("### 📅 Vias com Maior Propensão ao Congestionamento por Dia da Semana")
    st.caption("Baseado no histórico completo de congestionamentos carregados — independente do filtro de data.")

    weekdays_translation_prediction = {
        "Monday": "Segunda",
        "Tuesday": "Terça",
        "Wednesday": "Quarta",
        "Thursday": "Quinta",
        "Friday": "Sexta",
        "Saturday": "Sábado",
        "Sunday": "Domingo"
    }
    weekday_order_prediction = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

    historical_jams_dataframe = raw_jams_dataframe.copy() if not raw_jams_dataframe.empty else pd.DataFrame()

    if not historical_jams_dataframe.empty and "street" in historical_jams_dataframe.columns and "day_of_week" in historical_jams_dataframe.columns:
        historical_jams_dataframe = historical_jams_dataframe[
            historical_jams_dataframe["street"].notna() &
            (~historical_jams_dataframe["street"].isin(["NA", "nan", "Via", ""]))
        ].copy()
        historical_jams_dataframe["Dia"] = historical_jams_dataframe["day_of_week"].map(weekdays_translation_prediction)

        top_prediction_streets = historical_jams_dataframe["street"].value_counts().head(15).index.tolist()
        street_propensity_dataframe = historical_jams_dataframe[historical_jams_dataframe["street"].isin(top_prediction_streets)]

        street_weekday_propensity = (
            street_propensity_dataframe.groupby(["street", "Dia"]).size()
            .reset_index(name="Ocorrências")
        )

        total_occurrences_by_street = street_weekday_propensity.groupby("street")["Ocorrências"].transform("sum")
        street_weekday_propensity["Propensão (%)"] = (
            street_weekday_propensity["Ocorrências"] / total_occurrences_by_street * 100
        ).round(1)

        propensity_col_1, propensity_col_2 = st.columns([3, 2])

        with propensity_col_1:
            propensity_pivot = street_weekday_propensity.pivot_table(
                index="street",
                columns="Dia",
                values="Propensão (%)",
                aggfunc="sum"
            ).reindex(
                columns=[weekday for weekday in weekday_order_prediction if weekday in street_weekday_propensity["Dia"].unique()],
                fill_value=0
            )

            propensity_heatmap_chart = px.imshow(
                propensity_pivot,
                color_continuous_scale="YlOrRd",
                aspect="auto",
                title="Mapa de Propensão: Via × Dia da Semana (% de ocorrências históricas)",
                labels={"color": "Propensão (%)", "x": "Dia", "y": "Via"}
            )
            propensity_heatmap_chart.update_layout(height=480)
            st.plotly_chart(propensity_heatmap_chart, use_container_width=True)

        with propensity_col_2:
            st.markdown("#### 🔎 Filtro por Dia da Semana")
            selected_prediction_weekday = st.selectbox("Ver vias mais propensas em:", weekday_order_prediction, key="pred_dia")

            selected_weekday_propensity = street_weekday_propensity[
                street_weekday_propensity["Dia"] == selected_prediction_weekday
            ].sort_values("Propensão (%)", ascending=False).head(10)

            if not selected_weekday_propensity.empty:
                selected_weekday_chart = px.bar(
                    selected_weekday_propensity,
                    x="Propensão (%)",
                    y="street",
                    orientation="h",
                    color="Propensão (%)",
                    color_continuous_scale="Reds",
                    title=f"Top 10 — {selected_prediction_weekday}",
                    labels={"street": "Via", "Propensão (%)": "% do tráfego semanal"}
                )
                selected_weekday_chart.update_layout(height=380, coloraxis_showscale=False)
                st.plotly_chart(selected_weekday_chart, use_container_width=True)
            else:
                st.info(f"Sem dados históricos para {selected_prediction_weekday}.")

        st.markdown("#### 📋 Pior Dia da Semana por Via")
        worst_weekday_by_street = (
            street_weekday_propensity.loc[street_weekday_propensity.groupby("street")["Propensão (%)"].idxmax()]
            [["street", "Dia", "Propensão (%)", "Ocorrências"]]
            .sort_values("Ocorrências", ascending=False)
            .head(15)
            .reset_index(drop=True)
        )

        st.dataframe(
            worst_weekday_by_street,
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

    months_translation_pt = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    weekdays_translation_comparison = {
        "Monday": "Segunda", "Tuesday": "Terça", "Wednesday": "Quarta",
        "Thursday": "Quinta", "Friday": "Sexta", "Saturday": "Sábado", "Sunday": "Domingo"
    }

    comparison_source_frames = []

    if not raw_alerts_dataframe.empty:
        alerts_comparison_dataframe = raw_alerts_dataframe.copy()
        alerts_comparison_dataframe["categoria"] = alerts_comparison_dataframe.get(
            "type",
            pd.Series("ALERTA", index=alerts_comparison_dataframe.index)
        )
        alerts_comparison_dataframe["origem"] = "alerta"
        comparison_source_frames.append(
            alerts_comparison_dataframe[
                [column for column in ["timestamp", "categoria", "origem", "street", "day_of_week"] if column in alerts_comparison_dataframe.columns]
            ]
        )

    if not raw_jams_dataframe.empty:
        jams_comparison_dataframe = raw_jams_dataframe.copy()
        jams_comparison_dataframe["categoria"] = "CONGESTIONAMENTO"
        jams_comparison_dataframe["origem"] = "jams"
        comparison_source_frames.append(
            jams_comparison_dataframe[
                [column for column in ["timestamp", "categoria", "origem", "street", "day_of_week"] if column in jams_comparison_dataframe.columns]
            ]
        )

    if comparison_source_frames:
        monthly_comparison_dataframe = pd.concat(comparison_source_frames, ignore_index=True)
        monthly_comparison_dataframe["timestamp"] = pd.to_datetime(monthly_comparison_dataframe["timestamp"], errors="coerce")
        monthly_comparison_dataframe = monthly_comparison_dataframe.dropna(subset=["timestamp"])
        monthly_comparison_dataframe["ano"] = monthly_comparison_dataframe["timestamp"].dt.year
        monthly_comparison_dataframe["mes"] = monthly_comparison_dataframe["timestamp"].dt.month
        monthly_comparison_dataframe["Dia"] = (
            monthly_comparison_dataframe["day_of_week"].map(weekdays_translation_comparison)
            if "day_of_week" in monthly_comparison_dataframe.columns else "Todos"
        )
        monthly_comparison_dataframe["mes_nome"] = monthly_comparison_dataframe["mes"].map(months_translation_pt)

        available_years = sorted(monthly_comparison_dataframe["ano"].dropna().unique().astype(int).tolist())
        available_categories = sorted(monthly_comparison_dataframe["categoria"].dropna().unique().tolist())
        available_weekdays = ["Todos"] + ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

        comparison_col_1, comparison_col_2, comparison_col_3, comparison_col_4 = st.columns(4)

        with comparison_col_1:
            selected_year_a = st.selectbox("Ano A:", available_years, index=0, key="cmp_ano_a")
        with comparison_col_2:
            available_year_b_options = [year for year in available_years if year != selected_year_a]
            selected_year_b = st.selectbox("Ano B:", available_year_b_options if available_year_b_options else available_years, key="cmp_ano_b")
        with comparison_col_3:
            selected_comparison_weekday = st.selectbox("Dia da Semana:", available_weekdays, key="cmp_dia")
        with comparison_col_4:
            selected_comparison_categories = st.multiselect(
                "Categorias:",
                available_categories,
                default=available_categories[:3] if len(available_categories) >= 3 else available_categories,
                key="cmp_cat"
            )

        comparison_filtered_dataframe = (
            monthly_comparison_dataframe[monthly_comparison_dataframe["categoria"].isin(selected_comparison_categories)]
            if selected_comparison_categories else monthly_comparison_dataframe.copy()
        )

        if selected_comparison_weekday != "Todos":
            comparison_filtered_dataframe = comparison_filtered_dataframe[
                comparison_filtered_dataframe["Dia"] == selected_comparison_weekday
            ]

        year_a_dataframe = comparison_filtered_dataframe[comparison_filtered_dataframe["ano"] == selected_year_a]
        year_b_dataframe = comparison_filtered_dataframe[comparison_filtered_dataframe["ano"] == selected_year_b]

        def aggregate_monthly_occurrences(input_dataframe, year_label):
            if input_dataframe.empty:
                return pd.DataFrame(columns=["mes", "mes_nome", "Total", "Ano"])
            grouped_dataframe = input_dataframe.groupby(["mes", "mes_nome", "categoria"]).size().reset_index(name="Total")
            grouped_dataframe["Ano"] = str(year_label)
            return grouped_dataframe

        year_a_summary = aggregate_monthly_occurrences(year_a_dataframe, selected_year_a)
        year_b_summary = aggregate_monthly_occurrences(year_b_dataframe, selected_year_b)
        monthly_comparison_summary = pd.concat([year_a_summary, year_b_summary], ignore_index=True)

        if not monthly_comparison_summary.empty:
            monthly_comparison_summary = monthly_comparison_summary.sort_values("mes")
            ordered_month_names = [months_translation_pt[month] for month in sorted(monthly_comparison_summary["mes"].unique())]

            monthly_totals = monthly_comparison_summary.groupby(["mes", "mes_nome", "Ano"])["Total"].sum().reset_index()
            monthly_totals = monthly_totals.sort_values("mes")

            monthly_evolution_chart = px.line(
                monthly_totals,
                x="mes_nome",
                y="Total",
                color="Ano",
                markers=True,
                title=f"Evolução Mensal Total — {selected_year_a} vs {selected_year_b}" + (f" · {selected_comparison_weekday}" if selected_comparison_weekday != "Todos" else ""),
                labels={"mes_nome": "Mês", "Total": "Nº Ocorrências", "Ano": "Ano"},
                color_discrete_map={str(selected_year_a): "#2563EB", str(selected_year_b): "#DC2626"},
                category_orders={"mes_nome": ordered_month_names}
            )
            monthly_evolution_chart.update_layout(height=380)
            st.plotly_chart(monthly_evolution_chart, use_container_width=True)

            monthly_category_comparison_chart = px.bar(
                monthly_comparison_summary,
                x="mes_nome",
                y="Total",
                color="Ano",
                facet_col="categoria",
                facet_col_wrap=3,
                barmode="group",
                title="Comparativo por Categoria e Mês",
                labels={"mes_nome": "Mês", "Total": "Ocorrências"},
                color_discrete_map={str(selected_year_a): "#2563EB", str(selected_year_b): "#DC2626"},
                category_orders={"mes_nome": ordered_month_names}
            )
            monthly_category_comparison_chart.update_layout(height=420)
            monthly_category_comparison_chart.for_each_annotation(lambda annotation: annotation.update(text=annotation.text.split("=")[-1]))
            st.plotly_chart(monthly_category_comparison_chart, use_container_width=True)

            st.markdown("#### 📈 Variação Percentual Mês a Mês (Crescimento / Decrescimento)")
            monthly_variation_pivot = monthly_totals.pivot_table(index="mes_nome", columns="Ano", values="Total").reindex(ordered_month_names)
            monthly_variation_pivot.columns = [str(column_name) for column_name in monthly_variation_pivot.columns]

            year_a_column = str(selected_year_a)
            year_b_column = str(selected_year_b)

            if year_a_column in monthly_variation_pivot.columns and year_b_column in monthly_variation_pivot.columns:
                monthly_variation_pivot["Variação (%)"] = (
                    (monthly_variation_pivot[year_b_column] - monthly_variation_pivot[year_a_column]) /
                    monthly_variation_pivot[year_a_column].replace(0, np.nan) * 100
                ).round(1)

                monthly_variation_pivot = monthly_variation_pivot.reset_index()
                monthly_variation_pivot["Cor"] = monthly_variation_pivot["Variação (%)"].apply(
                    lambda value: "Aumento 📈" if value >= 0 else "Redução 📉"
                )

                monthly_variation_chart = px.bar(
                    monthly_variation_pivot.dropna(subset=["Variação (%)"]),
                    x="mes_nome",
                    y="Variação (%)",
                    color="Cor",
                    color_discrete_map={"Aumento 📈": "#DC2626", "Redução 📉": "#16A34A"},
                    title=f"Variação % de {selected_year_a} → {selected_year_b} por Mês",
                    labels={"mes_nome": "Mês", "Variação (%)": "Variação (%)"},
                    text="Variação (%)",
                    category_orders={"mes_nome": ordered_month_names}
                )
                monthly_variation_chart.update_traces(texttemplate="%{text}%", textposition="outside")
                monthly_variation_chart.add_hline(y=0, line_dash="dash", line_color="gray")
                monthly_variation_chart.update_layout(height=360, showlegend=True)
                st.plotly_chart(monthly_variation_chart, use_container_width=True)

            st.markdown("#### 📋 Tabela Resumo Comparativa")
            comparison_summary_table = (
                monthly_variation_pivot[[ "mes_nome", year_a_column, year_b_column, "Variação (%)"]].copy()
                if "Variação (%)" in monthly_variation_pivot.columns
                else monthly_variation_pivot
            )

            if "Variação (%)" in comparison_summary_table.columns:
                comparison_summary_table.columns = ["Mês", str(selected_year_a), str(selected_year_b), "Δ (%)"]

            st.dataframe(comparison_summary_table, hide_index=True, use_container_width=True)
        else:
            st.info("Sem dados suficientes para o comparativo mensal com os filtros selecionados.")
    else:
        st.info("Nenhum dado histórico disponível para comparação.")

with data_tab:
    st.subheader("Tabela de Incidentes")

    if not filtered_alerts_dataframe.empty:
        visible_incident_columns = [
            column for column in [
                "timestamp", "type", "subtype", "street", "lat", "lon",
                "confidence", "reportRating"
            ] if column in filtered_alerts_dataframe.columns
        ]
        st.dataframe(
            filtered_alerts_dataframe[visible_incident_columns].sort_values("timestamp", ascending=False),
            width="stretch"
        )
        incidents_csv = filtered_alerts_dataframe[visible_incident_columns].to_csv(index=False).encode("utf-8")
        st.download_button(
            "Baixar CSV — Incidentes",
            data=incidents_csv,
            file_name=f"incidentes_{selected_date}.csv",
            mime="text/csv"
        )
    else:
        st.info("Nenhum dado de incidente disponível.")

    st.subheader("Tabela de Congestionamentos")

    if not filtered_jams_dataframe.empty:
        visible_jam_columns = [
            column for column in [
                "timestamp", "street", "speed", "length", "delay",
                "type", "subtype", "lat", "lon"
            ] if column in filtered_jams_dataframe.columns
        ]

        visible_jams_dataframe = filtered_jams_dataframe[visible_jam_columns].copy()
        if "speed" in visible_jams_dataframe.columns:
            visible_jams_dataframe["speed_kmh"] = (visible_jams_dataframe["speed"] * 3.6).round(1)

        st.dataframe(
            visible_jams_dataframe.sort_values("timestamp", ascending=False),
            width="stretch"
        )
        jams_csv = visible_jams_dataframe.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Baixar CSV — Congestionamentos",
            data=jams_csv,
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
