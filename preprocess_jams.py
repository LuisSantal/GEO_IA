import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
from datetime import datetime, timedelta
import warnings
from collections import defaultdict
import ast # Para avaliar strings que representam listas/dicionários

# --- CONFIGURAÇÕES DE CAMINHOS (AJUSTE AQUI!) ---
# Diretório onde estão seus arquivos .h5 brutos
RAW_DATA_DIR = "/home/les.alvarez.2015/Área de Trabalho/DADOS WAZE/Códigos/Dados/DataFeed/jams"

# Diretório onde o arquivo .parquet processado será salvo
PROCESSED_DATA_DIR = "/home/les.alvarez.2015/Área de Trabalho/DADOS WAZE/DadosProcessados"
PROCESSED_FILE_NAME = "jams_processed.parquet" # Formato Parquet para performance

# Caminho completo para o arquivo .parquet processado
PROCESSED_FILE_PATH = os.path.join(PROCESSED_DATA_DIR, PROCESSED_FILE_NAME)
# --- FIM DAS CONFIGURAÇÕES DE CAMINHOS ---

# Bounds das cidades (copiado do dashboard)
CITY_BOUNDS = {
    "Foz do Iguaçu": {"min_lon": -54.62, "max_lon": -54.5, "min_lat": -25.55, "max_lat": -25.45},
    "Ciudad del Este": {"min_lon": -54.7, "max_lon": -54.6, "min_lat": -25.55, "max_lat": -25.45},
    "Puerto Iguazú": {"min_lon": -54.6, "max_lon": -54.5, "min_lat": -25.61, "max_lat": -25.55}
}

warnings.filterwarnings('ignore', category=UserWarning)

def classify_city(line_coords_evaluated):
    """Classifies the city based on the midpoint of the line coordinates.
    Expects line_coords_evaluated to be a list of dicts or similar structure."""
    
    if not line_coords_evaluated or not isinstance(line_coords_evaluated, list) or len(line_coords_evaluated) == 0:
        return "Desconhecido"
    
    # Adicionando uma verificação mais robusta aqui também, caso a avaliação anterior falhe.
    # Garante que todos os pontos na lista são dicionários com 'x' e 'y'.
    if not all(isinstance(pt, dict) and 'x' in pt and 'y' in pt for pt in line_coords_evaluated):
        return "Desconhecido"
    
    midpoint_idx = len(line_coords_evaluated) // 2
    # Fallback para o último ponto se midpoint_idx for igual ou maior que o tamanho da lista
    if midpoint_idx >= len(line_coords_evaluated): 
        midpoint_idx = len(line_coords_evaluated) - 1 if len(line_coords_evaluated) > 0 else 0
    
    midpoint = line_coords_evaluated[midpoint_idx]
    
    lon, lat = midpoint['x'], midpoint['y']
    for city, bounds in CITY_BOUNDS.items():
        if (bounds['min_lon'] <= lon <= bounds['max_lon'] and
            bounds['min_lat'] <= lat <= bounds['max_lat']):
            return city
    return "Desconhecido"

def preprocess_jams_data():
    """Reads raw .h5 files, processes them, and saves to a single .parquet file."""
    print("PREPROCESS: Iniciando pré-processamento de dados de jams...")

    if not os.path.exists(RAW_DATA_DIR):
        print(f"ERROR: Diretório de dados brutos não encontrado: {RAW_DATA_DIR}")
        return

    files = [f for f in os.listdir(RAW_DATA_DIR) if f.lower().endswith('.h5')]
    if not files:
        print(f"WARNING: Nenhum arquivo .h5 encontrado em {RAW_DATA_DIR}. Não há dados para processar.")
        return

    print(f"PREPROCESS: Encontrados {len(files)} arquivos .h5. Lendo e processando...")

    df_list = []
    processed_count = 0
    failed_files_processing = []

    for file_name in files:
        file_path = os.path.join(RAW_DATA_DIR, file_name)
        try:
            df = pd.read_hdf(file_path)
            required_cols = ['uuid', 'pubMillis', 'line', 'speedKMH']
            if not all(col in df.columns for col in required_cols):
                print(f"WARNING: Arquivo '{file_name}' não contém todas as colunas necessárias. Pulando.")
                failed_files_processing.append(f"{file_name} (colunas ausentes)")
                continue
            df_list.append(df)
            processed_count += 1
        except (IOError, OSError, KeyError, pd.errors.EmptyDataError) as e:
            print(f"ERROR: Falha ao ler ou processar arquivo '{file_name}': {e}")
            failed_files_processing.append(f"{file_name} (erro de leitura/formato)")
        except Exception as e:
            print(f"CRITICAL ERROR: Erro inesperado ao processar arquivo '{file_name}': {e}")
            failed_files_processing.append(f"{file_name} (erro inesperado)")

    if not df_list:
        print("ERROR: Nenhum dado válido foi carregado dos arquivos brutos para processamento.")
        return

    print("PREPROCESS: Concatenando todos os DataFrames lidos...")
    dataFrameJams = pd.concat(df_list, ignore_index=True)
    print(f"PREPROCESS: Total de registros brutos concatenados: {len(dataFrameJams):,}")

    print("PREPROCESS: Realizando limpeza e engenharia de features...")
    dataFrameJamsClean = dataFrameJams.copy()
    dataFrameJamsClean = dataFrameJamsClean[~dataFrameJamsClean['uuid'].duplicated()]
    
    # --- CORREÇÃO AQUI para a coluna 'line' ---
    # 1. Tentar avaliar a string, se já for uma lista, manter. Se der erro, colocar None.
    def safe_literal_eval(val):
        if isinstance(val, str):
            try:
                # ast.literal_eval é mais seguro que eval()
                return ast.literal_eval(val)
            except (ValueError, SyntaxError):
                return None # Retorna None se a string não for uma estrutura Python válida
        elif isinstance(val, list):
            return val # Se já for uma lista, mantém
        return None # Para outros tipos inesperados

    dataFrameJamsClean['line_evaluated'] = dataFrameJamsClean['line'].apply(safe_literal_eval)
    
    # Filtrar linhas onde a avaliação da geometria falhou
    dataFrameJamsClean = dataFrameJamsClean[dataFrameJamsClean['line_evaluated'].notna()]
    dataFrameJamsClean = dataFrameJamsClean[dataFrameJamsClean['line_evaluated'].apply(lambda x: isinstance(x, list) and len(x) > 1)]

    # A coluna 'line' original não é mais necessária para o processamento,
    # mas a manteremos como string para salvar no Parquet e garantir que o tipo não mude
    # antes de ser salva, e depois reavaliada no dashboard.
    dataFrameJamsClean['line'] = dataFrameJamsClean['line_evaluated'].apply(str) 

    print("PREPROCESS: Convertendo timestamps e adicionando colunas temporais...")
    dataFrameJamsClean['time'] = pd.to_datetime(dataFrameJamsClean['pubMillis'], unit='ms')
    dataFrameJamsClean['hour'] = dataFrameJamsClean['time'].dt.hour
    dataFrameJamsClean['day_of_week'] = dataFrameJamsClean['time'].dt.day_name()
    
    # Classifica cidades, usando a coluna 'line_evaluated'
    print("PREPROCESS: Classificando cidades...")
    dataFrameJamsClean['city'] = dataFrameJamsClean['line_evaluated'].apply(classify_city)

    # Adiciona colunas padrão se não existirem
    for col_to_check in ['delay', 'length', 'level']:
        if col_to_check not in dataFrameJamsClean.columns:
            dataFrameJamsClean[col_to_check] = 0

    print(f"PREPROCESS: Dados limpos e features adicionadas. Total de registros finais: {len(dataFrameJamsClean):,}")

    # Garante que o diretório de destino existe
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

    print(f"PREPROCESS: Salvando dados processados em '{PROCESSED_FILE_PATH}'...")
    try:
        # Colunas a serem salvas no Parquet. Removendo a temporária 'line_evaluated' e 'pubMillis'.
        # Certifique-se que todas as colunas que espera no Dash estão aqui.
        cols_to_save = [col for col in dataFrameJamsClean.columns if col not in ['pubMillis', 'line_evaluated']]
        
        # Certifique-se que a coluna 'line' é string ANTES de salvar no Parquet.
        # Parquet não gosta de colunas com tipos mistos ou objetos Python complexos diretamente.
        dataFrameJamsClean['line'] = dataFrameJamsClean['line'].astype(str)

        dataFrameJamsClean[cols_to_save].to_parquet(PROCESSED_FILE_PATH, index=False)
        print(f"SUCCESS: Dados processados salvos com sucesso em '{PROCESSED_FILE_PATH}'.")
        if failed_files_processing:
            print(f"WARNING: {len(failed_files_processing)} arquivo(s) bruto(s) falhou(ram) durante o processamento:")
            for f in failed_files_processing:
                print(f"  - {f}")
    except Exception as e:
        print(f"CRITICAL ERROR: Falha ao salvar o arquivo processado em '{PROCESSED_FILE_PATH}': {e}")

if __name__ == "__main__":
    preprocess_jams_data()