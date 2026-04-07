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
st.set_page_config(page_title="Waze Foz do Iguaçu", layout="wide", page_icon="🚗")

# =============================================
# 2. TIMEZONE E HORA LOCAL
# =============================================
TZ_FOZ = ZoneInfo("America/Sao_Paulo")

def now_foz():
    return datetime.now(TZ_FOZ).replace(tzinfo=None)

# =============================================
# 3. ESTADO DA SESSÃO
# =============================================
if "app_start_time" not in st.session_state:
    st.session_state.app_start_time = now_foz()
    st.session_state.manual_refreshes = 0

_start = st.session_state.app_start_time
_now   = now_foz()
if hasattr(_start, "tzinfo") and _start.tzinfo is not None:
    _start = _start.replace(tzinfo=None)
    st.session_state.app_start_time = _start

tempo_sessao       = (_now - _start).total_seconds()
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
    if speed_kmh >= 80:   return "#00AA00"
    elif speed_kmh >= 60: return "#55DD00"
    elif speed_kmh >= 40: return "#DDDD00"
    elif speed_kmh >= 20: return "#FF8800"
    else:                 return "#FF0000"

def get_danger_color(incident_type):
    if pd.isna(incident_type) or str(incident_type).strip() == "":
        return "#0099FF"
    danger_colors = {
        "ACIDENTE":         "#FF0000",
        "VIA FECHADA":      "#FF4400",
        "CONGESTIONAMENTO": "#FFAA00",
        "PERIGO":           "#FF6600",
        "ALERTA":           "#FFDD00",
        "OBRAS":            "#AAAAAA",
    }
    return danger_colors.get(str(incident_type).upper().strip(), "#0099FF")

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
    return build("drive", "v3", credentials=creds)

def get_latest_h5_id(folder_id):
    service = get_drive_service()
    query   = "'" + folder_id + "' in parents and name contains '.h5' and trashed=false"
    results = service.files().list(
        q=query,
        fields="files(id, name, modifiedTime)",
        orderBy="modifiedTime desc",
        pageSize=20
    ).execute()
    files = results.get("files", [])
    if not files:
        return None
    latest_id, latest_ts = None, -1
    for f in files:
        match = re.search(r"(\d{8,})", f["name"])
        if match:
            ts = int(match.group(1))
            if ts > latest_ts:
                latest_ts = ts
                latest_id = f["id"]
    return latest_id if latest_id else files[0]["id"]

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
    with tempfile.NamedTemporaryFile(delete=False, suffix=".h5") as tmp:
        tmp.write(fh.getvalue())
        tmp_path = tmp.name
    return pd.read_hdf(tmp_path, key="s")

# =============================================
# 7. NORMALIZAÇÃO DE TIMESTAMPS
# =============================================
def normalize_timestamps(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    if "pubMillis" in df.columns:
        df["timestamp"] = (
            pd.to_datetime(df["pubMillis"], unit="ms", utc=True)
            .dt.tz_convert("America/Sao_Paulo")
            .dt.tz_localize(None)
        )
    elif "timestamp" not in df.columns:
        df["timestamp"] = datetime.now()
    df["date"]        = df["timestamp"].dt.date
    df["hour"]        = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.day_name()
    return df

# =============================================
# 8. EXTRAÇÃO DE COORDENADAS (alerts — usa "location")
# =============================================
def extract_coordinates(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    if "lat" in df.columns and "lon" in df.columns:
        return df
    if "location" in df.columns:
        try:
            sample = df["location"].dropna().iloc[0] if not df["location"].dropna().empty else None
            if isinstance(sample, str):
                df["location"] = df["location"].apply(
                    lambda x: ast.literal_eval(x) if isinstance(x, str) else x
                )
            df["lat"] = df["location"].apply(lambda x: float(x.get("y", 0)) if isinstance(x, dict) else None)
            df["lon"] = df["location"].apply(lambda x: float(x.get("x", 0)) if isinstance(x, dict) else None)
        except Exception:
            pass
    if "lat" not in df.columns and "y" in df.columns:
        df["lat"] = pd.to_numeric(df["y"], errors="coerce")
    if "lon" not in df.columns and "x" in df.columns:
        df["lon"] = pd.to_numeric(df["x"], errors="coerce")
    return df

# =============================================
# 9. EXTRAÇÃO DE COORDENADAS PARA JAMS (usa "line" → ponto médio)
#    FIX PRINCIPAL: jams do Waze armazenam segmentos em "line",
#    não em "location". Extraímos o ponto central do array.
# =============================================
def extract_jams_coordinates(df):
    if df is None or df.empty:
        return df
    df = df.copy()

    if "lat" in df.columns and "lon" in df.columns:
        df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
        df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
        return df

    if "line" in df.columns:
        def _midpoint(val):
            try:
                pts = val if isinstance(val, list) else ast.literal_eval(str(val))
                if not pts:
                    return None, None
                mid = pts[len(pts) // 2]
                return float(mid.get("y")), float(mid.get("x"))
            except Exception:
                return None, None
        coords      = df["line"].apply(lambda x: pd.Series(_midpoint(x), index=["lat", "lon"]))
        df["lat"]   = coords["lat"]
        df["lon"]   = coords["lon"]
        return df

    if "location" in df.columns:
        try:
            sample = df["location"].dropna().iloc[0] if not df["location"].dropna().empty else None
            if isinstance(sample, str):
                df["location"] = df["location"].apply(
                    lambda x: ast.literal_eval(x) if isinstance(x, str) else x
                )
            df["lat"] = df["location"].apply(lambda x: float(x.get("y", 0)) if isinstance(x, dict) else None)
            df["lon"] = df["location"].apply(lambda x: float(x.get("x", 0)) if isinstance(x, dict) else None)
        except Exception:
            pass

    if "lat" not in df.columns and "y" in df.columns:
        df["lat"] = pd.to_numeric(df["y"], errors="coerce")
    if "lon" not in df.columns and "x" in df.columns:
        df["lon"] = pd.to_numeric(df["x"], errors="coerce")
    return df

# =============================================
# 10. NORMALIZAÇÃO DE VELOCIDADE
# =============================================
def normalize_speed(df):
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

# =============================================
# 11. TRADUÇÕES WAZE → PT-BR
# =============================================
TYPE_MAP = {
    "ROAD_CLOSED": "VIA FECHADA", "ROAD_CLOSED_CONSTRUCTION": "VIA FECHADA",
    "ROAD_CLOSED_EVENT": "VIA FECHADA", "HAZARD": "PERIGO",
    "ACCIDENT": "ACIDENTE", "JAM": "CONGESTIONAMENTO",
    "WEATHERHAZARD": "PERIGO CLIMÁTICO",
}
SUBTYPE_MAP = {
    "ROAD_CLOSED_CONSTRUCTION": "OBRAS", "ROAD_CLOSED_EVENT": "EVENTO",
    "HAZARD_ON_ROAD": "PERIGO NA VIA", "HAZARD_ON_SHOULDER": "PERIGO NO ACOSTAMENTO",
    "HAZARD_WEATHER": "CONDIÇÕES CLIMÁTICAS", "HAZARD_ON_ROAD_POT_HOLE": "BURACO NA VIA",
    "HAZARD_ON_ROAD_ROAD_KILL": "ANIMAL NA VIA", "HAZARD_ON_ROAD_CAR_STOPPED": "VEÍCULO PARADO",
    "HAZARD_ON_ROAD_CONSTRUCTION": "OBRAS NA VIA", "HAZARD_ON_ROAD_OBJECT": "OBJETO NA VIA",
    "HAZARD_ON_ROAD_TRAFFIC_LIGHT_FAULT": "SEMÁFORO QUEBRADO",
    "HAZARD_WEATHER_FOG": "NEBLINA", "HAZARD_WEATHER_HAIL": "GRANIZO",
    "HAZARD_WEATHER_HEAVY_RAIN": "CHUVA FORTE", "HAZARD_WEATHER_FLOOD": "INUNDAÇÃO",
    "ACCIDENT_MAJOR": "ACIDENTE GRAVE", "ACCIDENT_MINOR": "ACIDENTE LEVE",
    "JAM_HEAVY_TRAFFIC": "TRÂNSITO PESADO", "JAM_MODERATE_TRAFFIC": "TRÂNSITO MODERADO",
    "JAM_STAND_STILL_TRAFFIC": "TRÂNSITO PARADO",
}

def translate_dataframe(df):
    if df is None or df.empty:
        return df
    df = df.copy()
    if "type" in df.columns:
        df["type"] = df["type"].replace(TYPE_MAP)
    if "subtype" in df.columns:
        df["subtype"] = df["subtype"].replace(SUBTYPE_MAP)
    return df

# =============================================
# 12. PIPELINE PRINCIPAL DE DADOS
#     FIX: jams usam extract_jams_coordinates (via "line")
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
        if "street" not in df_alerts.columns:
            df_alerts["street"] = "N/A"

    if not df_jams.empty:
        df_jams = normalize_timestamps(df_jams)
        df_jams = extract_jams_coordinates(df_jams)   # usa "line"
        df_jams = normalize_speed(df_jams)
        if "street" not in df_jams.columns:
            df_jams["street"] = "Via"

    return df_alerts, df_jams

# =============================================
# 13. FUNÇÕES DE MAPA
# =============================================
LAT_MIN, LAT_MAX = -25.70, -25.40
LON_MIN, LON_MAX = -54.75, -54.45

def create_folium_map_with_compass(lat, lon, zoom_level=13):
    m = folium.Map(location=[lat, lon], zoom_start=zoom_level, tiles="OpenStreetMap", max_bounds=True)
    plugins.MousePosition(position="topright", separator=" | ", prefix="Lat/Lon: ", num_digits=5).add_to(m)
    plugins.MeasureControl(position="bottomright").add_to(m)
    north_html = (
        '<div style="position:fixed;top:10px;left:10px;width:45px;height:45px;'
        'background:linear-gradient(145deg,#f0f0f0,#e6e6e6);'
        'border:2px solid #333;border-radius:8px;z-index:1000;'
        'box-shadow:0 2px 10px rgba(0,0,0,0.3);'
        'display:flex;align-items:center;justify-content:center;'
        'font-weight:bold;font-size:18px;">'
        '<div style="color:#d32f2f;text-shadow:1px 1px 1px white;">&#x2191;</div>'
        '<div style="position:absolute;bottom:2px;font-size:9px;color:#333;font-weight:bold;">N</div>'
        '</div>'
    )
    folium.Element(north_html).add_to(m)
    folium.LayerControl(position="topright", collapsed=True).add_to(m)
    return m

@st.cache_resource(ttl=600, show_spinner=False)
def generate_incidents_map(df_json):
    df = pd.read_json(io.StringIO(df_json))
    if df.empty:
        return None
    if "lat" not in df.columns and "y" in df.columns:
        df["lat"] = pd.to_numeric(df["y"], errors="coerce")
    if "lon" not in df.columns and "x" in df.columns:
        df["lon"] = pd.to_numeric(df["x"], errors="coerce")
    if "lat" not in df.columns and "location" in df.columns:
        def _gy(x):
            try:   return float((ast.literal_eval(x) if isinstance(x, str) else x).get("y"))
            except: return None
        def _gx(x):
            try:   return float((ast.literal_eval(x) if isinstance(x, str) else x).get("x"))
            except: return None
        df["lat"] = df["location"].apply(_gy)
        df["lon"] = df["location"].apply(_gx)
    if "lat" not in df.columns or "lon" not in df.columns:
        return None
    df_map = df.dropna(subset=["lat", "lon"]).head(50)
    df_map = df_map[df_map["lat"].between(LAT_MIN, LAT_MAX) & df_map["lon"].between(LON_MIN, LON_MAX)]
    if df_map.empty:
        return None
    m = create_folium_map_with_compass(df_map["lat"].mean(), df_map["lon"].mean())
    for _, row in df_map.iterrows():
        try:
            color        = get_danger_color(row.get("type", "ALERTA"))
            ts           = pd.to_datetime(row["timestamp"]).strftime("%H:%M") if pd.notna(row.get("timestamp")) else "--"
            tipo         = row.get("type", "?")
            subtipo      = row.get("subtype", "")
            rua          = row.get("street", "N/A")
            lat_val      = float(row["lat"])
            lon_val      = float(row["lon"])
            popup_html   = (
                '<div style="min-width:200px;font-family:Arial;">'
                '<b style="color:' + color + ';font-size:16px;">🚨 ' + str(tipo) + '</b><br>'
                '<b>' + str(subtipo) + '</b><br>'
                '🛣️ <i>' + str(rua) + '</i><br>'
                '🕒 ' + ts + '<br>'
                '📍 ' + f"{lat_val:.4f}, {lon_val:.4f}" +
                '</div>'
            )
            folium.CircleMarker(
                location=[lat_val, lon_val],
                radius=9,
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=str(tipo) + ": " + str(rua),
                color=color, fill=True, fillColor=color, fillOpacity=0.8, weight=2
            ).add_to(m)
        except Exception:
            continue
    return m

@st.cache_resource(ttl=600, show_spinner=False)
def generate_jams_map(df_json):
    df = pd.read_json(io.StringIO(df_json))
    if df.empty:
        return None

    # FIX: extrai ponto médio do campo "line" se lat/lon ausentes ou todos NaN
    if "lat" not in df.columns or df["lat"].isna().all():
        if "line" in df.columns:
            def _midpoint(val):
                try:
                    pts = val if isinstance(val, list) else ast.literal_eval(str(val))
                    if not pts:
                        return None, None
                    mid = pts[len(pts) // 2]
                    return float(mid.get("y")), float(mid.get("x"))
                except Exception:
                    return None, None
            coords    = df["line"].apply(lambda x: pd.Series(_midpoint(x), index=["lat", "lon"]))
            df["lat"] = coords["lat"]
            df["lon"] = coords["lon"]

    if "lat" not in df.columns and "y" in df.columns:
        df["lat"] = pd.to_numeric(df["y"], errors="coerce")
    if "lon" not in df.columns and "x" in df.columns:
        df["lon"] = pd.to_numeric(df["x"], errors="coerce")
    if "lat" not in df.columns and "location" in df.columns:
        def _get_y(x):
            try:   return float((ast.literal_eval(x) if isinstance(x, str) else x).get("y"))
            except: return None
        def _get_x(x):
            try:   return float((ast.literal_eval(x) if isinstance(x, str) else x).get("x"))
            except: return None
        df["lat"] = df["location"].apply(_get_y)
        df["lon"] = df["location"].apply(_get_x)

    if "speed" not in df.columns or df["speed"].isna().all():
        for alt in ["speedKMH", "speedkmh", "speed_kmh", "velocity"]:
            if alt in df.columns:
                df["speed"] = pd.to_numeric(df[alt], errors="coerce") / 3.6
                break
        else:
            df["speed"] = float("nan")
    else:
        df["speed"] = pd.to_numeric(df["speed"], errors="coerce")

    if "lat" not in df.columns or "lon" not in df.columns:
        return None

    df_valid = df.dropna(subset=["lat", "lon"]).head(40)
    df_valid = df_valid[df_valid["lat"].between(LAT_MIN, LAT_MAX) & df_valid["lon"].between(LON_MIN, LON_MAX)]

    lat_col = df["lat"] if "lat" in df.columns else pd.Series([])
    valid_count = int(df_valid["lat"].notna().sum()) if not df_valid.empty else 0
    print("[JAMS MAP] total=" + str(len(df)) + " | validos bbox=" + str(valid_count))
    if not df_valid.empty:
        if not df_valid.empty and "lat" in df_valid.columns:
            lat_min_s = str(round(float(df_valid["lat"].min()), 4))
            lat_max_s = str(round(float(df_valid["lat"].max()), 4))
            print("[JAMS MAP] lat range: " + lat_min_s + "~" + lat_max_s)

    if df_valid.empty:
        return None

    m = create_folium_map_with_compass(df_valid["lat"].mean(), df_valid["lon"].mean())
    for _, row in df_valid.iterrows():
        try:
            speed_raw  = row.get("speed", float("nan"))
            speed_kmh  = float(speed_raw) * 3.6 if pd.notna(speed_raw) else 0.0
            color      = get_congestion_color(speed_kmh)
            ts         = pd.to_datetime(row["timestamp"]).strftime("%H:%M") if pd.notna(row.get("timestamp")) else "--"
            rua        = row.get("street", "Via")
            lat_val    = float(row["lat"])
            lon_val    = float(row["lon"])
            popup_html = (
                '<div style="min-width:180px;">'
                '<b style="color:' + color + '">🚗 ' + f"{speed_kmh:.0f}" + ' km/h</b><br>'
                '🛣️ <i>' + str(rua) + '</i><br>'
                '🕒 ' + ts +
                '</div>'
            )
            folium.CircleMarker(
                location=[lat_val, lon_val],
                radius=7,
                popup=folium.Popup(popup_html, max_width=220),
                tooltip=f"{speed_kmh:.0f}" + "km/h - " + str(rua),
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
    if "lat" not in df.columns and "y" in df.columns:
        df["lat"] = pd.to_numeric(df["y"], errors="coerce")
    if "lon" not in df.columns and "x" in df.columns:
        df["lon"] = pd.to_numeric(df["x"], errors="coerce")
    if "lat" not in df.columns or "lon" not in df.columns:
        return None
    df_map = df.dropna(subset=["lat", "lon"])
    if df_map.empty:
        return None
    m = create_folium_map_with_compass(df_map["lat"].mean(), df_map["lon"].mean())
    heat_data = [[row["lat"], row["lon"]] for _, row in df_map.iterrows()]
    plugins.HeatMap(heat_data, radius=15, blur=10).add_to(m)
    return m

# =============================================
# 14. SIDEBAR
# =============================================
hora_foz_atual = now_foz()

st.sidebar.header("⚙️ Controles")
st.sidebar.markdown("### ⏰ Status da Sessão")
st.sidebar.markdown("🕐 **Hora atual (Foz):** `" + hora_foz_atual.strftime("%d/%m/%Y %H:%M:%S") + "`")
st.sidebar.metric("⏳ Tempo online",  str(tempo_total // 3600) + "h:" + str((tempo_total % 3600) // 60).zfill(2) + "m")
st.sidebar.metric("⏳ Próximo ciclo", str(minutos_restantes) + ":" + str(segundos_restantes).zfill(2))
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
    st.error("❌ Erro ao conectar com o Google Drive: " + str(e))
    st.markdown("""
    **Verifique:**
    - As credenciais `gcp_service_account` estão configuradas em **Settings → Secrets**
    - A Service Account tem acesso às pastas do Drive
    - Os arquivos `.h5` existem nas pastas configuradas
    """)
    st.stop()

for df_ref in [df_alerts_raw, df_jams_raw]:
    if not df_ref.empty:
        if "hour" not in df_ref.columns:
            df_ref["hour"] = df_ref["timestamp"].dt.hour
        if "date" not in df_ref.columns:
            df_ref["date"] = df_ref["timestamp"].dt.date

# =============================================
# 16. FILTROS NA SIDEBAR
# =============================================
st.sidebar.subheader("🔍 Filtros")
today_foz = hora_foz_atual.date()

all_dates = set()
if not df_alerts_raw.empty: all_dates.update(df_alerts_raw["date"].unique())
if not df_jams_raw.empty:   all_dates.update(df_jams_raw["date"].unique())

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
    max_value=max(max_date, today_foz)
)

tipos_disponiveis = sorted(df_alerts_raw["type"].dropna().unique().tolist()) if not df_alerts_raw.empty else []
filtro_tipo = st.sidebar.multiselect("🚨 Tipo de Alerta", options=tipos_disponiveis, default=tipos_disponiveis)
filtro_rua  = st.sidebar.text_input("🛣️ Buscar Rua", placeholder="Ex: Av. Brasil")
hora_range  = st.sidebar.slider("⏰ Horário", 0, 23, (0, 23))

# =============================================
# 17. APLICAÇÃO DOS FILTROS COM FALLBACK
# =============================================
df_filtered = pd.DataFrame()
if not df_alerts_raw.empty:
    df_filtered = df_alerts_raw[
        (df_alerts_raw["date"] == selected_date) &
        (df_alerts_raw["type"].isin(filtro_tipo)) &
        (df_alerts_raw["hour"].between(hora_range[0], hora_range[1]))
    ].copy()
    if filtro_rua:
        df_filtered = df_filtered[df_filtered["street"].str.contains(filtro_rua, case=False, na=False)]
    if df_filtered.empty:
        st.sidebar.warning("⚠️ Sem dados em " + str(selected_date) + ". Exibindo dados mais recentes.")
        df_filtered = df_alerts_raw[
            (df_alerts_raw["type"].isin(filtro_tipo)) &
            (df_alerts_raw["hour"].between(hora_range[0], hora_range[1]))
        ].copy()

df_jams_filtered = pd.DataFrame()
if not df_jams_raw.empty:
    df_jams_filtered = df_jams_raw[
        (df_jams_raw["date"] == selected_date) &
        (df_jams_raw["hour"].between(hora_range[0], hora_range[1]))
    ].copy()
    if df_jams_filtered.empty:
        df_jams_filtered = df_jams_raw[df_jams_raw["hour"].between(hora_range[0], hora_range[1])].copy()

# =============================================
# 18. CABEÇALHO
# =============================================
st.title("🚗 Monitoramento de Tráfego — Foz do Iguaçu | " + selected_date.strftime("%d/%m/%Y"))
st.success(
    "✅ **Dados reais** carregados do Google Drive | "
    "🕐 Hora local (Foz): **" + hora_foz_atual.strftime("%H:%M:%S") + "**",
    icon="🟢"
)
st.markdown("---")

# =============================================
# 19. RESUMO DOS FILTROS ATIVOS
# =============================================
col_f1, col_f2, col_f3, col_f4 = st.columns(4)
col_f1.metric("📅 Data",    selected_date.strftime("%d/%m/%Y"))
col_f2.metric("🚨 Alertas", str(len(filtro_tipo)) + " tipos")
col_f3.metric("🛣️ Rua",     ("'" + filtro_rua + "'") if filtro_rua else "Todas")
col_f4.metric("⏰ Horário", str(hora_range[0]).zfill(2) + ":00–" + str(hora_range[1]).zfill(2) + ":59")
st.markdown("---")

# =============================================
# 20. KPIs PRINCIPAIS
# =============================================
st.subheader("📊 Resumo Estatístico")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

incidentes_dia   = len(df_filtered)
acidentes_graves = len(df_filtered[df_filtered["type"] == "ACIDENTE"]) if not df_filtered.empty else 0
v_media_kmh      = (
    df_jams_filtered["speed"].mean() * 3.6
    if not df_jams_filtered.empty
    and "speed" in df_jams_filtered.columns
    and df_jams_filtered["speed"].notna().any()
    else 0
)
status_via = "🚫 Crítico" if incidentes_dia > 15 else ("⚠️ Moderado" if incidentes_dia > 5 else "✅ Normal")

kpi1.metric("Total Alertas", incidentes_dia)
kpi2.metric("Acidentes",     acidentes_graves)
kpi3.metric("Vel. Média",    f"{v_media_kmh:.1f} km/h")
kpi4.metric("Status da Via", status_via)
st.markdown("---")

# =============================================
# 21. INDICADORES VISUAIS DE GRAVIDADE
# =============================================
st.subheader("📈 Indicadores de Gravidade")
col_grav, col_vel = st.columns(2)

gravidade = min(75, incidentes_dia * 5)
cor_grav  = "#FF0000" if gravidade >= 75 else ("#FF8800" if gravidade >= 50 else ("#FFDD00" if gravidade >= 25 else "#00AA00"))

with col_grav:
    fig_grav = px.bar_polar(r=[gravidade], theta=[0], range_r=[0, 100], color_discrete_sequence=[cor_grav])
    fig_grav.update_layout(
        title="🚨 Gravidade: " + str(incidentes_dia) + " incidentes",
        polar=dict(radialaxis=dict(range=[0, 100], showticklabels=False), angularaxis=dict(showticklabels=False)),
        showlegend=False, height=220
    )
    st.plotly_chart(fig_grav, use_container_width=True)

cor_vel = "green" if v_media_kmh > 40 else ("yellow" if v_media_kmh > 20 else "red")
with col_vel:
    fig_vel = px.bar_polar(r=[v_media_kmh], theta=[0], range_r=[0, 80], color_discrete_sequence=[cor_vel])
    fig_vel.update_layout(
        title="🚗 Velocidade Média: " + f"{v_media_kmh:.1f}" + " km/h",
        polar=dict(radialaxis=dict(range=[0, 80], showticklabels=False), angularaxis=dict(showticklabels=False)),
        showlegend=False, height=220
    )
    st.plotly_chart(fig_vel, use_container_width=True)

st.markdown("---")

# =============================================
# 22. ABAS DE VISUALIZAÇÃO
# =============================================
st.subheader("🗺️ Visualizações")
tab_inc, tab_jams, tab_calor, tab_graficos, tab_dados = st.tabs([
    "📍 Incidentes", "🚗 Congestionamentos", "🔥 Mapa de Calor", "📊 Gráficos", "📋 Dados Detalhados"
])

# --- ABA 1: Incidentes ---
with tab_inc:
    st.caption("📍 Centro: -25.54, -54.58 | 🧭 Norte ↑ | Clique nos pontos para detalhes")
    if not df_filtered.empty:
        m_inc = generate_incidents_map(df_filtered.to_json(date_format="iso"))
        if m_inc:
            st_folium(m_inc, width="100%", height=500, key="mapa_inc")
        else:
            st.info("⚠️ Nenhum incidente dentro da área de Foz do Iguaçu.")
    else:
        st.info("Nenhum incidente com os filtros aplicados.")

# --- ABA 2: Congestionamentos ---
with tab_jams:
    st.caption("📏 Escala métrica | 🟢 Livre → 🔴 Parado")
    st.caption("🔍 Jams disponíveis: " + str(len(df_jams_raw)) + " total | " + str(len(df_jams_filtered)) + " após filtro de data/hora")
    if not df_jams_filtered.empty:
        m_jam = generate_jams_map(df_jams_filtered.to_json(date_format="iso"))
        if m_jam:
            st_folium(m_jam, width="100%", height=500, key="mapa_jam")
            st.markdown("**Legenda:** 🟢 >80 km/h | 🟡 40–80 km/h | 🟠 20–40 km/h | 🔴 <20 km/h")
        else:
            st.warning("⚠️ Congestionamentos carregados, mas sem coordenadas válidas na área de Foz.")
            cols_diag = [c for c in ["lat", "lon", "line", "speed", "street"] if c in df_jams_filtered.columns]
            if cols_diag:
                st.caption("📋 Amostra dos dados de jams (5 primeiras linhas):")
                st.dataframe(df_jams_filtered[cols_diag].head(5), use_container_width=True)
    else:
        st.info("Nenhum congestionamento para exibir.")

# --- ABA 3: Mapa de Calor ---
with tab_calor:
    st.subheader("Zonas de Concentração de Incidentes")
    if not df_filtered.empty:
        m_heat = generate_heatmap(df_filtered.to_json(date_format="iso"))
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
                df_filtered["hour"].value_counts().sort_index().reset_index(),
                x="hour", y="count",
                labels={"hour": "Hora (Foz UTC-3)", "count": "Qtd"},
                color="count", color_continuous_scale="Reds"
            )
            st.plotly_chart(fig_hora, use_container_width=True)
        with col_g2:
            st.subheader("🥧 Proporção por Tipo")
            fig_pie = px.pie(df_filtered, names="type", color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig_pie, use_container_width=True)
        if "day_of_week" in df_filtered.columns:
            st.subheader("📅 Incidentes por Dia da Semana")
            order      = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            dow_counts = df_filtered["day_of_week"].value_counts().reindex(order).dropna().reset_index()
            dow_counts.columns = ["day_of_week", "count"]
            fig_dow = px.bar(
                dow_counts, x="day_of_week", y="count",
                labels={"day_of_week": "Dia", "count": "Qtd"},
                color="count", color_continuous_scale="Blues"
            )
            st.plotly_chart(fig_dow, use_container_width=True)
    else:
        st.info("Sem dados para gerar gráficos.")

# --- ABA 5: Dados Detalhados ---
with tab_dados:
    st.subheader("Registros Filtrados")
    if not df_filtered.empty:
        df_display = df_filtered.copy()
        if "lat" in df_display.columns and "lon" in df_display.columns:
            df_display["Google Maps"] = df_display.apply(
                lambda x: "https://www.google.com/maps?q=" + str(x.get("lat", 0)) + "," + str(x.get("lon", 0)),
                axis=1
            )
        cols_show = [c for c in ["timestamp", "type", "subtype", "street", "Google Maps"] if c in df_display.columns]
        st.dataframe(
            df_display[cols_show].sort_values("timestamp", ascending=False),
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
        csv = df_display[cols_show].to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Baixar CSV", csv, "alertas_foz.csv", "text/csv")
    else:
        st.info("Nenhum registro com os filtros aplicados.")

# =============================================
# 23. RODAPÉ
# =============================================
st.markdown("---")
st.info("💡 Passe o mouse sobre os mapas para ver coordenadas em tempo real no canto superior direito.")
st.caption(
    "Fonte: Google Drive | "
    "Hora Foz: " + hora_foz_atual.strftime("%H:%M") + " (UTC-3) | "
    "Atualizações manuais: " + str(st.session_state.manual_refreshes) + " | "
    "App online há " + str(tempo_total // 60) + " min"
)
