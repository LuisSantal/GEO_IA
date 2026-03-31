import pandas as pd
import os

def convert_folder(folder_path):
    if not os.path.exists(folder_path):
        return
    
    files = [f for f in os.listdir(folder_path) if f.endswith('.h5')]
    print(f"Encontrados {len(files)} arquivos em {folder_path}")
    
    for f in files:
        h5_path = os.path.join(folder_path, f)
        pq_path = h5_path.replace('.h5', '.parquet')
        try:
            df = pd.read_hdf(h5_path, key='s')
            df.to_parquet(pq_path)
            # Opcional: remover o .h5 original para economizar espaço
            # os.remove(h5_path) 
            print(f"✅ {f} -> Parquet")
        except Exception as e:
            print(f"❌ Erro em {f}: {e}")

# Executa para as suas pastas
convert_folder('alerts')
convert_folder('jams')