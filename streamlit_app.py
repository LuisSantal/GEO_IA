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
    st.session_state.use_mock_data = False  # tenta Drive real primeiro

tempo_sessao = (datetime.now() - st.session_state.app_start_time).total_seconds()
tempo_prox_refresh = 600 - (tempo_sessao % 600)
minutos_restantes = int(tempo_prox_refresh // 60)
segundos_restantes = int(tempo_prox_refresh % 60)
tempo_total = int(tempo_sessao)

# =============================================
# 3. IDs DAS PASTAS DO GOOGLE DRIVE
# =============================================
# Cole os IDs reais das suas pastas abaixo:
FOLDER_ALERTS_ID = "1xKkqLEusWuNoGzy5-UYuevUbMHAvc-bL"  # pasta alerts
FOLDER_JAMS_ID   = "192MCefe9vQwYhQcu-uZXekMbgdslTcgC"  # pasta jams

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
        'ACIDENTE': '#FF0000', 'VIA FECHADA': '#FF4400',
        'CONGESTIONAMENTO': '#FFAA00', 'PERIGO': '#FF6600',
        'ALERTA': '#FFDD00', 'OBRAS': '#AAAAAA',
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
      ...
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
    except Exception as e:
        st.session_state.use_mock_data = True
        return None

def get_latest_h5_id(folder_id, file_prefix=""):
    """
    Encontra o arquivo .h5 mais recente na pasta do Drive,
    baseando-se no timestamp numérico embutido no nome do arquivo.
    Ex: alerts1774879588.h5 → timestamp 1774879588
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

        latest_id = None
        latest_ts = -1
        for f in files:
            # Tenta extrair timestamp numérico do nome (ex: alerts1774879588.h5)
            match = re.search(r'(\d{8,})', f['name'])
            if match:
                ts = int(match.group(1))
                if ts > latest_ts:
                    latest_ts = ts
                    latest_id = f['id']
        
        # Fallback: usa o primeiro arquivo (já ordenado por modifiedTime desc)
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
            status, done = downloader.next_chunk()
        fh.seek(0)

        # Salva em arquivo temporário (pandas lê HDF5 melhor via path)
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
    Converte pubMillis (epoch ms UTC) para horário local de Foz do Iguaçu.
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
    Extrai lat/lon de diferentes formatos possíveis nos dados do Waze:
    - Coluna 'location' como dict {'x': lon, 'y': lat}
    - Coluna 'location' como string "{'x': ..., 'y': ...}"
    - Colunas separadas 'x' e 'y'
    - Colunas 'lat' e 'lon' já existentes
    """
    if df is None or df.empty:
        return df
    df = df.copy()

    if 'lat' in df.columns and 'lon' in df.columns:
        return df  # já processado

    if 'location' in df.columns:
        try:
            # Se for string, tenta converter para dict
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

    # Fallback: colunas 'x' e 'y'
    if 'lat' not in df.columns and 'y' in df.columns:
        df['lat'] = pd.to_numeric(df['y'], errors='coerce')
    if 'lon' not in df.columns and 'x' in df.columns:
        df['lon'] = pd.to_numeric(df['x'], errors='coerce')

    return df

# =============================================
# 8. TRADUÇÃO DE TIPOS E SUBTIPOS (WAZE → PT-BR)
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
    """Traduz colunas type e subtype de inglês para português."""
    if df is None or df.empty:
        return df
    df = df.copy()
    if 'type' in df.columns:
        df['type'] = df['type'].replace(TYPE_MAP)
    if 'subtype' in df.columns:
        df['subtype'] = df['subtype'].replace(SUBTYPE_MAP)
    return df

# =============================================
# 9. DADOS MOCKADOS (FALLBACK)
# =============================================
def create_mock_data():
    """Dados mockados realistas de Foz do Iguaçu para demonstração."""
    foz_streets = [
        ("Av. Brasil",          -25.5475, -54.5870),
        ("Av. JK",              -25.5502, -54.5851),
        ("Av. das Cataratas",   -25.5531, -54.5792),
        ("Av. Paraná",          -25.5458, -54.5901),
