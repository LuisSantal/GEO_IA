# Imports from both, consolidated
import os
import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import osmnx as ox
import geopandas as gpd
from collections import defaultdict
import json
from shapely.geometry import Point, LineString
import math
import warnings
import time
import threading
import concurrent.futures
from dash.exceptions import PreventUpdate
from functools import lru_cache
from typing import List 
import ast 

# Global Configurations
warnings.filterwarnings('ignore', category=UserWarning)

external_stylesheets = [dbc.themes.BOOTSTRAP]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.title = "Traffic Dashboard - Border Region"
PROCESSED_FILE_PATH = "/home/les.alvarez.2015/Área de Trabalho/DADOS WAZE/DadosProcessados/jams_processed.parquet"

# --- LOCAL FILE PATHS (ADJUST THESE!) ---
# THESE ARE CRITICAL FOR THE APP'S FUNCTIONALITY.
DATA_DIR = "/home/les.alvarez.2015/Área de Trabalho/DADOS WAZE/Códigos/Dados/DataFeed/jams" 
BAIRROS_GPKG_PATH = "/home/les.alvarez.2015/Área de Trabalho/DADOS WAZE/Bairros Foz do Iguacu.gpkg" 

# Local cache for OSM data and output figures - created relative to the script
SCRIPT_DIR = os.path.dirname(__file__) if '__file__' in locals() else os.getcwd()
OSM_CACHE_DIR = os.path.join(SCRIPT_DIR, "osm_cache") 
os.makedirs(OSM_CACHE_DIR, exist_ok=True)

OUTPUT_DIR_FIGURAS = os.path.join(SCRIPT_DIR, "figures_output") 
os.makedirs(OUTPUT_DIR_FIGURAS, exist_ok=True)
PATHS = {
    'static_maps': os.path.join(OUTPUT_DIR_FIGURAS, 'static_maps'),
    'interactive_maps': os.path.join(OUTPUT_DIR_FIGURAS, 'interactive_maps'),
    'reports': os.path.join(OUTPUT_DIR_FIGURAS, 'reports'),
    'hotspots': os.path.join(OUTPUT_DIR_FIGURAS, 'hotspots')
}
for path_val in PATHS.values():
    os.makedirs(path_val, exist_ok=True)

CITY_BOUNDS = {
    "Foz do Iguaçu": {"min_lon": -54.62, "max_lon": -54.5, "min_lat": -25.55, "max_lat": -25.45},
    "Ciudad del Este": {"min_lon": -54.7, "max_lon": -54.6, "min_lat": -25.55, "max_lat": -25.45},
    "Puerto Iguazú": {"min_lon": -54.6, "max_lon": -54.5, "min_lat": -25.61, "max_lat": -25.55}
}

CACHE_TIMEOUT_BAIRROS = 7 * 24 * 3600 
CACHE_TIMEOUT_OSM = 30 * 24 * 3600 

# Global variables for loading status
load_lock = threading.Lock()
load_progress = 0
load_message = ""
load_running = False
loaded_data = None
failed_files = [] 

MAX_MAP_POINTS_TO_PLOT = 15000 

def classify_city(line_coords_evaluated):
    """Classifies the city based on the midpoint of the line coordinates.
    Expects line_coords_evaluated to be a list of dicts or similar structure."""
    
    if not line_coords_evaluated or not isinstance(line_coords_evaluated, list) or len(line_coords_evaluated) == 0:
        return "Unknown"
    
    if not all(isinstance(pt, dict) and 'x' in pt and 'y' in pt for pt in line_coords_evaluated):
        return "Unknown"
    
    midpoint_idx = len(line_coords_evaluated) // 2
    if midpoint_idx >= len(line_coords_evaluated): 
        midpoint_idx = len(line_coords_evaluated) - 1 if len(line_coords_evaluated) > 0 else 0 
    
    midpoint = line_coords_evaluated[midpoint_idx]
    
    lon, lat = midpoint['x'], midpoint['y']
    for city, bounds in CITY_BOUNDS.items():
        if (bounds['min_lon'] <= lon <= bounds['max_lon'] and
            bounds['min_lat'] <= lat <= bounds['max_lat']):
            return city
    return "Unknown"

def load_data_thread_combined():
    """Função executada em uma thread para carregar os dados de jams do arquivo PARQUET processado."""
    global load_progress, load_message, load_running, loaded_data, failed_files
    with load_lock:
        load_progress = 0
        load_message = "Iniciando carregamento do arquivo processado..."
        load_running = True
        failed_files = [] 
    print("THREAD: Iniciando carregamento de dados do arquivo processado...")

    if not os.path.exists(PROCESSED_FILE_PATH):
        with load_lock:
            load_message = f"Erro: Arquivo de dados processado não encontrado: {PROCESSED_FILE_PATH}. Por favor, gere-o primeiro com 'preprocess_jams.py'!"
            load_progress = 100
            load_running = False
            loaded_data = pd.DataFrame() 
        print(f"THREAD ERROR: {load_message}")
        return

    try:
        print(f"THREAD: Lendo {PROCESSED_FILE_PATH}...")
        df = pd.read_parquet(PROCESSED_FILE_PATH)
        print(f"THREAD: Leitura do Parquet completa. Registros: {len(df):,}")
        
        df['time'] = pd.to_datetime(df['time'])
        df['hour'] = df['time'].dt.hour 
        df['day_of_week'] = df['time'].dt.day_name()
        
        print("THREAD: Avaliando a coluna 'line' para geometria...")
        def safe_literal_eval_for_line(val):
            if isinstance(val, str):
                try:
                    return ast.literal_eval(val)
                except (ValueError, SyntaxError):
                    return None 
            return None 

        df['line'] = df['line'].apply(safe_literal_eval_for_line)
        
        df = df[df['line'].notna()]
        df = df[df['line'].apply(lambda x: isinstance(x, list) and len(x) > 1)]

        required_cols = ['uuid', 'time', 'line', 'speedKMH', 'city', 'delay', 'length', 'level']
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0 if col in ['delay', 'length', 'level', 'speedKMH'] else 'N/A'
                print(f"THREAD WARNING: Coluna '{col}' recriada com valor padrão na leitura do Parquet.")

        with load_lock:
            loaded_data = df
            load_message = f"Carregamento completo do arquivo processado! {len(loaded_data):,} registros."
            print(f"THREAD SUCCESS: {load_message}")
            load_progress = 100
            load_running = False
    except Exception as e:
        with load_lock:
            load_message = f"Erro crítico ao carregar arquivo processado: {str(e)}"
            loaded_data = pd.DataFrame()
            load_progress = 100
            load_running = False
        print(f"THREAD CRITICAL ERROR: {str(e)}")
    finally:
        pass


@lru_cache(maxsize=1)
def get_loaded_data():
    """Retorna os dados carregados globalmente. Não inicia o carregamento por si só."""
    global loaded_data
    if loaded_data is None:
        print("WARNING: get_loaded_data foi chamada antes que os dados fossem carregados pela thread. Retornando DataFrame vazio.")
        return pd.DataFrame()
    return loaded_data

def download_osm_city_combined(cidade, lugar, cache_dir, force_download=False):
    """Baixa ou carrega dados OSM de cache para uma cidade."""
    cache_file = os.path.join(cache_dir, f"{cidade.replace(' ', '_')}.geojson")
    print(f"OSM: Tentando carregar/baixar OSM para {cidade}...")
    if not force_download and os.path.exists(cache_file) and \
       (time.time() - os.path.getmtime(cache_file)) < CACHE_TIMEOUT_OSM:
        try:
            gdf = gpd.read_file(cache_file)
            for col in ['highway', 'maxspeed', 'name']:
                if col in gdf.columns:
                    if gdf[col].apply(lambda x: isinstance(x, list)).any():
                        gdf[col] = gdf[col].apply(
                            lambda x: ', '.join(map(str, x)) if isinstance(x, list) else str(x) if x is not None else 'N/A'
                        )
                else:
                    gdf[col] = 'N/A' 
            print(f"OSM: Carregado {cidade} do cache.")
            return cidade, gdf
        except Exception as e:
            print(f"OSM ERROR: Falha ao ler cache GeoJSON para {cidade}: {e}. Tentando baixar.")
            pass 

    try:
        print(f"OSM: Baixando dados OSM para {cidade} ({lugar})...")
        G = ox.graph_from_place(lugar, network_type='drive')
        gdf = ox.graph_to_gdfs(G, nodes=False)
        gdf['geometry'] = gdf['geometry'].simplify(tolerance=0.0001)
        cols_to_keep = ['geometry', 'osmid', 'highway', 'name', 'length', 'maxspeed']
        gdf_filtered = gdf[[c for c in cols_to_keep if c in gdf.columns]].copy()

        for col in ['highway', 'maxspeed', 'name']:
            if col in gdf_filtered.columns:
               if gdf_filtered[col].apply(lambda x: isinstance(x, list)).any():
                  gdf_filtered[col] = gdf_filtered[col].apply(
                      lambda x: ', '.join(map(str, x)) if isinstance(x, list) else str(x) if x is not None else 'N/A'
                  )
            else:
               gdf_filtered[col] = 'N/A' 
        
        gdf_filtered.to_file(cache_file, driver='GeoJSON')
        print(f"OSM: Baixado e salvo {cidade} no cache.")
        return cidade, gdf_filtered
    except Exception as e:
        print(f"OSM CRITICAL ERROR: Falha ao baixar ou processar OSM para {cidade}: {e}")
        return cidade, gpd.GeoDataFrame()

@lru_cache(maxsize=1)
def get_osm_data_combined(force_download=False):
    """Carrega dados OSM para todas as cidades em paralelo."""
    print("OSM_DATA: Iniciando carregamento de dados OSM...")
    os.makedirs(OSM_CACHE_DIR, exist_ok=True)
    lugares = {
        "Foz do Iguaçu": "Foz do Iguaçu, Brazil",
        "Ciudad del Este": "Ciudad del Este, Paraguay",
        "Puerto Iguazú": "Puerto Iguazú, Argentina"
    }
    arestas = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(lugares)) as executor:
        futures = {
            executor.submit(download_osm_city_combined, cidade, lugar, OSM_CACHE_DIR, force_download): cidade 
            for cidade, lugar in lugares.items()
        }
        for future in concurrent.futures.as_completed(futures):
            cidade_nome = futures[future]
            try:
                _, gdf = future.result()
                arestas[cidade_nome] = gdf
            except Exception as e:
                print(f"OSM_DATA ERROR: Falha ao obter resultado para {cidade_nome}: {e}")
                arestas[cidade_nome] = gpd.GeoDataFrame()
    print("OSM_DATA: Carregamento de dados OSM finalizado.")
    return arestas

@lru_cache(maxsize=1)
def get_bairros_foz_local():
    """Carrega o GeoDataFrame de bairros de Foz do Iguaçu."""
    print("BAIRROS: Tentando carregar dados de bairros de Foz do Iguaçu...")
    try:
        if not os.path.exists(BAIRROS_GPKG_PATH):
            print(f"BAIRROS ERROR: Arquivo GPKG de bairros não encontrado: {BAIRROS_GPKG_PATH}")
            return gpd.GeoDataFrame()
            
        gdf_bairros = gpd.read_file(BAIRROS_GPKG_PATH)
        
        # --- NOVO AJUSTE AQUI para priorizar o nome real do bairro ---
        found_name_col = False
        possible_name_columns_priority = ['NOME', 'name', 'nome', 'bairro', 'BAIRRO', 'NOME_BAIRRO']
        
        for col_name in possible_name_columns_priority:
            if col_name in gdf_bairros.columns:
                # Se a coluna já for "NOME", ou se for uma das prioritárias e não for "NOME", renomeia
                if col_name != 'NOME':
                    gdf_bairros = gdf_bairros.rename(columns={col_name: 'NOME'})
                    print(f"BAIRROS INFO: Coluna de nome do bairro renomeada para 'NOME' de '{col_name}'.")
                
                # Certifica que a coluna 'NOME' é do tipo string (alguns shapefiles podem ter números ou outros tipos)
                gdf_bairros['NOME'] = gdf_bairros['NOME'].astype(str)
                # Verifica se a coluna 'NOME' tem valores não-nulos e significativos
                if gdf_bairros['NOME'].count() > 0 and not (gdf_bairros['NOME'] == '').all():
                    found_name_col = True
                    break # Encontrou um nome de coluna válido e significativo, para a busca
                else:
                    print(f"BAIRROS WARNING: Coluna '{col_name}' existe, mas parece vazia ou sem valores significativos. Tentando outras.")
                    
        if not found_name_col:
            # Como último recurso, cria um nome baseado no índice, mas com aviso
            gdf_bairros['NOME'] = "Bairro " + gdf_bairros.index.astype(str)
            print("BAIRROS WARNING: Nenhuma coluna de nome de bairro significativa encontrada. Usando 'Bairro [índice]' como nome.")
        # --- FIM NOVO AJUSTE ---

        gdf_bairros['geometry'] = gdf_bairros['geometry'].simplify(tolerance=0.0001)
        print(f"BAIRROS: Carregado {len(gdf_bairros)} bairros.")
        return gdf_bairros
    except Exception as e:
        print(f"BAIRROS CRITICAL ERROR: Falha ao carregar dados de bairros: {e}")
        return gpd.GeoDataFrame()

def analyze_bairros_congestion_combined(df_jams, gdf_bairros_foz):
    """Analisa congestionamentos por bairro para Foz do Iguaçu."""
    print(f"ANALYZE_BAIRROS: Iniciando análise de congestionamento por bairros. Jams: {len(df_jams)}, Bairros: {len(gdf_bairros_foz)}")
    if gdf_bairros_foz is None or gdf_bairros_foz.empty or df_jams is None or df_jams.empty:
        print("ANALYZE_BAIRROS: Dados de jams ou bairros vazios/nulos.")
        return pd.DataFrame()
    if 'line' not in df_jams.columns:
        print("ANALYZE_BAIRROS: Coluna 'line' não encontrada em df_jams.")
        return pd.DataFrame()
    
    df_jams_copy = df_jams.copy()
    # Cria a geometria LineString a partir da coluna 'line'
    df_jams_copy['geometry'] = df_jams_copy['line'].apply(
        lambda lines: LineString([(p['x'], p['y']) for p in lines if isinstance(p, dict) and 'x' in p and 'y' in p]) 
        if isinstance(lines, list) and len(lines) >= 2 else None
    )
    df_jams_copy = df_jams_copy[df_jams_copy['geometry'].notna()]
    if df_jams_copy.empty:
        print("ANALYZE_BAIRROS: Nenhuma geometria válida encontrada após processar 'line'.")
        return pd.DataFrame()

    try:
        gdf_jams = gpd.GeoDataFrame(df_jams_copy, geometry='geometry')
        # Tenta inferir o CRS do df_jams_copy e definir o mesmo do gdf_bairros_foz
        if gdf_jams.crs is None and gdf_bairros_foz.crs is not None:
            gdf_jams.crs = gdf_bairros_foz.crs
        elif gdf_jams.crs is not None and gdf_bairros_foz.crs is not None and gdf_jams.crs != gdf_bairros_foz.crs:
            gdf_jams = gdf_jams.to_crs(gdf_bairros_foz.crs)

    except Exception as e:
        print(f"ANALYZE_BAIRROS ERROR: Falha ao criar GeoDataFrame de jams: {e}")
        return pd.DataFrame()
    
    try:
        # Realiza o spatial join
        gdf_jams_bairros = gpd.sjoin(gdf_jams, gdf_bairros_foz, how='left', predicate='intersects')
    except Exception as e:
        print(f"ANALYZE_BAIRROS ERROR: Falha ao realizar spatial join: {e}")
        return pd.DataFrame()
    
    # A coluna 'NOME' é verificada e padronizada em get_bairros_foz_local
    if 'NOME' not in gdf_jams_bairros.columns:
        print("ANALYZE_BAIRROS ERROR: Coluna 'NOME' não encontrada no resultado do spatial join.")
        return pd.DataFrame()
    
    agg_dict = {}
    if 'speedKMH' in gdf_jams_bairros.columns: agg_dict['speedKMH'] = 'mean'
    if 'delay' in gdf_jams_bairros.columns: agg_dict['delay'] = 'sum'
    if 'length' in gdf_jams_bairros.columns: agg_dict['length'] = 'sum'
    if 'level' in gdf_jams_bairros.columns: agg_dict['level'] = 'mean'
    agg_dict['uuid'] = 'count' # Conta o número de congestionamentos

    if not agg_dict or 'uuid' not in agg_dict:
        print("ANALYZE_BAIRROS ERROR: Dicionário de agregação vazio ou 'uuid' ausente.")
        return pd.DataFrame()
    
    # Agrupa por bairro e calcula as estatísticas
    bairros_stats = gdf_jams_bairros.groupby('NOME').agg(agg_dict)
    
    rename_map = {
        'uuid': 'total_congestionamentos',
        'speedKMH': 'velocidade_media_kmh',
        'delay': 'atraso_total_s',
        'length': 'extensao_total_m',
        'level': 'nivel_medio_trafego'
    }
    bairros_stats = bairros_stats.rename(columns={k:v for k,v in rename_map.items() if k in bairros_stats.columns})
    bairros_stats = bairros_stats.sort_values('total_congestionamentos', ascending=False).reset_index()
    print(f"ANALYZE_BAIRROS: Análise por bairros concluída. {len(bairros_stats)} bairros com dados.")
    return bairros_stats

def get_color_for_speed_detailed(speed):
    if pd.isna(speed):
        return '#999999' 
    if speed < 10: return '#d73027' # Vermelho escuro
    elif speed < 20: return '#fdae61' # Laranja
    elif speed < 30: return '#fee08b' # Amarelo claro
    elif speed < 40: return '#a6d96a' # Verde claro
    else: return '#1a9850' # Verde escuro

def create_dash_legend_html(title="Velocidade (km/h)"):
    legend_items = [
        (" < 10 km/h", '#d73027'),
        ("10-20 km/h", '#fdae61'),
        ("20-30 km/h", '#fee08b'),
        ("30-40 km/h", '#a6d96a'),
        (" > 40 km/h", '#1a9850'),
        ("Sem dados", '#999999')
    ]
    div_items = [html.Div(title, style={'fontWeight': 'bold', 'marginBottom': '5px'})]
    for text, color in legend_items:
        div_items.append(
            html.Div([
                html.Div(style={'background': color, 'width': '20px', 'height': '20px', 
                                'marginRight': '5px', 'border': '1px solid grey', 'display': 'inline-block'}),
                html.Span(text, style={'fontSize':'12px'})
            ], style={'display': 'flex', 'alignItems': 'center', 'margin': '2px 0'})
        )
    return html.Div(div_items, style={
        'position': 'absolute', 'bottom': '20px', 'right': '10px', 'left': 'auto',
        'width': '160px', 'padding': '10px', 'backgroundColor': 'white',
        'border': '1px solid grey', 'borderRadius': '5px', 'zIndex': '1000',
        'fontSize': '14px'
    })

initial_map_figure = go.Figure(go.Scattermapbox())
initial_map_figure.update_layout(
    mapbox_style="open-street-map",
    mapbox_center_lon=-54.55, mapbox_center_lat=-25.53, mapbox_zoom=11,
    margin={"r":0,"t":0,"l":0,"b":0},
    height=700
)

app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("Dashboard de Tráfego Fronteiriço (Combinado)"), width=12, className="text-center my-4")),
    dbc.Row([
        dbc.Col([
            dbc.Button("Carregar/Atualizar Dados de Tráfego", id='load-data-button', color="primary", className="mb-2"),
            dbc.Progress(id="loading-progress-bar", value=0, striped=True, animated=True, style={'height': '20px', 'marginBottom': '5px'}),
            html.Div(id='loading-progress-text', style={'textAlign': 'center', 'marginBottom': '10px'}),
            html.Div(id='data-summary-info', className="mt-2 small")
        ], width=12)
    ], className="mb-3"),
    dbc.Card(dbc.CardBody([
        html.H4("Filtros", className="card-title"),
        dbc.Row([
            dbc.Col([
                html.Label("Período:", className="form-label"),
                dcc.DatePickerRange(
                    id='date-picker-range',
                    display_format='DD/MM/YYYY',
                    className="mb-2",
                )
            ], md=4),
            dbc.Col([
                html.Label("Cidade:", className="form-label"),
                dcc.Dropdown(
                    id='city-dropdown-filter',
                    options=[
                        {'label': 'Todas', 'value': 'all'},
                        {'label': 'Foz do Iguaçu', 'value': 'Foz do Iguaçu'},
                        {'label': 'Ciudad del Este', 'value': 'Ciudad del Este'},
                        {'label': 'Puerto Iguazú', 'value': 'Puerto Iguazú'}
                    ],
                    value='all', clearable=False, className="mb-2"
                )
            ], md=4),
            dbc.Col([
                html.Label("Hora do Dia (0-23h):", className="form-label"),
                dcc.RangeSlider(
                    id='hour-range-slider', min=0, max=23, step=1,
                    marks={i: str(i) for i in range(0, 24, 2)},
                    value=[0, 23], className="mb-2"
                )
            ], md=4)
        ]),
        dbc.Row([
            dbc.Col([
                html.Label("Dia da Semana:", className="form-label"),
                dcc.Dropdown(
                    id='day-of-week-filter',
                    options=[
                        {'label': 'Todos', 'value': 'all'},
                        {'label': 'Segunda-feira', 'value': 'Monday'},
                        {'label': 'Terça-feira', 'value': 'Tuesday'},
                        {'label': 'Quarta-feira', 'value': 'Wednesday'},
                        {'label': 'Quinta-feira', 'value': 'Thursday'},
                        {'label': 'Sexta-feira', 'value': 'Friday'},
                        {'label': 'Sábado', 'value': 'Saturday'},
                        {'label': 'Domingo', 'value': 'Sunday'}
                    ],
                    value='all', clearable=False, className="mb-2"
                )
            ], md=4),
            dbc.Col([
                html.Label("Velocidade Mínima (km/h):", className="form-label"),
                dcc.Input(id='min-speed-filter', type='number', value=0, min=0, max=200, step=1, className="form-control mb-2")
            ], md=4),
            dbc.Col([
                html.Label("Velocidade Máxima (km/h):", className="form-label"),
                dcc.Input(id='max-speed-filter', type='number', value=120, min=0, max=200, step=1, className="form-control mb-2")
            ], md=4)
        ])
    ]), className="mb-4"),
    dbc.Row([
        dbc.Col([
            dbc.Card(dbc.CardBody([
                html.H4("Mapa de Congestionamento", className="card-title"),
                html.Div(id='map-legend-div', style={'position': 'relative'}), # Container para a legenda
                dcc.Graph(id='traffic-map', figure=initial_map_figure, config={'scrollZoom': True})
            ]))
        ], md=8, className="mb-3"),
        dbc.Col([
            dbc.Card(dbc.CardBody([
                html.H4("Estatísticas de Congestionamento", className="card-title"),
                html.Div(id='general-stats-output', className="mb-3"),
                html.H5("Principais Pontos de Congestionamento", className="mt-3"),
                dash_table.DataTable(
                    id='hotspots-table',
                    columns=[
                        {"name": "Localização (Aprox.)", "id": "location_approx"},
                        {"name": "Nº Eventos", "id": "event_count"},
                        {"name": "Vel. Média", "id": "avg_speed_kmh"},
                        {"name": "Rua Principal", "id": "street_name"},
                        {"name": "Cidade", "id": "city_name"},
                    ],
                    style_cell={'textAlign': 'left', 'fontSize': '12px'},
                    style_header={'fontWeight': 'bold'},
                    page_size=10,
                ),
                html.H5("Análise por Bairro (Foz do Iguaçu)", className="mt-4"),
                dash_table.DataTable(
                    id='bairros-table',
                    columns=[
                        {"name": "Bairro", "id": "NOME"}, # Agora usará o nome real do bairro
                        {"name": "Congestionamentos", "id": "total_congestionamentos"},
                        {"name": "Vel. Média", "id": "velocidade_media_kmh"},
                    ],
                    style_cell={'textAlign': 'left', 'fontSize': '12px'},
                    style_header={'fontWeight': 'bold'},
                    page_size=5,
                )
            ]))
        ], md=4)
    ]),
    dcc.Interval(id='interval-component', interval=1*1000, n_intervals=0), # Intervalo de 1 segundo
    dcc.Store(id='loaded-data-store'), # Armazena um sinal de que os dados foram carregados
    dcc.Store(id='osm-data-store'), # Armazena um sinal de que os dados OSM foram carregados
    dcc.Store(id='bairros-data-store') # Armazena um sinal de que os dados de bairros foram carregados
], fluid=True)
# Callbacks

@app.callback(
    [Output('loading-progress-bar', 'value'),
     Output('loading-progress-text', 'children'),
     Output('loaded-data-store', 'data'), # Atualizado com um timestamp para acionar outros callbacks
     Output('data-summary-info', 'children')],
    [Input('load-data-button', 'n_clicks')],
    [State('loaded-data-store', 'data')] # Usado para verificar o estado atual, mas não é um trigger principal
)
def handle_data_load_button(n_clicks, existing_data_trigger):
    global load_running, loaded_data, load_progress, load_message, failed_files
    ctx = dash.callback_context
    print(f"\n--- CALLBACK START: handle_data_load_button - Triggered by: {ctx.triggered} ---")

    # If the callback wasn't triggered by the button, check current loading status
    if not ctx.triggered or ctx.triggered[0]['prop_id'] != 'load-data-button.n_clicks':
        if load_running:
            print(f"DEBUG: handle_data_load_button - Loading in progress. Progress: {load_progress}%")
            return load_progress, load_message, dash.no_update, dash.no_update
        elif loaded_data is not None and not loaded_data.empty:
            summary_parts = []
            summary_parts.append(html.P(f"{len(loaded_data):,} registros carregados."))
            summary_parts.append(html.P(f"Período: {loaded_data['time'].min().strftime('%d/%m/%y')} a {loaded_data['time'].max().strftime('%d/%m/%y')}."))
            
            if failed_files:
                summary_parts.append(html.P(html.Strong(f"Atenção: {len(failed_files)} arquivo(s) falhou(ram) na leitura!")))
                summary_parts.append(html.P("Por favor, verifique os seguintes arquivos no diretório de dados e tente novamente após removê-los ou corrigi-los:"))
                summary_parts.append(html.Ul([html.Li(f) for f in failed_files]))
            summary = html.Div(summary_parts)
            print("DEBUG: handle_data_load_button - Data already loaded (not triggered by button).")
            return 100, "Dados carregados.", datetime.now().timestamp(), summary
        else:
            print("DEBUG: handle_data_load_button - No data loaded and not triggered by button.")
            return 0, "Clique em 'Carregar Dados'.", None, "Nenhum dado carregado."
    
    # If triggered by the button
    if load_running:
        print("DEBUG: handle_data_load_button - Button clicked, but loading is already in progress.")
        return load_progress, f"Carregamento já em progresso: {load_message}", dash.no_update, dash.no_update
    
    # Start a new load
    print("DEBUG: handle_data_load_button - Button clicked, initiating new loading.")
    thread = threading.Thread(target=load_data_thread_combined)
    thread.start()
    return 0, "Iniciando carregamento...", "loading", dash.no_update

@app.callback(
    [Output('loading-progress-bar', 'value', allow_duplicate=True),
     Output('loading-progress-text', 'children', allow_duplicate=True),
     Output('loaded-data-store', 'data', allow_duplicate=True), # Allows this callback to update as well
     Output('data-summary-info', 'children', allow_duplicate=True)],
    [Input('interval-component', 'n_intervals')],
    prevent_initial_call=True 
)
def update_loading_status(n_intervals):
    global load_running, loaded_data, load_progress, load_message, failed_files

    if load_running:
        return load_progress, load_message, dash.no_update, dash.no_update
    elif loaded_data is not None and load_progress == 100:
        summary_parts = []
        summary_parts.append(html.P(f"{len(loaded_data):,} registros carregados."))
        if not loaded_data.empty:
            summary_parts.append(html.P(f"Período: {loaded_data['time'].min().strftime('%d/%m/%y')} a {loaded_data['time'].max().strftime('%d/%m/%y')}."))
        
        if failed_files:
            summary_parts.append(html.P(html.Strong(f"Atenção: {len(failed_files)} arquivo(s) falhou(ram) na leitura!")))
            summary_parts.append(html.P("Por favor, verifique os seguintes arquivos no diretório de dados e tente novamente após removê-los ou corrigi-los:"))
            summary_parts.append(html.Ul([html.Li(f) for f in failed_files]))
        
        summary = html.Div(summary_parts)
        
        print(f"DEBUG: update_loading_status - Carregamento completo, atualizando store: {load_message}")
        return 100, load_message, datetime.now().timestamp(), summary 
    
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update

@app.callback(
    [Output('osm-data-store', 'data'),
     Output('bairros-data-store', 'data')],
    [Input('loaded-data-store', 'data')], # Triggers when the loaded data signal is received
    prevent_initial_call=True
)
def preload_geospatial_data(data_loaded_signal):
    print(f"\n--- CALLBACK START: preload_geospatial_data - data_loaded_signal: {data_loaded_signal} ---")
    if not isinstance(data_loaded_signal, (int, float)):
        print("DEBUG: preload_geospatial_data - Loaded data signal is not a timestamp (might be 'loading' or None). Preventing update.")
        raise PreventUpdate
    
    print("DEBUG: preload_geospatial_data - Initiating geospatial data pre-loading.")
    start_time_osm_preload = time.time()
    osm_data = get_osm_data_combined(force_download=False) 
    print(f"DEBUG: preload_geospatial_data - OSM loading completed in {time.time() - start_time_osm_preload:.2f}s")

    start_time_bairros_preload = time.time()
    bairros_data = get_bairros_foz_local()
    print(f"DEBUG: preload_geospatial_data - Neighborhoods loading completed in {time.time() - start_time_bairros_preload:.2f}s")

    osm_loaded_signal = {city: True for city in osm_data} if osm_data else {}
    bairros_loaded_signal = True if bairros_data is not None and not bairros_data.empty else False
    
    print(f"DEBUG: preload_geospatial_data - OSM Loaded: {osm_loaded_signal}, Bairros Loaded: {bairros_loaded_signal}")
    return osm_loaded_signal, bairros_loaded_signal

@app.callback(
    [Output('date-picker-range', 'min_date_allowed'),
     Output('date-picker-range', 'max_date_allowed'),
     Output('date-picker-range', 'start_date'),
     Output('date-picker-range', 'end_date')],
    [Input('loaded-data-store', 'data')]
)
def update_date_picker(data_loaded_signal):
    print(f"\n--- CALLBACK START: update_date_picker - data_loaded_signal: {data_loaded_signal} ---")
    if not isinstance(data_loaded_signal, (int, float)) or loaded_data is None or loaded_data.empty:
        print("DEBUG: update_date_picker - Data not loaded or invalid signal, using default dates.")
        default_start = datetime.now().date() - timedelta(days=7) 
        default_end = datetime.now().date()
        return default_start, default_end, default_start, default_end
    
    min_date = loaded_data['time'].min().date()
    max_date = loaded_data['time'].max().date()
    print(f"DEBUG: update_date_picker - Data dates: {min_date} to {max_date}")
    return min_date, max_date, min_date, max_date

@app.callback(
    [Output('traffic-map', 'figure'),
     Output('hotspots-table', 'data'),
     Output('bairros-table', 'data'),
     Output('general-stats-output', 'children'),
     Output('map-legend-div', 'children')],
    [Input('loaded-data-store', 'data'),
     Input('osm-data-store', 'data'),
     Input('bairros-data-store', 'data'),
     Input('date-picker-range', 'start_date'),
     Input('date-picker-range', 'end_date'),
     Input('city-dropdown-filter', 'value'),
     Input('hour-range-slider', 'value'),
     Input('day-of-week-filter', 'value'),
     Input('min-speed-filter', 'value'),
     Input('max-speed-filter', 'value')]
)
def update_dashboard_outputs(main_data_signal, osm_data_signal, bairros_data_signal,
                             start_date_str, end_date_str, selected_city,
                             hour_range, selected_day_of_week, min_speed, max_speed):
    
    start_time_callback = time.time()
    print(f"\n--- CALLBACK START: update_dashboard_outputs ({start_time_callback:.2f}s) ---")
    print(f"DEBUG: update_dashboard_outputs - Signals: Main Data: {main_data_signal}, OSM: {osm_data_signal}, Bairros: {bairros_data_signal}")

    if not isinstance(main_data_signal, (int, float)) or loaded_data is None or loaded_data.empty:
        print("ERROR: update_dashboard_outputs - Main data not loaded or empty. Returning initial state.")
        return initial_map_figure, [], [], "Carregue os dados para visualizar o dashboard.", create_dash_legend_html()

    df_filtered = loaded_data.copy()
    print(f"DEBUG: update_dashboard_outputs - Initial data for filtering: {len(df_filtered):,} records.")
    
    # --- Filtering Stage ---
    start_time_filter = time.time()
    if start_date_str and end_date_str:
        start_date = pd.to_datetime(start_date_str).normalize()
        end_date = pd.to_datetime(end_date_str).normalize() + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        df_filtered = df_filtered[(df_filtered['time'] >= start_date) & (df_filtered['time'] <= end_date)]
    if selected_city != 'all':
        df_filtered = df_filtered[df_filtered['city'] == selected_city]
    if hour_range:
        df_filtered = df_filtered[(df_filtered['hour'] >= hour_range[0]) & (df_filtered['hour'] <= hour_range[1])]
    if selected_day_of_week != 'all':
        df_filtered = df_filtered[df_filtered['day_of_week'] == selected_day_of_week]
    if min_speed is not None:
        df_filtered = df_filtered[df_filtered['speedKMH'] >= min_speed]
    if max_speed is not None:
        df_filtered = df_filtered[df_filtered['speedKMH'] <= max_speed]
    print(f"DEBUG: update_dashboard_outputs - Filtering completed in {time.time() - start_time_filter:.2f}s. Records after filter: {len(df_filtered):,}.")

    if df_filtered.empty:
        print("WARNING: update_dashboard_outputs - No data found for the selected filters.")
        return initial_map_figure, [], [], "Nenhum dado encontrado para os filtros selecionados.", create_dash_legend_html()

    map_traces = []
    
    # --- OSM Street Plotting ---
    start_time_osm_plot = time.time()
    osm_streets_data = {}
    if osm_data_signal:
        osm_streets_data = get_osm_data_combined()
        print(f"DEBUG: update_dashboard_outputs - OSM data loaded for {len(osm_streets_data)} cities.")
    else:
        print("WARNING: update_dashboard_outputs - OSM signal not received. Street maps will not be rendered.")

    if osm_streets_data:
        num_street_traces_added = 0
        for city_name, gdf_streets in osm_streets_data.items():
            if selected_city != 'all' and city_name != selected_city:
                continue

            if gdf_streets is not None and not gdf_streets.empty:
                # Ensure 'name' column exists and is string type
                if 'name' not in gdf_streets.columns:
                    gdf_streets['name'] = 'N/A'
                if gdf_streets['name'].apply(lambda x: isinstance(x, list)).any():
                    gdf_streets['name'] = gdf_streets['name'].apply(
                        lambda x: ', '.join(map(str, x)) if isinstance(x, list) else str(x) if x is not None else 'N/A'
                    )

                # Simplify geometry for performance
                gdf_streets_simplified = gdf_streets.copy()
                gdf_streets_simplified['geometry'] = gdf_streets_simplified['geometry'].simplify(tolerance=0.00005)

                all_lons_streets = []
                all_lats_streets = []
                
                # Limit streets for performance
                if len(gdf_streets_simplified) > 5000:
                    print(f"DEBUG: update_dashboard_outputs - Limiting streets for {city_name} to 5000 for performance.")
                    gdf_streets_sample = gdf_streets_simplified.sample(n=5000, random_state=42)
                else:
                    gdf_streets_sample = gdf_streets_simplified

                for _, street_series in gdf_streets_sample.iterrows():
                    if street_series.geometry and not street_series.geometry.is_empty:
                        x_coords, y_coords = street_series.geometry.xy
                        all_lons_streets.extend(list(x_coords))
                        all_lats_streets.extend(list(y_coords))
                        all_lons_streets.append(None)
                        all_lats_streets.append(None)

                if all_lons_streets:
                    map_traces.append(go.Scattermapbox(
                        lon=all_lons_streets, lat=all_lats_streets,
                        mode='lines',
                        line=dict(width=0.5, color='grey'),
                        opacity=0.7,
                        name=f"Ruas {city_name}",
                        hoverinfo='skip'
                    ))
                    num_street_traces_added += 1
        print(f"DEBUG: update_dashboard_outputs - Added {num_street_traces_added} street trace(s) in {time.time() - start_time_osm_plot:.2f}s.")

    # --- Congestion Plotting (Jams) ---
    start_time_jams_plot = time.time()
    lons = []
    lats = []
    speeds = []
    hover_texts = []
    
    df_jams_for_map = df_filtered
    if len(df_filtered) > MAX_MAP_POINTS_TO_PLOT:
        df_jams_for_map = df_filtered.sample(n=MAX_MAP_POINTS_TO_PLOT, random_state=42)
        print(f"DEBUG: update_dashboard_outputs - Sampling congestion data for map: {len(df_jams_for_map):,} of {len(df_filtered):,} total.")

    for _, row in df_jams_for_map.iterrows():
        line_coords = row['line']
        if line_coords and len(line_coords) > 0:
            mid_idx = len(line_coords) // 2
            mid_point = line_coords[mid_idx]
            if isinstance(mid_point, dict) and 'x' in mid_point and 'y' in mid_point:
                lons.append(mid_point['x'])
                lats.append(mid_point['y'])
                speeds.append(row['speedKMH'])
                hover_texts.append(
                    f"Vel: {row['speedKMH']:.1f} km/h<br>"
                    f"Hora: {row['time'].strftime('%H:%M')}<br>"
                    f"Cidade: {row['city']}"
                )

    if lons:
        colors = [get_color_for_speed_detailed(s) for s in speeds]
        map_traces.append(go.Scattermapbox(
            lon=lons, lat=lats,
            mode='markers',
            marker=go.scattermapbox.Marker(
                size=8, 
                color=colors,
                opacity=0.8
            ),
            text=hover_texts,
            hoverinfo='text',
            name="Congestionamentos"
        ))
    print(f"DEBUG: update_dashboard_outputs - Added {len(lons):,} congestion traces in {time.time() - start_time_jams_plot:.2f}s.")

    # --- Map Configuration ---
    start_time_map_layout = time.time()
    fig = go.Figure(data=map_traces)
    map_center_lon = -54.55
    map_center_lat = -25.53
    map_zoom = 11
    if selected_city != 'all' and selected_city in CITY_BOUNDS:
        bounds = CITY_BOUNDS[selected_city]
        map_center_lon = (bounds['min_lon'] + bounds['max_lon']) / 2
        map_center_lat = (bounds['min_lat'] + bounds['max_lat']) / 2
        map_zoom = 13
    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox_center_lon=map_center_lon, mapbox_center_lat=map_center_lat, mapbox_zoom=map_zoom,
        margin={"r":0,"t":30,"l":0,"b":0},
        height=700,
        showlegend=False
    )
    print(f"DEBUG: update_dashboard_outputs - Map figure updated in {time.time() - start_time_map_layout:.2f}s.")

    # --- Hotspots Table Generation ---
    start_time_hotspots_table = time.time()
    hotspots_table_data = []
    if not df_filtered.empty:
        hotspot_points = []
        for _, row in df_filtered.iterrows():
            line_coords = row['line']
            if line_coords and len(line_coords) > 0:
                # Using the first point of the line for hotspot location
                first_point = line_coords[0] 
                if isinstance(first_point, dict) and 'x' in first_point and 'y' in first_point:
                    hotspot_points.append({'geometry': Point(first_point['x'], first_point['y']), 'speedKMH': row['speedKMH'], 'city': row['city']})
        
        if hotspot_points:
            gdf_hotspots = gpd.GeoDataFrame(hotspot_points, crs="EPSG:4326")

            loc_counts = defaultdict(int)
            loc_speeds = defaultdict(list)
            loc_cities = {}
            
            for _, row in gdf_hotspots.iterrows():
                # Round coordinates to group nearby points
                lon, lat = round(row.geometry.x, 4), round(row.geometry.y, 4)
                point_key = (lon, lat)
                loc_counts[point_key] += 1
                loc_speeds[point_key].append(row['speedKMH'])
                loc_cities[point_key] = row['city']

            sorted_locs = sorted(loc_counts.items(), key=lambda item: item[1], reverse=True)[:20]

            if osm_data_signal and osm_streets_data:
                print("DEBUG: update_dashboard_outputs - Performing spatial join for street information of hotspots.")
                
                # Combine all city streets into one GeoDataFrame for efficient sjoin
                all_streets_gdf_list: List[gpd.GeoDataFrame] = [] 
                for city_name, gdf_streets in osm_streets_data.items():
                    if gdf_streets is not None and not gdf_streets.empty:
                        # Ensure 'name' column exists and is string type
                        if 'name' not in gdf_streets.columns:
                            gdf_streets['name'] = 'Não identificada'
                        if gdf_streets['name'].apply(lambda x: isinstance(x, list)).any():
                            gdf_streets['name'] = gdf_streets['name'].apply(
                                lambda x: ', '.join(map(str, x)) if isinstance(x, list) else str(x) if x is not None else 'Não identificada'
                            )
                        
                        if gdf_streets.crs is None:
                            gdf_streets.set_crs("EPSG:4326", allow_override=True, inplace=True)
                        elif gdf_streets.crs != "EPSG:4326":
                            gdf_streets = gdf_streets.to_crs("EPSG:4326")
                        
                        all_streets_gdf_list.append(gdf_streets[['geometry', 'name']].copy())

                if all_streets_gdf_list:
                    # Create the combined GeoDataFrame of streets
                    all_streets_gdf: gpd.GeoDataFrame = gpd.GeoDataFrame(
                        pd.concat(all_streets_gdf_list, ignore_index=True), 
                        crs="EPSG:4326"
                    )
                    all_streets_gdf.sindex # Build spatial index for speed

                    hotspots_to_join = []
                    for (lon, lat), count in sorted_locs:
                        hotspots_to_join.append({'geometry': Point(lon, lat), 'event_count': count, 'avg_speed_kmh': np.mean(loc_speeds[(lon, lat)]), 'city': loc_cities[(lon, lat)]})
                    
                    if hotspots_to_join:
                        gdf_hotspots_for_join = gpd.GeoDataFrame(hotspots_to_join, crs="EPSG:4326")
                        gdf_hotspots_for_join.sindex

                        try:
                            # Use max_distance to limit the search and speed up
                            # 0.001 degrees is roughly 111 meters at the equator
                            hotspots_with_streets = gpd.sjoin_nearest(gdf_hotspots_for_join, all_streets_gdf, how="left", max_distance=0.001)
                        except AttributeError: # Fallback for older GeoPandas versions if sjoin_nearest isn't available
                            gdf_hotspots_buffered = gdf_hotspots_for_join.copy()
                            gdf_hotspots_buffered['geometry'] = gdf_hotspots_buffered.geometry.buffer(0.0001) # Small buffer
                            hotspots_with_streets = gpd.sjoin(gdf_hotspots_buffered, all_streets_gdf, how="left", predicate='intersects')


                        for _, row in hotspots_with_streets.iterrows():
                            street_name = row.get('name', 'Não identificada')
                            if isinstance(street_name, list):
                                street_name = ', '.join(map(str, street_name))
                            
                            hotspots_table_data.append({
                                "location_approx": f"({row.geometry.y:.3f}, {row.geometry.x:.3f})",
                                "event_count": int(row['event_count']),
                                "avg_speed_kmh": f"{row['avg_speed_kmh']:.1f}",
                                "street_name": str(street_name) if street_name else "Não identificada",
                                "city_name": row['city']
                            })
                    else:
                        print("DEBUG: update_dashboard_outputs - No hotspots to perform street join.")
                else:
                    print("DEBUG: update_dashboard_outputs - No combined OSM street data available.")
            else:
                print("WARNING: update_dashboard_outputs - OSM signal not received or OSM data empty for hotspots. Street names will not be displayed.")
                for (lon, lat), count in sorted_locs:
                    avg_speed = np.mean(loc_speeds[(lon, lat)])
                    hotspots_table_data.append({
                        "location_approx": f"({lat:.3f}, {lon:.3f})",
                        "event_count": count,
                        "avg_speed_kmh": f"{avg_speed:.1f}",
                        "street_name": "N/A (Dados OSM não disponíveis)",
                        "city_name": loc_cities[(lon, lat)]
                    })
    print(f"DEBUG: update_dashboard_outputs - Hotspots table data generated: {len(hotspots_table_data)} rows in {time.time() - start_time_hotspots_table:.2f}s.")

    # --- Neighborhood Analysis ---
    start_time_bairros_analysis = time.time()
    bairros_table_data = []
    if bairros_data_signal and selected_city in ['all', 'Foz do Iguaçu']:
        gdf_bairros_foz = get_bairros_foz_local()
        if gdf_bairros_foz is not None and not gdf_bairros_foz.empty:
            df_foz_jams = df_filtered[df_filtered['city'] == 'Foz do Iguaçu']
            if not df_foz_jams.empty:
                bairros_stats_df = analyze_bairros_congestion_combined(df_foz_jams, gdf_bairros_foz)
                if bairros_stats_df is not None and not bairros_stats_df.empty:
                    bairros_stats_df_display = bairros_stats_df[['NOME', 'total_congestionamentos']].copy()
                    if 'velocidade_media_kmh' in bairros_stats_df.columns:
                         bairros_stats_df_display['velocidade_media_kmh'] = bairros_stats_df['velocidade_media_kmh'].round(1)
                    else:
                         bairros_stats_df_display['velocidade_media_kmh'] = 'N/A'
                    bairros_table_data = bairros_stats_df_display.to_dict('records')
                    print(f"DEBUG: update_dashboard_outputs - Bairros table data generated: {len(bairros_table_data)} rows.")
            else:
                print("DEBUG: update_dashboard_outputs - df_foz_jams está vazio para análise de bairros.")
        else:
            print("DEBUG: update_dashboard_outputs - gdf_bairros_foz está vazio ou não carregado.")
    else:
        print("DEBUG: update_dashboard_outputs - Bairros data signal não recebido ou cidade não é Foz do Iguaçu.")
    print(f"DEBUG: update_dashboard_outputs - Neighborhood analysis completed in {time.time() - start_time_bairros_analysis:.2f}s.")

    # --- General Statistics ---
    total_jams = len(df_filtered)
    avg_speed_overall = df_filtered['speedKMH'].mean() if total_jams > 0 else 0
    stats_html = [
        html.P(f"Total de Eventos de Congestionamento: {total_jams:,}"),
        html.P(f"Velocidade Média Geral: {avg_speed_overall:.1f} km/h")
    ]

    header = html.H5(f"Estatísticas para: {selected_city}") if selected_city != 'all' else None
    if header:
        stats_html_with_header = [header] + stats_html
    else:
        stats_html_with_header = stats_html

    legend_html_component = create_dash_legend_html()
    
    print(f"--- CALLBACK END: update_dashboard_outputs. Total Time: {time.time() - start_time_callback:.2f}s ---\n")
    return fig, hotspots_table_data, bairros_table_data, stats_html_with_header, legend_html_component

if __name__ == '__main__':
    print("Iniciando o servidor Dash para desenvolvimento local...")
    app.run(debug=True, host='127.0.0.1', port=8056)