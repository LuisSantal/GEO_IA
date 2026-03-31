import streamlit as st
import pandas as pd
import plotly.express as px
import io
import re
import tempfile
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

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

# --- FUNÇÕES DE CONEXÃO E DADOS ---

@st.cache_resource
def get_drive_service():
    """Autentica na Service Account usando os Secrets do Streamlit."""
    creds_info = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(creds_info)
    return build('drive', 'v3', credentials=creds)

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
    selected_date = st.sidebar.date_input("Selecionar Data", value=max_date, min_value=min_date, max_value=max_date)
    
    # Atualizar título com a data selecionada
    st.title(f"🚗 Monitoramento de Tráfego - Foz do Iguaçu - {selected_date.strftime('%d/%m/%Y')}")
    st.markdown("Dados extraídos em tempo real do Waze via Google Drive.")

    # Sidebar - Filtros Dinâmicos
    filtro_tipo = st.sidebar.multiselect("Filtrar por Tipo", options=df_alerts['type'].unique() if df_alerts is not None else [])
    filtro_rua = st.sidebar.text_input("Buscar Rua", placeholder="Ex: Avenida Brasil")

    # CARREGAR DADOS PARA A DATA SELECIONADA DE AMBOS TIPOS
    df_filtered = pd.DataFrame()
    df_jams_filtered = pd.DataFrame()
    
    if df_alerts is not None:
        # Filtrar alerts pela data selecionada
        df_alerts_date = df_alerts[df_alerts['timestamp'].dt.date == selected_date].copy()
        if not df_alerts_date.empty:
            # Aplicar filtros de tipo e rua
            if filtro_tipo:
                df_alerts_date = df_alerts_date[df_alerts_date['type'].isin(filtro_tipo)]
            if filtro_rua:
                df_alerts_date = df_alerts_date[df_alerts_date['street'].str.contains(filtro_rua, case=False, na=False)]
            df_filtered = df_alerts_date
    
    if df_jams is not None:
        # Filtrar jams pela data selecionada
        df_jams_filtered = df_jams[df_jams['timestamp'].dt.date == selected_date].copy()

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
        st.subheader("Mapa de Incidentes")
        
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
            
            # Criar dados customizados para o hover ANTES de criar o gráfico
            hover_data = []
            for idx, row in df_filtered.iterrows():
                maps_link = create_google_maps_link(row['lat'], row['lon'])
                coords = f"{row['lat']:.6f}, {row['lon']:.6f}"
                hover_data.append(f"<b>{row['subtype']}</b><br>Coordenadas: {coords}<br><a href='{maps_link}' target='_blank' style='color: blue; text-decoration: underline;'>Ver no Google Maps</a>")
            
            # Adicionar coluna de customdata ao dataframe
            df_filtered = df_filtered.copy()
            df_filtered['custom_hover'] = hover_data
            
            # Criar gráfico Mapbox com customdata
            fig_map = px.scatter_map(df_filtered, lat='lat', lon='lon', color='type', 
                                       hover_name='subtype', zoom=12, height=600,
                                       custom_data=['custom_hover'])
            fig_map.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0})
            
            # Atualizar traces com hovertemplate correto
            fig_map.update_traces(
                hovertemplate="%{customdata[0]}<extra></extra>"
            )
            
            st.plotly_chart(fig_map, width='stretch')

    # --- MAPA DE CONGESTIONAMENTOS ---
    if not df_jams_filtered.empty:
        st.subheader("Mapa de Congestionamentos - Largura dos Atascos")

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

            # Criar mapa de congestionamentos
            fig_jams = px.scatter_map(
                df_jams_valid,
                lat='lat',
                lon='lon',
                color='severidade_label',
                size='length' if 'length' in df_jams_valid.columns else None,
                hover_name='street' if 'street' in df_jams_valid.columns else 'Congestionamento',
                zoom=12,
                height=400,
                color_discrete_map={
                    '🔴 Crítico': 'red',
                    '🟠 Alto': 'orange',
                    '🟡 Moderado': 'yellow'
                }
            )

            # Personalizar hover para mostrar informações do congestionamento
            hover_template = "<b>%{hovertext}</b><br>"
            if 'speed' in df_jams_valid.columns:
                hover_template += "Velocidade: %{customdata[0]:.1f} km/h<br>"
            if 'length' in df_jams_valid.columns:
                hover_template += "Comprimento: %{customdata[1]:.0f} metros<br>"
            hover_template += "Severidade: %{customdata[2]}<extra></extra>"

            customdata = []
            for _, row in df_jams_valid.iterrows():
                speed_val = row.get('speed', 0) * 3.6 if row.get('speed', 0) < 50 else row.get('speed', 0)
                length_val = row.get('length', 0)
                sev_val = row['severidade_label']
                customdata.append([speed_val, length_val, sev_val])

            fig_jams.update_traces(
                hovertemplate=hover_template,
                customdata=customdata
            )

            fig_jams.update_layout(
                mapbox_style="open-street-map",
                margin={"r":0,"t":0,"l":0,"b":0},
                showlegend=True,
                legend_title="Severidade do Congestionamento"
            )

            st.plotly_chart(fig_jams, width='stretch')

            # Estatísticas dos congestionamentos
            col_stats1, col_stats2, col_stats3 = st.columns(3)
            with col_stats1:
                total_jams = len(df_jams_valid)
                st.metric("Total de Congestionamentos", total_jams)

            with col_stats2:
                avg_speed = (df_jams_valid['speed'] * 3.6 if df_jams_valid['speed'].mean() < 50 else df_jams_valid['speed']).mean()
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
