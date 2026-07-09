import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import re
import ast
import os
import tempfile
import numpy as np
import requests
from datetime import datetime, time
from zoneinfo import ZoneInfo
import folium
from folium import plugins
from folium.plugins import MarkerCluster
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

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

DIAS_PT = {
    "Monday": "Segunda",
    "Tuesday": "Terça",
    "Wednesday": "Quarta",
    "Thursday": "Quinta",
    "Friday": "Sexta",
    "Saturday": "Sábado",
    "Sunday": "Domingo",
}

DIAS_PT_CMP = DIAS_PT.copy()
ORDEM_DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

CORES_TIPO = {
    "ACIDENTE": "#e74c3c",
    "VIA FECHADA": "#c0392b",
    "PERIGO": "#e67e22",
    "PERIGO CLIMÁTICO": "#3498db",
    "CONGESTIONAMENTO": "#9b59b6",
    "ALERTA": "#f1c40f",
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
:root {
    --bg: #f0f4f8; --surface: #ffffff; --surface-soft: #f8fafc; --surface-2: #e8edf2;
    --text: #1e293b; --text-strong: #0f172a; --text-muted: #475569; --text-faint: #94a3b8;
    --border: #dde3ea; --primary: #2563eb; --primary-dark: #1d4ed8; --primary-soft: #eff6ff;
    --primary-hover: #1e40af; --success: #16a34a; --success-soft: #f0fdf4; --warning: #d97706;
    --warning-soft: #fffbeb; --danger: #dc2626; --danger-soft: #fef2f2; --purple: #7c3aed;
    --radius: 12px; --shadow-sm: 0 1px 3px rgba(15,23,42,0.07), 0 1px 2px rgba(15,23,42,0.04);
    --shadow-md: 0 4px 12px rgba(15,23,42,0.10), 0 2px 6px rgba(15,23,42,0.06);
    --shadow-lg: 0 10px 30px rgba(15,23,42,0.12), 0 4px 10px rgba(15,23,42,0.07);
}
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; -webkit-font-smoothing: antialiased !important; }
body { color: var(--text); }
.stApp { background: var(--bg) !important; color: var(--text) !important; }
.main .block-container { background: transparent !important; padding-top: 1.5rem !important; }
[data-testid="stSidebar"] { background: var(--surface) !important; border-right: 1px solid var(--border) !important; box-shadow: 2px 0 8px rgba(15,23,42,0.05) !important; }
[data-testid="stSidebar"] * { color: var(--text) !important; }
[data-testid="stSidebar"] .stMarkdown h3, [data-testid="stSidebar"] .stMarkdown h4 { color: var(--text-strong) !important; font-weight: 700 !important; }
[data-testid="stSidebar"] [data-testid="stMetricValue"] { color: var(--primary) !important; font-weight: 700 !important; }
.stButton button[kind="primary"] { background: var(--primary) !important; color: #ffffff !important; border: none !important; border-radius: 10px !important; font-weight: 600 !important; box-shadow: var(--shadow-md) !important; }
.stButton button[kind="secondary"] { background: var(--surface) !important; color: var(--primary) !important; border: 1.5px solid var(--primary) !important; border-radius: 10px !important; font-weight: 600 !important; }
[data-testid="metric-container"] { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: var(--radius) !important; padding: 1rem 1.2rem !important; box-shadow: var(--shadow-sm) !important; }
[data-testid="metric-container"] label { color: var(--text-muted) !important; font-size: 0.72rem !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 0.9px !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: var(--text-strong) !important; font-size: 1.6rem !important; font-weight: 700 !important; }
.stTabs [data-baseweb="tab-list"] { background: var(--surface-soft) !important; border-radius: 12px !important; padding: 4px !important; gap: 4px !important; border: 1px solid var(--border) !important; }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: var(--text-muted) !important; border-radius: 8px !important; font-weight: 500 !important; padding: 8px 18px !important; }
.stTabs [aria-selected="true"] { background: var(--primary) !important; color: #ffffff !important; font-weight: 600 !important; box-shadow: 0 2px 8px rgba(37,99,235,0.30) !important; }
[data-testid="stDataFrame"] { border-radius: var(--radius) !important; overflow: hidden !important; border: 1px solid var(--border) !important; background: var(--surface) !important; box-shadow: var(--shadow-sm) !important; }
.card-light { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.25rem 1.5rem; box-shadow: var(--shadow-sm); }
.badge { display: inline-flex; align-items: center; gap: 4px; padding: 2px 10px; border-radius: 99px; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.4px; }
.badge-success { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.badge-warning { background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
.badge-danger  { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.badge-primary { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
hr { border-color: var(--border) !important; }
</style>
""", unsafe_allow_html=True)

TZ_FOZ = ZoneInfo("America/Sao_Paulo")

def now_foz() -> datetime:
    return datetime.now(TZ_FOZ).replace(tzinfo=None)

if "app_start_time" not in st.session_state:
    st.session_state.app_start_time = now_foz()
if "manual_refreshes" not in st.session_state:
    st.session_state.manual_refreshes = 0

tempo_sessao = (now_foz() - st.session_state.app_start_time).total_seconds()
tempo_prox_refresh = 600 - (tempo_sessao % 600)
minutos_restantes = int(tempo_prox_refresh // 60)
segundos_restantes = int(tempo_prox_refresh % 60)
tempo_total = int(tempo_sessao)

FOLDER_ALERTS_ID = "1xKkqLEusWuNoGzy5-UYuevUbMHAvc-bL"
FOLDER_JAMS_ID = "192MCefe9vQwYhQcu-uZXekMbgdslTcgC"
FOLDER_ALERTS_ID2 = "1kQfYRJz0-EwY4gcsjTTVBCgK9zO5BAR0"
FOLDER_JAMS_ID2 = "16bblUG7NQmLMZM7BQUGAa3-GZIFYMka0"
CSV_FILES_TO_MERGE = [
    "Waze for Cities Data _ tabelas alertas_20240101_20260306.csv",
    "Waze for Cities Data _ buracos na via maio 2025 a maio 2026.csv",
    "Waze for Cities Data _ todos os alertas maio 2025 a maio 2026.csv",
    "Waze for Cities Data _Dashboard_Traffic Alerts_Tabela_2025-01-01-2026-07-04.csv",
]
LAT_MIN, LAT_MAX = -25.70, -25.40
LON_MIN, LON_MAX = -54.75, -54.45

def get_congestion_color(speed_kmh: float) -> str:
    if speed_kmh >= 80: return "#2196F3"
    elif speed_kmh >= 60: return "#4CAF50"
    elif speed_kmh >= 40: return "#8BC34A"
    elif speed_kmh >= 20: return "#FF9800"
    elif speed_kmh >= 5: return "#F44336"
    return "#7B1FA2"

def get_danger_color(incident_type: str, subtype: str | None = None) -> str:
    leves = {"ACIDENTE LEVE","TRÂNSITO MODERADO","PERIGO NA VIA","OBJETO NA VIA","ANIMAL NA VIA","VEÍCULO PARADO","VEÍCULO PARADO NA VIA","CONDIÇÕES CLIMÁTICAS"}
    tipo = str(incident_type).upper().strip() if incident_type else ""
    subtipo = str(subtype).upper().strip() if subtype else ""
    is_leve = subtipo in leves
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
        "ACIDENTE GRAVE": "#B71C1C", "ACIDENTE LEVE": "#EF9A9A", "BURACO NA VIA": "#FF9800",
        "OBRAS NA VIA": "#78909C", "SEMÁFORO QUEBRADO": "#FDD835", "INUNDAÇÃO": "#0288D1",
        "NEBLINA": "#B0BEC5", "TRÂNSITO PARADO": "#7B1FA2", "TRÂNSITO PESADO": "#F44336",
        "TRÂNSITO MODERADO": "#FF9800",
    }
    if subtipo in subtype_override: return subtype_override[subtipo]
    return color_map.get(tipo, "#90A4AE")

TYPE_MAP = {
    "ROAD_CLOSED": "VIA FECHADA", "ROAD_CLOSED_CONSTRUCTION": "VIA FECHADA", "ROAD_CLOSED_EVENT": "VIA FECHADA",
    "HAZARD": "PERIGO", "ACCIDENT": "ACIDENTE", "JAM": "CONGESTIONAMENTO", "WEATHERHAZARD": "PERIGO CLIMÁTICO",
}
SUBTYPE_MAP = {
    "ROAD_CLOSED_CONSTRUCTION": "OBRAS", "ROAD_CLOSED_EVENT": "EVENTO", "HAZARD_ON_ROAD": "PERIGO NA VIA",
    "HAZARD_ON_ROAD_POT_HOLE": "BURACO NA VIA", "HAZARD_ON_ROAD_ROAD_KILL": "ANIMAL NA VIA",
    "HAZARD_ON_ROAD_CAR_STOPPED": "VEÍCULO PARADO NA VIA", "HAZARD_ON_ROAD_CONSTRUCTION": "OBRAS NA VIA",
    "HAZARD_ON_ROAD_OBJECT": "OBJETO NA VIA", "HAZARD_ON_ROAD_TRAFFIC_LIGHT_FAULT": "SEMÁFORO QUEBRADO",
    "HAZARD_ON_ROAD_ICE": "PISTA COM GELO", "HAZARD_ON_ROAD_LANE_CLOSED": "FAIXA INTERDITADA",
    "HAZARD_ON_SHOULDER": "PERIGO NO ACOSTAMENTO", "HAZARD_ON_SHOULDER_CAR_STOPPED": "VEÍCULO PARADO NO ACOSTAMENTO",
    "HAZARD_ON_SHOULDER_ANIMALS": "ANIMAIS NO ACOSTAMENTO", "HAZARD_ON_SHOULDER_MISSING_SIGN": "SINALIZAÇÃO AUSENTE",
    "HAZARD_WEATHER": "CONDIÇÕES CLIMÁTICAS", "HAZARD_WEATHER_FOG": "NEBLINA", "HAZARD_WEATHER_HAIL": "GRANIZO",
    "HAZARD_WEATHER_HEAVY_RAIN": "CHUVA FORTE", "HAZARD_WEATHER_FLOOD": "INUNDAÇÃO", "HAZARD_WEATHER_MONSOON": "TEMPORAL",
    "HAZARD_WEATHER_TORNADO": "TORNADO", "HAZARD_WEATHER_HEAT_WAVE": "ONDA DE CALOR", "HAZARD_WEATHER_HEAVY_SNOW": "NEVE INTENSA",
    "HAZARD_WEATHER_FREEZING_RAIN": "CHUVA COM GELO", "ACCIDENT_MAJOR": "ACIDENTE GRAVE", "ACCIDENT_MINOR": "ACIDENTE LEVE",
    "JAM_HEAVY_TRAFFIC": "TRÂNSITO PESADO", "JAM_MODERATE_TRAFFIC": "TRÂNSITO MODERADO", "JAM_STAND_STILL_TRAFFIC": "TRÂNSITO PARADO",
    "JAM_LIGHT_TRAFFIC": "TRÂNSITO LEVE",
}

def translate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return df
    df = df.copy()
    if "type" in df.columns: df["type"] = df["type"].replace(TYPE_MAP)
    if "subtype" in df.columns:
        df["subtype"] = df["subtype"].replace(SUBTYPE_MAP)
        known_values = set(SUBTYPE_MAP.values())
        mask = df["subtype"].notna() & ~df["subtype"].isin(known_values)
        df.loc[mask, "subtype"] = (
            df.loc[mask, "subtype"].astype(str)
            .str.replace(r"^(HAZARD_ON_ROAD_|HAZARD_ON_SHOULDER_|HAZARD_WEATHER_|HAZARD_|ACCIDENT_|JAM_|ROAD_CLOSED_)","",regex=True)
            .str.replace("_", " ", regex=False).str.title()
        )
    return df

def parse_pt_date(value):
    if pd.isna(value): return pd.NaT
    try: return pd.to_datetime(value, dayfirst=True, errors="coerce")
    except Exception: return pd.NaT

def extract_wkt_coordinates(location_str):
    if pd.isna(location_str): return None, None
    match = re.search(r"Point\(([-\s\d\.]+)\)", str(location_str), re.IGNORECASE)
    if match:
        try:
            coords = match.group(1).strip().split()
            return float(coords[1]), float(coords[0])
        except Exception:
            pass
    return None, None

def normalize_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return df
    df = df.copy()
    if "pubMillis" in df.columns:
        df["timestamp"] = pd.to_datetime(df["pubMillis"], unit="ms", utc=True).dt.tz_convert("America/Sao_Paulo").dt.tz_localize(None)
    elif "Date" in df.columns:
        df["timestamp"] = df["Date"].apply(parse_pt_date)
    elif "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    else:
        df["timestamp"] = now_foz()
    df["date"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.date
    df["hour"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.hour
    df["day_of_week"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.day_name()
    df["month"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.month
    df["year"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.year
    return df

def _parse_dict_like(value):
    if isinstance(value, dict): return value
    if isinstance(value, str):
        try: return ast.literal_eval(value)
        except Exception: return None
    return None

def _extract_lat_lon_from_location(value):
    parsed = _parse_dict_like(value)
    if isinstance(parsed, dict):
        try: return float(parsed.get("y")), float(parsed.get("x"))
        except Exception: return None, None
    return None, None

def extract_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return df
    df = df.copy()
    if "lat" in df.columns and "lon" in df.columns:
        df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
        df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
        return df
    if "location" in df.columns:
        coords = df["location"].apply(lambda x: pd.Series(_extract_lat_lon_from_location(x), index=["lat", "lon"]))
        df["lat"] = coords["lat"]
        df["lon"] = coords["lon"]
    if "lat" not in df.columns and "y" in df.columns: df["lat"] = pd.to_numeric(df["y"], errors="coerce")
    if "lon" not in df.columns and "x" in df.columns: df["lon"] = pd.to_numeric(df["x"], errors="coerce")
    return df

def _extract_midpoint_from_line(value):
    try:
        points = value if isinstance(value, list) else ast.literal_eval(str(value))
        if not points: return None, None
        mid = points[len(points) // 2]
        return float(mid.get("y")), float(mid.get("x"))
    except Exception: return None, None

def extract_jams_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return df
    df = df.copy()
    if "lat" in df.columns and "lon" in df.columns:
        df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
        df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
        if df["lat"].notna().any(): return df
    if "line" in df.columns:
        coords = df["line"].apply(lambda x: pd.Series(_extract_midpoint_from_line(x), index=["lat", "lon"]))
        df["lat"] = coords["lat"]
        df["lon"] = coords["lon"]
        if df["lat"].notna().any(): return df
    if "location" in df.columns:
        coords = df["location"].apply(lambda x: pd.Series(_extract_lat_lon_from_location(x), index=["lat", "lon"]))
        df["lat"] = coords["lat"]
        df["lon"] = coords["lon"]
    if "lat" not in df.columns and "y" in df.columns: df["lat"] = pd.to_numeric(df["y"], errors="coerce")
    if "lon" not in df.columns and "x" in df.columns: df["lon"] = pd.to_numeric(df["x"], errors="coerce")
    return df

def normalize_speed(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return df
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

def filter_bbox_foz(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return df
    df = df.copy()
    if "lat" not in df.columns or "lon" not in df.columns: return pd.DataFrame()
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    return df[df["lat"].between(LAT_MIN, LAT_MAX) & df["lon"].between(LON_MIN, LON_MAX)].copy()

@st.cache_resource(show_spinner=False)
def get_drive_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    try:
        creds_info = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=["https://www.googleapis.com/auth/drive.readonly"])
        return build("drive", "v3", credentials=creds)
    except Exception:
        return None

def get_latest_h5_id(folder_id: str) -> str | None:
    service = get_drive_service()
    if not service: return None
    try:
        query = f"'{folder_id}' in parents and name contains '.h5' and trashed=false"
        results = service.files().list(q=query, fields="files(id, name, modifiedTime)", orderBy="modifiedTime desc", pageSize=20).execute()
        files = results.get("files", [])
        if not files: return None
        latest_id, latest_ts = None, -1
        for file_meta in files:
            match = re.search(r"(\d{8,})", file_meta["name"])
            if match:
                ts = int(match.group(1))
                if ts > latest_ts:
                    latest_ts = ts
                    latest_id = file_meta["id"]
        return latest_id if latest_id else files[0]["id"]
    except Exception:
        return None

@st.cache_data(ttl=600, show_spinner="📥 Baixando dados do Drive...")
def load_hdf_from_drive(file_id: str) -> pd.DataFrame:
    from googleapiclient.http import MediaIoBaseDownload
    service = get_drive_service()
    if not service: return pd.DataFrame()
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
        return pd.read_hdf(tmp_path, key="s")
    except Exception:
        return pd.DataFrame()
    finally:
        if tmp_path and os.path.exists(tmp_path): os.remove(tmp_path)

@st.cache_data(ttl=600, show_spinner="🔄 Carregando dados do Google Drive...")
def load_all_data():
    alerts_id = get_latest_h5_id(FOLDER_ALERTS_ID)
    alerts_id2 = get_latest_h5_id(FOLDER_ALERTS_ID2)
    jams_id = get_latest_h5_id(FOLDER_JAMS_ID)
    jams_id2 = get_latest_h5_id(FOLDER_JAMS_ID2)
    frames_alerts, frames_jams = [], []
    if alerts_id: frames_alerts.append(load_hdf_from_drive(alerts_id))
    if alerts_id2: frames_alerts.append(load_hdf_from_drive(alerts_id2))
    if jams_id: frames_jams.append(load_hdf_from_drive(jams_id))
    if jams_id2: frames_jams.append(load_hdf_from_drive(jams_id2))

    if frames_alerts:
        df_alerts = pd.concat(frames_alerts, ignore_index=True)
        dedup_cols = ["uuid"] if "uuid" in df_alerts.columns else [c for c in ["pubMillis", "street"] if c in df_alerts.columns]
        if dedup_cols: df_alerts = df_alerts.drop_duplicates(subset=dedup_cols)
    else:
        df_alerts = pd.DataFrame()

    if frames_jams:
        df_jams = pd.concat(frames_jams, ignore_index=True)
        dedup_cols = ["uuid"] if "uuid" in df_jams.columns else [c for c in ["pubMillis", "street"] if c in df_jams.columns]
        if dedup_cols: df_jams = df_jams.drop_duplicates(subset=dedup_cols)
    else:
        df_jams = pd.DataFrame()

    if not df_alerts.empty:
        df_alerts = normalize_timestamps(df_alerts)
        df_alerts = extract_coordinates(df_alerts)
        df_alerts = translate_dataframe(df_alerts)

    prob_matrix = {}
    if not df_alerts.empty and {"type", "day_of_week", "hour"}.issubset(df_alerts.columns):
        grp = df_alerts.groupby(["type", "day_of_week", "hour"]).size().unstack(fill_value=0)
        for idx, row in grp.iterrows():
            total = row.sum()
            prob_matrix[idx] = row.values / total if total > 0 else np.ones(24) / 24.0

    local_csv_frames = []
    local_csvs_found = []
    for csv_file_path in CSV_FILES_TO_MERGE:
        if os.path.exists(csv_file_path):
            try:
                df_local_csv = pd.read_csv(csv_file_path)
                rename_map = {}
                if "Street" in df_local_csv.columns: rename_map["Street"] = "street"
                if "Type" in df_local_csv.columns: rename_map["Type"] = "type"
                if "Subtype" in df_local_csv.columns: rename_map["Subtype"] = "subtype"
                df_local_csv = df_local_csv.rename(columns=rename_map)
                if "Location" in df_local_csv.columns:
                    coords_wkt = df_local_csv["Location"].apply(lambda x: pd.Series(extract_wkt_coordinates(x), index=["lat", "lon"]))
                    df_local_csv["lat"] = coords_wkt["lat"]
                    df_local_csv["lon"] = coords_wkt["lon"]
                df_local_csv = normalize_timestamps(df_local_csv)
                df_local_csv = translate_dataframe(df_local_csv)
                if {"type", "day_of_week", "date"}.issubset(df_local_csv.columns):
                    horas_estimadas = []
                    for _, row in df_local_csv.iterrows():
                        tipo_evento = row.get("type", "HAZARD")
                        dia_semana = row.get("day_of_week", "Monday")
                        if (tipo_evento, dia_semana) in prob_matrix:
                            hora_estimada = int(np.random.choice(range(24), p=prob_matrix[(tipo_evento, dia_semana)]))
                        else:
                            hora_estimada = int(np.random.choice(range(24)))
                        horas_estimadas.append(hora_estimada)
                    df_local_csv["hour"] = horas_estimadas
                    df_local_csv["timestamp"] = df_local_csv.apply(lambda row: datetime.combine(row["date"], time(hour=int(row["hour"]))) if pd.notna(row["date"]) else row["timestamp"], axis=1)
                local_csv_frames.append(df_local_csv)
                local_csvs_found.append(csv_file_path)
            except Exception:
                continue

    if local_csv_frames:
        df_local_merged = pd.concat(local_csv_frames, ignore_index=True)
        dedup_local_cols = [col for col in ["uuid", "street", "type", "subtype", "timestamp", "lat", "lon"] if col in df_local_merged.columns]
        if dedup_local_cols: df_local_merged = df_local_merged.drop_duplicates(subset=dedup_local_cols)
        df_alerts = pd.concat([df_alerts, df_local_merged], ignore_index=True) if not df_alerts.empty else df_local_merged

    if not df_alerts.empty:
        dedup_cols = ["uuid"] if "uuid" in df_alerts.columns else [c for c in ["timestamp", "street"] if c in df_alerts.columns]
        if dedup_cols: df_alerts = df_alerts.drop_duplicates(subset=dedup_cols)
        df_alerts = normalize_timestamps(df_alerts)
        df_alerts = extract_coordinates(df_alerts)
        df_alerts = translate_dataframe(df_alerts)
        if "street" not in df_alerts.columns: df_alerts["street"] = "N/A"

    if not df_jams.empty:
        df_jams = normalize_timestamps(df_jams)
        df_jams = extract_jams_coordinates(df_jams)
        df_jams = normalize_speed(df_jams)
        if "street" not in df_jams.columns: df_jams["street"] = "Via"

    load_metadata = {
        "local_csvs_found": local_csvs_found,
        "local_csv_count": len(local_csvs_found),
        "local_rows_merged": int(sum(len(df) for df in local_csv_frames)) if local_csv_frames else 0,
    }
    return df_alerts, df_jams, load_metadata

def create_folium_map_with_compass(lat: float, lon: float, zoom_level: int = 13) -> folium.Map:
    m = folium.Map(location=[lat, lon], zoom_start=zoom_level, tiles="OpenStreetMap", max_bounds=True, control_scale=False)
    plugins.MousePosition(position="topright", separator=" | ", prefix="Lat/Lon: ", num_digits=5).add_to(m)
    plugins.Fullscreen(position="topleft", title="Expandir mapa", title_cancel="Sair da tela cheia", force_separate_button=True).add_to(m)
    folium.LayerControl(position="topright", collapsed=True).add_to(m)
    return m

def load_json_df(df_json: str) -> pd.DataFrame:
    try: return pd.read_json(io.StringIO(df_json))
    except Exception: return pd.DataFrame()

def safe_time_label(value) -> str:
    try:
        if pd.notna(value): return pd.to_datetime(value).strftime("%H:%M")
    except Exception: pass
    return "--"

def generate_incidents_map(df_json: str) -> folium.Map | None:
    df = load_json_df(df_json)
    if df.empty or "lat" not in df.columns or "lon" not in df.columns: return None
    df_map = filter_bbox_foz(df.dropna(subset=["lat", "lon"])).head(50)
    if df_map.empty: return None
    m = create_folium_map_with_compass(df_map["lat"].mean(), df_map["lon"].mean())
    for _, row in df_map.iterrows():
        try:
            tipo, subtipo, rua = str(row.get("type", "?")), str(row.get("subtype", "")), str(row.get("street", "N/A"))
            color = get_danger_color(tipo, row.get("subtype"))
            ts = safe_time_label(row.get("timestamp"))
            folium.CircleMarker(location=[float(row["lat"]), float(row["lon"])], radius=9, popup=f"{tipo} - {subtipo} - {rua} - {ts}", color=color, fill=True, fillColor=color, fillOpacity=0.8, weight=2).add_to(m)
        except Exception:
            continue
    return m

def generate_jams_map(df_json: str) -> folium.Map | None:
    df = load_json_df(df_json)
    if df.empty or "lat" not in df.columns or "lon" not in df.columns: return None
    df_valid = filter_bbox_foz(df.dropna(subset=["lat", "lon"])).head(40)
    if df_valid.empty: return None
    m = create_folium_map_with_compass(df_valid["lat"].mean(), df_valid["lon"].mean())
    for _, row in df_valid.iterrows():
        try:
            speed_raw = row.get("speed", float("nan"))
            speed_kmh = float(speed_raw) * 3.6 if pd.notna(speed_raw) else 0.0
            color = get_congestion_color(speed_kmh)
            rua = str(row.get("street", "Via"))
            ts = safe_time_label(row.get("timestamp"))
            folium.CircleMarker(location=[float(row["lat"]), float(row["lon"])] , radius=7, popup=f"{speed_kmh:.0f} km/h - {rua} - {ts}", color=color, fill=True, fillColor=color, fillOpacity=0.7, weight=2).add_to(m)
        except Exception:
            continue
    return m

def apply_base_time_filter(df: pd.DataFrame, selected_date, hora_range: tuple[int, int]) -> pd.DataFrame:
    if df is None or df.empty: return pd.DataFrame()
    df = df.copy()
    if "date" not in df.columns or "hour" not in df.columns: return pd.DataFrame()
    df_date_col = pd.to_datetime(df["date"], errors="coerce").dt.date
    target_date = pd.to_datetime(selected_date).date()
    return df[(df_date_col == target_date) & (df["hour"].between(hora_range[0], hora_range[1]))].copy()

def classify_traffic_status(media_vel_kmh: float) -> str:
    if media_vel_kmh < 20: return "🔴 Crítico"
    elif media_vel_kmh < 40: return "🟠 Lento"
    elif media_vel_kmh < 60: return "🟡 Moderado"
    return "🟢 Fluindo"

hora_foz_atual = now_foz()
st.sidebar.header("⚙️ Controles")
st.sidebar.markdown("### ⏳ Status da Sessão")
st.sidebar.markdown(f"**Hora atual Foz:** {hora_foz_atual.strftime('%d/%m/%Y %H:%M:%S')}")
st.sidebar.metric("Tempo online", f"{tempo_total // 3600}h {(tempo_total % 3600) // 60:02d}m")
st.sidebar.metric("Próximo ciclo", f"{minutos_restantes}:{segundos_restantes:02d}")
st.sidebar.metric("Atualizações", st.session_state.manual_refreshes)
if st.sidebar.button("ATUALIZAR DADOS AGORA", use_container_width=True, type="primary"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.session_state.manual_refreshes += 1
    st.rerun()

try:
    df_alerts_raw, df_jams_raw, load_metadata = load_all_data()
except Exception as e:
    st.error(f"Erro ao conectar com o Google Drive: {e}")
    st.stop()

st.sidebar.subheader("📦 Fusão local")
st.sidebar.metric("CSV locais encontrados", load_metadata.get("local_csv_count", 0))
st.sidebar.metric("Linhas locais lidas", load_metadata.get("local_rows_merged", 0))
for csv_name in load_metadata.get("local_csvs_found", []):
    st.sidebar.caption(f"• {csv_name}")

all_dates = set()
if not df_alerts_raw.empty and "date" in df_alerts_raw.columns: all_dates.update(pd.to_datetime(df_alerts_raw["date"]).dt.date.unique())
if not df_jams_raw.empty and "date" in df_jams_raw.columns: all_dates.update(pd.to_datetime(df_jams_raw["date"]).dt.date.unique())
today_foz = hora_foz_atual.date()
if all_dates:
    min_date, max_date = min(all_dates), max(all_dates)
    default_date = today_foz if today_foz in all_dates else max_date
else:
    min_date = max_date = default_date = today_foz

selected_date = st.sidebar.date_input("📅 Data", value=default_date, min_value=min_date, max_value=max_date)
hora_range = st.sidebar.slider("🕒 Horário", min_value=0, max_value=23, value=(0, 23))

df_filtered = apply_base_time_filter(df_alerts_raw, selected_date, hora_range)
df_jams_filtered = apply_base_time_filter(df_jams_raw, selected_date, hora_range)

st.title("Monitoramento de Tráfego — Foz do Iguaçu")
st.caption("Versão com fusão plurianual local via CSV_FILES_TO_MERGE")
col1, col2, col3 = st.columns(3)
col1.metric("Alertas filtrados", len(df_filtered))
col2.metric("Jams filtrados", len(df_jams_filtered))
vel_media = (df_jams_filtered["speed"].mean() * 3.6) if (not df_jams_filtered.empty and "speed" in df_jams_filtered.columns and df_jams_filtered["speed"].notna().any()) else 0
col3.metric("Vel. média", f"{vel_media:.1f} km/h", classify_traffic_status(vel_media))

tab1, tab2, tab3 = st.tabs(["Incidentes", "Congestionamentos", "Dados"])
with tab1:
    if not df_filtered.empty:
        m = generate_incidents_map(df_filtered.to_json(date_format="iso"))
        if m: st_folium(m, width="100%", height=500)
        st.dataframe(df_filtered.head(500), use_container_width=True)
    else:
        st.info("Nenhum incidente para os filtros aplicados.")
with tab2:
    if not df_jams_filtered.empty:
        m = generate_jams_map(df_jams_filtered.to_json(date_format="iso"))
        if m: st_folium(m, width="100%", height=500)
        st.dataframe(df_jams_filtered.head(500), use_container_width=True)
    else:
        st.info("Nenhum congestionamento para os filtros aplicados.")
with tab3:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Alertas brutos")
        st.dataframe(df_alerts_raw.head(300), use_container_width=True)
    with c2:
        st.subheader("Jams brutos")
        st.dataframe(df_jams_raw.head(300), use_container_width=True)
