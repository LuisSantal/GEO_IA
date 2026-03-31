import streamlit as st
import pandas as pd
import plotly.express as px
import io
import re
import tempfile
import json
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import folium
from streamlit_folium import st_folium
import colorsys

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Waze Foz do Iguaçu", layout="wide")

# --- CONFIGURAÇÃO DE AUTO-REFRESH A CADA 10 MINUTOS ---
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.now()

# Verificar se passou 10 minutos desde o último refresh
tempo_desde_refresh = datetime.now() - st.session_state.last_refresh
if tempo_desde_refresh.total_seconds() >= 600:  # 600 segundos = 10 minutos
    st.session_state.last_refresh = datetime.now()
    st.cache_data.clear()  # Limpar cache para forçar recarregamento dos dados
    st.rerun()

# Exibir indicador de quando foi o último refresh
minutos_restantes = 10 - int(tempo_desde_refresh.total_seconds() // 60)
segundos_restantes = int(tempo_desde_refresh.total_seconds() % 60)
st.sidebar.markdown(f"""
**⏰ Próximo Refresh**  
Em {minutos_restantes}:{segundos_restantes:02d} minutos  
Último: {st.session_state.last_refresh.strftime('%H:%M:%S')}
""")

# --- CONSTANTES ---
# Substitua pelos IDs reais das suas pastas no Google Drive
FOLDER_ALERTS_ID = "https://drive.google.com/drive/folders/1xKkqLEusWuNoGzy5-UYuevUbMHAvc-bL"
FOLDER_JAMS_ID = "https://drive.google.com/drive/folders/192MCefe9vQwYhQcu-uZXekMbgdslTcgC"

def extract_folder_id(folder_url):
    """Extrai o ID da pasta do URL completo do Google Drive."""
    import re
    match = re.search(r'/folders/([a-zA-Z0-9_-]+)', folder_url)
    if match:
        return match.group(1)
    return folder_url  # Retorna como está se não for URL

# --- FUNÇÕES DE PALETA DE CORES ---

def get_color_from_gradient(value, min_val=0, max_val=100, reverse=False):
    """
    Gera cor na paleta Verde → Amarelo → Vermelho baseado em valor percentual.
    
    Args:
        value: Valor entre min_val e max_val
        min_val: Valor mínimo (verde)
        max_val: Valor máximo (vermelho)
        reverse: Se True, inverte a escala (verde = perigoso)
    
    Returns:
        Código de cor em hexadecimal (#RRGGBB)
    """
    # Normalizar valor entre 0 e 1
    if max_val == min_val:
        normalized = 0.5
    else:
        normalized = (value - min_val) / (max_val - min_val)
    
    normalized = max(0, min(1, normalized))  # Limitar entre 0 e 1
    
    if reverse:
        normalized = 1 - normalized
    
    # Criar gradiente verde → amarelo → vermelho
    if normalized < 0.5:
        # Verde → Amarelo
        r = int(255 * (normalized * 2))
        g = 255
        b = 0
    else:
        # Amarelo → Vermelho
        r = 255
        g = int(255 * (2 - normalized * 2))
        b = 0
    
    return f'#{r:02x}{g:02x}{b:02x}'

def get_congestion_color(speed_kmh):
    """
    Retorna cor baseada na velocidade de congestionamento.
    Verde (livre) → Vermelho (trânsito parado)
    """
    # Escala: 0 km/h = Vermelho (parado), 80+ km/h = Verde (livre)
    if speed_kmh >= 80:
        return '#00AA00'  # Verde
    elif speed_kmh >= 60:
        return '#55DD00'  # Verde-amarelo
    elif speed_kmh >= 40:
        return '#DDDD00'  # Amarelo
    elif speed_kmh >= 20:
        return '#FF8800'  # Laranja
    else:
        return '#FF0000'  # Vermelho

def get_danger_color(incident_type):
    """
    Retorna cor baseada no tipo de incidente (perigo).
    """
    danger_colors = {
        'ACIDENTE': '#FF0000',        # Vermelho - Mais perigoso
        'VIA FECHADA': '#FF4400',      # Vermelho-laranja
        'CONGESTIONAMENTO': '#FFAA00',  # Laranja
        'PERIGO': '#FF6600',            # Laranja-vermelho
        'ALERTA': '#FFDD00',            # Amarelo
        'OBRAS': '#AAAAAA',             # Cinza
    }
    return danger_colors.get(str(incident_type).upper(), '#0099FF')  # Azul padrão

def create_folium_map_with_compass(lat, lon, zoom_level=12, title="Mapa"):
    """
    Cria um mapa Folium com:
    - Controle de zoom (escala)
    - Seta do norte (compass)
    - Zoom inicial configurável
    
    Args:
        lat: Latitude central
        lon: Longitude central
        zoom_level: Nível de zoom inicial
        title: Título do mapa
    
    Returns:
        Objeto folium.Map configurado
    """
    m = folium.Map(
        location=[lat, lon],
        zoom_start=zoom_level,
        tiles="OpenStreetMap",
        max_bounds=True
    )
    
    # Adicionar controles
    # 1. Zoom control (padrão já vem, mas explícito)
    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    
    # 2. Nord Arrow (Bússola/Seta do Norte)
    # Criar HTML para a seta do norte
    north_html = '''
    <div style="position: fixed; 
        top: 50px; right: 50px; width: 70px; height: 70px; 
        background-color: white; border:2px solid grey; z-index:9999; 
        display: flex; align-items: center; justify-content: center;
        border-radius: 5px;">
        <div style="font-size: 40px; color: red;">↑</div>
    </div>
    <div style="position: fixed; 
        top: 65px; right: 50px; width: 700px; height: 40px;
        text-align: center; z-index:9999; font-weight: bold; color: #333;">
        <small>N</small>
    </div>
    '''
    
    m.get_root().html.add_child(folium.Element(north_html))
    
    # 3. Adicionar escala (zoom scale)
    folium.ScaleControl(position='bottomleft', metric=True, imperial=False).add_to(m)
    
    return m

# --- FUNÇÕES DE CONEXÃO E DADOS ---

@st.cache_resource
def get_drive_service():
    """Autentica na Service Account usando os Secrets do Streamlit."""
    try:
        creds_info = st.secrets["gcp_service_account"]
        
        # Se for string JSON, fazer o parsing com tratamento melhorado
        if isinstance(creds_info, str):
            try:
                creds_info = json.loads(creds_info)
            except json.JSONDecodeError as e:
                st.error(f"❌ Erro ao fazer parse do JSON das credenciais: {str(e)}")
                st.error("**Solução:** Gere JSON minificado com o comando no terminal")
                st.error("**No Streamlit Cloud:** Cole entre aspas triplas no campo Secrets")
                st.code("""
gcp_service_account = \"\"\"
[COLE AQUI O JSON MINIFICADO]
\"\"\"
""")
                st.stop()
        
        # Validar que é um dicionário
        if not isinstance(creds_info, dict):
            st.error("❌ Credenciais GCP não estão em formato de dicionário")
            st.stop()
        
        creds = service_account.Credentials.from_service_account_info(creds_info)
        return build('drive', 'v3', credentials=creds)
    except KeyError:
        st.error("❌ Secret 'gcp_service_account' não encontrada!")
        st.error("Adicione as credenciais GCP em Settings → Secrets da sua app no Streamlit Cloud")
        st.stop()
    except Exception as e:
        st.error(f"❌ Erro ao autenticar com GCP: {str(e)}")
        st.stop()

def get_all_h5_files(folder_id):
    """Encontra todos os arquivos .h5 na pasta ordenados por timestamp."""
    service = get_drive_service()
    folder_id = extract_folder_id(folder_id)
    query = f"'{folder_id}' in parents and name contains '.h5'"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    
    # Ordenar por timestamp no nome do arquivo
    file_list = []
    for f in files:
        match = re.search(r'(\d+)\.h5', f['name'])
        if match:
            ts = int(match.group(1))
            file_list.append((ts, f['id'], f['name']))
    
    # Ordenar do mais recente para o mais antigo
    file_list.sort(reverse=True)
    return file_list

def load_historical_data(folder_id, selected_date=None):
    """Carrega dados históricos baseados na data selecionada."""
    file_list = get_all_h5_files(folder_id)
    
    if not file_list:
        return None
    
    # Se não há data selecionada, carrega o mais recente
    if selected_date is None:
        return load_hdf_from_drive(file_list[0][1])
    
    # Procurar arquivo que contenha dados da data selecionada
    # Como os arquivos têm timestamp, vamos carregar arquivos recentes
    # e filtrar por data dentro deles
    all_data = []
    for _, file_id, _ in file_list[:5]:  # Carregar os 5 mais recentes
        try:
            df = load_hdf_from_drive(file_id)
            if df is not None:
                df['timestamp'] = pd.to_datetime(df['pubMillis'] / 1000, unit='s')
                all_data.append(df)
        except:
            continue
    
    if not all_data:
        return None
    
    # Combinar todos os dados
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Remover duplicatas baseadas em pubMillis E location para evitar coordenadas conflitantes
    if 'location' in combined_df.columns:
        # Criar uma coluna temporária com coordenadas extraídas para deduplicação
        combined_df['temp_coords'] = combined_df['location'].apply(
            lambda x: f"{eval(x)['y']:.6f}_{eval(x)['x']:.6f}" if isinstance(x, str) else f"{x['y']:.6f}_{x['x']:.6f}"
        )
        combined_df = combined_df.drop_duplicates(subset=['pubMillis', 'temp_coords'])
        combined_df = combined_df.drop('temp_coords', axis=1)
    else:
        # Fallback para deduplicação apenas por pubMillis
        combined_df = combined_df.drop_duplicates(subset=['pubMillis'])
    
    return combined_df

def load_hdf_from_drive(file_id):
    """Baixa o arquivo do Drive e carrega no Pandas."""
    if not file_id: return None
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

def create_google_maps_link(lat, lon):
    """Cria um link do Google Maps para as coordenadas especificadas."""
    return f"https://www.google.com/maps?q={lat},{lon}"

# --- LÓGICA DO DASHBOARD ---

st.title("🚗 Monitoramento de Tráfego - Foz do Iguaçu")
st.markdown("Dados extraídos em tempo real do Waze via Google Drive.")

# Sidebar de Filtros [cite: 63-91]
st.sidebar.header("Filtros e Configurações")
if st.sidebar.button("Atualizar Dados"):
    st.cache_data.clear()

# 1. Carregar Alertas (dados históricos)
df_alerts = load_historical_data(FOLDER_ALERTS_ID)
if df_alerts is not None:
    
    # Processamento de Dados [cite: 258, 982]
    df_alerts['timestamp'] = pd.to_datetime(df_alerts['pubMillis'] / 1000, unit='s')
    df_alerts['hour'] = df_alerts['timestamp'].dt.hour
    df_alerts['day_of_week'] = df_alerts['timestamp'].dt.day_name()
    
    # Traduções [cite: 308-312, 1012-1016]
    type_map = {
        'ROAD_CLOSED': 'VIA FECHADA',
        'HAZARD': 'PERIGO',
        'ACCIDENT': 'ACIDENTE',
        'JAM': 'CONGESTIONAMENTO',
        'WEATHERHAZARD': 'PERIGO CLIMÁTICO'
    }
    df_alerts['type'] = df_alerts['type'].replace(type_map)
    
    # Traduções para subtipos - mapa mais completo
    subtype_map = {
        'ROAD_CLOSED_CONSTRUCTION': 'OBRAS',
        'ROAD_CLOSED_EVENT': 'EVENTO',
        'HAZARD_ON_ROAD': 'PERIGO NA VIA',
        'HAZARD_ON_SHOULDER': 'PERIGO NO ACOSTAMENTO',
        'HAZARD_WEATHER': 'CONDIÇÕES CLIMÁTICAS',
        'HAZARD_ON_ROAD_POT_HOLE': 'BURACO NA VIA',
        'HAZARD_ON_ROAD_ROAD_KILL': 'ANIMAL NA VIA',
        'HAZARD_ON_ROAD_CAR_STOPPED': 'VEÍCULO PARADO',
        'HAZARD_ON_ROAD_CONSTRUCTION': 'OBRAS NA VIA',
        'HAZARD_ON_ROAD_OBJECT': 'OBJETO NA VIA',
        'HAZARD_ON_ROAD_TRAFFIC_LIGHT_FAULT': 'SEMÁFORO QUEBRADO',
        'HAZARD_WEATHER_FOG': 'NEBLINA',
        'HAZARD_WEATHER_HAIL': 'GRANIZO',
        'HAZARD_WEATHER_HEAVY_RAIN': 'CHUVA FORTE',
        'HAZARD_WEATHER_FLOOD': 'INUNDAÇÃO',
        'ACCIDENT_MAJOR': 'ACIDENTE GRAVE',
        'ACCIDENT_MINOR': 'ACIDENTE LEVE',
        'JAM_HEAVY_TRAFFIC': 'TRÂNSITO PESADO',
        'JAM_MODERATE_TRAFFIC': 'TRÂNSITO MODERADO',
        'JAM_STAND_STILL_TRAFFIC': 'TRÂNSITO PARADO'
    }
    df_alerts['subtype'] = df_alerts['subtype'].replace(subtype_map)

    # 2. Carregar Dados de Jams (para velocidade média)
    df_jams = load_historical_data(FOLDER_JAMS_ID)
    if df_jams is not None:
        df_jams['timestamp'] = pd.to_datetime(df_jams['pubMillis'] / 1000, unit='s')

    # Determinar datas disponíveis COM BASE EM TODOS OS DADOS CARREGADOS
    all_dates = set()
    if df_alerts is not None:
        all_dates.update(df_alerts['timestamp'].dt.date.unique())
    if df_jams is not None:
        all_dates.update(df_jams['timestamp'].dt.date.unique())
    
    if all_dates:
        min_date = min(all_dates)
        max_date = max(all_dates)
    else:
        # Fallback para hoje se não houver dados
        from datetime import date
        min_date = max_date = date.today()
    
    # Selector de Data
    selected_date = st.sidebar.date_input("📅 Selecionar Data", value=max_date, min_value=min_date, max_value=max_date)
    
    # Atualizar título com a data selecionada
    st.title(f"🚗 Monitoramento de Tráfego - Foz do Iguaçu - {selected_date.strftime('%d/%m/%Y')}")
    st.markdown("Dados extraídos em tempo real do Waze via Google Drive.")

    # Sidebar - Filtros Dinâmicos
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Filtros Avançados")
    
    # 1. Filtro por Tipo de Alerta
    tipos_disponiveis = sorted(df_alerts['type'].unique().tolist()) if df_alerts is not None else []
    filtro_tipo = st.sidebar.multiselect(
        "🚨 Tipo de Alerta",
        options=tipos_disponiveis,
        default=tipos_disponiveis,
        help="Selecione os tipos de alerta que deseja visualizar"
    )
    
    # 2. Filtro por Rua
    filtro_rua = st.sidebar.text_input(
        "🛣️ Buscar Rua",
        placeholder="Ex: Avenida Brasil",
        help="Digite parte do nome da rua para filtrar"
    )
    
    # 3. Filtro por Horário (range de horas)
    st.sidebar.markdown("**⏰ Horário**")
    col_hora_from, col_hora_to = st.sidebar.columns(2)
    with col_hora_from:
        hora_inicio = st.number_input("De:", min_value=0, max_value=23, value=0, step=1, label_visibility="collapsed")
    with col_hora_to:
        hora_fim = st.number_input("Até:", min_value=0, max_value=23, value=23, step=1, label_visibility="collapsed")
    
    # Garantir que hora_inicio <= hora_fim
    if hora_inicio > hora_fim:
        hora_inicio, hora_fim = hora_fim, hora_inicio

    # CARREGAR DADOS PARA A DATA SELECIONADA DE AMBOS TIPOS
    df_filtered = pd.DataFrame()
    df_jams_filtered = pd.DataFrame()
    
    if df_alerts is not None:
        # Filtrar alerts pela data selecionada
        df_alerts_date = df_alerts[df_alerts['timestamp'].dt.date == selected_date].copy()
        if not df_alerts_date.empty:
            # Aplicar filtros
            # 1. Filtro de Tipo de Alerta
            if filtro_tipo:
                df_alerts_date = df_alerts_date[df_alerts_date['type'].isin(filtro_tipo)]
            
            # 2. Filtro de Rua
            if filtro_rua:
                df_alerts_date = df_alerts_date[df_alerts_date['street'].str.contains(filtro_rua, case=False, na=False)]
            
            # 3. Filtro de Horário
            df_alerts_date = df_alerts_date[
                (df_alerts_date['hour'] >= hora_inicio) & 
                (df_alerts_date['hour'] <= hora_fim)
            ]
            
            df_filtered = df_alerts_date
    
    if df_jams is not None:
        # Filtrar jams pela data selecionada
        df_jams_filtered = df_jams[df_jams['timestamp'].dt.date == selected_date].copy()
        # Aplicar filtro de horário também em jams
        df_jams_filtered = df_jams_filtered[
            (df_jams_filtered['timestamp'].dt.hour >= hora_inicio) & 
            (df_jams_filtered['timestamp'].dt.hour <= hora_fim)
        ]

    # --- RESUMO DOS FILTROS APLICADOS ---
    st.markdown("---")
    col_filtros = st.columns([1, 1, 1, 1])
    
    with col_filtros[0]:
        st.metric("📅 Data", selected_date.strftime("%d/%m/%Y"))
    
    with col_filtros[1]:
        if filtro_tipo:
            st.metric("🚨 Alertas", f"{len(filtro_tipo)}")
        else:
            st.metric("🚨 Alertas", "Todos")
    
    with col_filtros[2]:
        if filtro_rua:
            st.metric("🛣️ Rua", f"'{filtro_rua}'")
        else:
            st.metric("🛣️ Rua", "Todas")
    
    with col_filtros[3]:
        st.metric("⏰ Horário", f"{hora_inicio:02d}:00 - {hora_fim:02d}:59")
    
    st.markdown("---")

    # --- INDICADORES DE GRAVIDADE E TEMPERATURA ---
    st.subheader("📊 Indicadores de Gravidade")

    # Calcular gravidade baseada nos incidentes do dia (apenas alerts)
    incidentes_dia = len(df_filtered) if not df_filtered.empty else 0
    acidentes_graves = len(df_filtered[df_filtered['type'] == 'ACIDENTE']) if not df_filtered.empty else 0
    vias_fechadas = len(df_filtered[df_filtered['type'] == 'VIA FECHADA']) if not df_filtered.empty else 0

    # Lógica de gravidade: mais incidentes = mais grave
    if incidentes_dia == 0:
        gravidade = 0
        cor_gravidade = 'green'
        status_gravidade = "✅ Situação Normal"
    elif incidentes_dia < 5:
        gravidade = 25
        cor_gravidade = 'yellow'
        status_gravidade = "⚠️ Atenção Moderada"
    elif incidentes_dia < 15:
        gravidade = 50
        cor_gravidade = 'orange'
        status_gravidade = "🚨 Alerta Elevado"
    else:
        gravidade = 75
        cor_gravidade = 'red'
        status_gravidade = "🚫 Situação Crítica"

    # Calcular velocidade média
    velocidade_media = 0
    if not df_jams_filtered.empty and 'speed' in df_jams_filtered.columns:
        velocidade_media = df_jams_filtered['speed'].mean()
        # Converter de m/s para km/h se necessário
        if velocidade_media < 50:  # Assume que está em m/s se for menor que 50
            velocidade_media = velocidade_media * 3.6

    # Temperatura simulada (substitua por API real se disponível)
    temperatura_atual = 25.5  # Simulado - em graus Celsius

    # Layout dos indicadores
    col_grav, col_vel, col_temp = st.columns(3)

    with col_grav:
        # Indicador de Gravidade dos Incidentes
        fig_grav = px.bar_polar(
            r=[gravidade],
            theta=[0],
            range_r=[0, 100],
            color_discrete_sequence=[cor_gravidade]
        )
        fig_grav.update_layout(
            title=f"🚨 Gravidade: {incidentes_dia} incidentes",
            polar=dict(
                radialaxis=dict(range=[0, 100], showticklabels=False),
                angularaxis=dict(showticklabels=False)
            ),
            showlegend=False,
            height=200
        )
        st.plotly_chart(fig_grav, width='stretch')
        st.markdown(f"**{status_gravidade}**")
        if acidentes_graves > 0:
            st.warning(f"🚑 {acidentes_graves} acidente(s) grave(s)")
        if vias_fechadas > 0:
            st.error(f"🚧 {vias_fechadas} via(s) fechada(s)")

    with col_vel:
        # Indicador de Velocidade Média
        fig_vel = px.bar_polar(
            r=[velocidade_media],
            theta=[0],
            range_r=[0, 80],
            color_discrete_sequence=['green' if velocidade_media > 40 else 'yellow' if velocidade_media > 20 else 'red']
        )
        fig_vel.update_layout(
            title=f"🚗 Velocidade Média: {velocidade_media:.1f} km/h",
            polar=dict(
                radialaxis=dict(range=[0, 80], showticklabels=False),
                angularaxis=dict(showticklabels=False)
            ),
            showlegend=False,
            height=200
        )
        st.plotly_chart(fig_vel, width='stretch')

        # Status da velocidade
        if velocidade_media > 40:
            st.success("✅ Tráfego Fluindo Bem")
        elif velocidade_media > 20:
            st.warning("⚠️ Tráfego Moderado")
        else:
            st.error("🚫 Tráfego Congestionado")

    with col_temp:
        # Indicador de Temperatura
        fig_temp = px.bar_polar(
            r=[temperatura_atual],
            theta=[0],
            range_r=[0, 45],
            color_discrete_sequence=['blue' if temperatura_atual < 15 else 'green' if temperatura_atual < 25 else 'orange' if temperatura_atual < 35 else 'red']
        )
        fig_temp.update_layout(
            title=f"🌡️ Temperatura: {temperatura_atual:.1f}°C",
            polar=dict(
                radialaxis=dict(range=[0, 45], showticklabels=False),
                angularaxis=dict(showticklabels=False)
            ),
            showlegend=False,
            height=200
        )
        st.plotly_chart(fig_temp, width='stretch')

        # Status da temperatura
        if temperatura_atual < 15:
            st.info("❄️ Frio")
        elif temperatura_atual < 25:
            st.success("🌤️ Agradável")
        elif temperatura_atual < 35:
            st.warning("☀️ Quente")
        else:
            st.error("🔥 Muito Quente")

    # Layout Principal - Colunas
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🗺️ Mapa de Incidentes - Nível de Perigo")
        
        if df_filtered.empty:
            st.info(f"📅 Nenhum incidente registrado para {selected_date.strftime('%d/%m/%Y')}, mas há dados de congestionamento disponíveis.")
        else:
            # Processar coordenadas ANTES de criar o gráfico
            if 'location' in df_filtered.columns:
                # Expande a string do dict para colunas reais se necessário
                df_filtered = df_filtered.copy()  # Criar cópia para evitar warnings
                df_filtered['lat'] = df_filtered['location'].apply(lambda x: eval(x)['y'] if isinstance(x, str) else x['y'])
                df_filtered['lon'] = df_filtered['location'].apply(lambda x: eval(x)['x'] if isinstance(x, str) else x['x'])
            
            # Remover duplicatas baseadas em coordenadas e timestamp para evitar pontos repetidos
            df_filtered = df_filtered.drop_duplicates(subset=['lat', 'lon', 'pubMillis'])
            
            # Calcular centro do mapa
            center_lat = df_filtered['lat'].mean()
            center_lon = df_filtered['lon'].mean()
            
            # Criar mapa Folium com compass e zoom
            m = create_folium_map_with_compass(center_lat, center_lon, zoom_level=12)
            
            # Adicionar marcadores com cores dinâmicas baseadas em tipo de incidente
            for idx, row in df_filtered.iterrows():
                maps_link = create_google_maps_link(row['lat'], row['lon'])
                color = get_danger_color(row['type'])
                
                # Determinar ícone baseado no tipo
                icon_type = 'exclamation-triangle' if row['type'] == 'ACIDENTE' else 'info-sign'
                
                folium.CircleMarker(
                    location=[row['lat'], row['lon']],
                    radius=8,
                    popup=f"""
                    <div style='font-size: 12px; width: 250px;'>
                        <b>{row['subtype']}</b><br>
                        <b>Tipo:</b> {row['type']}<br>
                        <b>Rua:</b> {row.get('street', 'N/A')}<br>
                        <b>Hora:</b> {row['timestamp'].strftime('%H:%M:%S') if hasattr(row['timestamp'], 'strftime') else row['timestamp']}<br>
                        <a href='{maps_link}' target='_blank' style='color: blue; text-decoration: underline;'>Ver no Google Maps</a>
                    </div>
                    """,
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.7,
                    weight=2,
                    tooltip=f"{row['subtype']} - {row['type']}"
                ).add_to(m)
            
            # Exibir mapa
            st_folium(m, width=700, height=600)

    # --- MAPA DE CONGESTIONAMENTOS ---
    if not df_jams_filtered.empty:
        st.subheader("🗺️ Mapa de Congestionamentos - Paleta Verde (Livre) → Vermelho (Parado)")

        # Processar coordenadas dos jams
        if 'line' in df_jams_filtered.columns:
            # Expandir coordenadas da linha do congestionamento
            df_jams_filtered['lat'] = df_jams_filtered['line'].apply(lambda x: eval(x)[0]['y'] if isinstance(x, str) and eval(x) else None)
            df_jams_filtered['lon'] = df_jams_filtered['line'].apply(lambda x: eval(x)[0]['x'] if isinstance(x, str) and eval(x) else None)

        # Filtrar apenas jams com coordenadas válidas
        df_jams_valid = df_jams_filtered.dropna(subset=['lat', 'lon'])

        if not df_jams_valid.empty:
            # Calcular severidade baseada na velocidade e comprimento
            df_jams_valid['severidade'] = 'Moderado'
            if 'speed' in df_jams_valid.columns:
                df_jams_valid.loc[df_jams_valid['speed'] < 10, 'severidade'] = 'Crítico'
                df_jams_valid.loc[(df_jams_valid['speed'] >= 10) & (df_jams_valid['speed'] < 20), 'severidade'] = 'Alto'
                df_jams_valid.loc[df_jams_valid['speed'] >= 20, 'severidade'] = 'Moderado'

            # Traduzir severidade
            severidade_map = {
                'Crítico': '🔴 Crítico',
                'Alto': '🟠 Alto',
                'Moderado': '🟡 Moderado'
            }
            df_jams_valid['severidade_label'] = df_jams_valid['severidade'].map(severidade_map)
            
            # Converter velocidade para km/h se necessário
            df_jams_valid['speed_kmh'] = df_jams_valid['speed'].apply(
                lambda x: (x * 3.6) if x < 50 else x
            )
            
            # Calcular centro do mapa
            center_lat = df_jams_valid['lat'].mean()
            center_lon = df_jams_valid['lon'].mean()
            
            # Criar mapa Folium com compass e zoom
            m_jams = create_folium_map_with_compass(center_lat, center_lon, zoom_level=12)
            
            # Adicionar marcadores com cores dinâmicas baseadas em velocidade
            for idx, row in df_jams_valid.iterrows():
                color = get_congestion_color(row.get('speed_kmh', 0))
                
                # Tamanho do círculo baseado no comprimento
                size = min(10, max(3, row.get('length', 100) / 100)) if 'length' in row else 5
                
                folium.CircleMarker(
                    location=[row['lat'], row['lon']],
                    radius=size,
                    popup=f"""
                    <div style='font-size: 12px; width: 250px;'>
                        <b>{row.get('street', 'Congestionamento')}</b><br>
                        <b>Velocidade:</b> {row.get('speed_kmh', 0):.1f} km/h<br>
                        <b>Comprimento:</b> {row.get('length', 0):.0f} metros<br>
                        <b>Severidade:</b> {row['severidade_label']}<br>
                        <b>Hora:</b> {row.get('timestamp', 'N/A').strftime('%H:%M:%S') if hasattr(row.get('timestamp', 'N/A'), 'strftime') else str(row.get('timestamp', 'N/A'))}
                    </div>
                    """,
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.6,
                    weight=2,
                    tooltip=f"Velocidade: {row.get('speed_kmh', 0):.1f} km/h"
                ).add_to(m_jams)
            
            # Exibir mapa
            st_folium(m_jams, width=700, height=500)
            
            # Legenda de cores
            st.markdown("""
            **Legenda de Cores:**
            - 🟢 **Verde**: Livre (≥80 km/h)
            - 🟡 **Amarelo-verde**: Boa fluidez (60-80 km/h)
            - 🟠 **Amarelo**: Fluxo moderado (40-60 km/h)
            - 🟠 **Laranja**: Fluxo reduzido (20-40 km/h)
            - 🔴 **Vermelho**: Parado/Crítico (<20 km/h)
            """)

            # Estatísticas dos congestionamentos
            col_stats1, col_stats2, col_stats3 = st.columns(3)
            with col_stats1:
                total_jams = len(df_jams_valid)
                st.metric("Total de Congestionamentos", total_jams)

            with col_stats2:
                avg_speed = df_jams_valid['speed_kmh'].mean()
                st.metric("Velocidade Média", f"{avg_speed:.1f} km/h")

            with col_stats3:
                if 'length' in df_jams_valid.columns:
                    total_length = df_jams_valid['length'].sum() / 1000  # converter para km
                    st.metric("Comprimento Total", f"{total_length:.1f} km")
                else:
                    st.metric("Comprimento Total", "N/A")
        else:
            st.info("Nenhum dado de congestionamento com coordenadas válidas para a data selecionada.")
    else:
        st.info("Nenhum dado de congestionamento encontrado para a data selecionada.")

    # --- GRÁFICOS ESTATÍSTICOS ---
    st.subheader("Estatísticas de Alertas")
    
    if df_filtered.empty:
        st.info("📊 Não há dados de incidentes para gerar estatísticas nesta data.")
    else:
        # Layout em colunas para os gráficos
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            # Gráfico por Hora 
            fig_hora = px.bar(df_filtered['hour'].value_counts().sort_index(), 
                             labels={'index': 'Hora', 'value': 'Qtd'},
                             title="Incidentes por Hora")
            st.plotly_chart(fig_hora, width='stretch')

        with col_graf2:
            # Gráfico de Subtipos 
            fig_pie = px.pie(df_filtered, names='type', title="Proporção por Categoria")
            st.plotly_chart(fig_pie, width='stretch')

        # Tabela de Detalhes
        st.subheader("Lista Detalhada de Eventos")
        # Incluir coluna 'user' se existir nos dados
        columns_to_show = ['timestamp', 'type', 'subtype', 'street']
        if 'user' in df_filtered.columns:
            columns_to_show.append('user')
        st.dataframe(df_filtered[columns_to_show].sort_values(by='timestamp', ascending=False))

else:
    st.error("Nenhum arquivo de alertas encontrado na pasta do Google Drive.")
