import streamlit as st
import pandas as pd
import json
import io
import os
import tempfile
import plotly.express as px
from datetime import datetime
from utils.drive_loader import extract_id_from_share_url, download_public_file, list_folder_files
import h5py
import numpy as np


st.set_page_config(page_title="GEO_IA Dashboard", layout="wide")


def load_json_bytes(content: bytes) -> pd.DataFrame:
    try:
        j = json.loads(content)
    except Exception:
        # try as text
        j = json.loads(content.decode('utf-8'))
    # if top-level is list of records
    if isinstance(j, list):
        return pd.json_normalize(j)
    if isinstance(j, dict):
        # try to find first list value
        for v in j.values():
            if isinstance(v, list):
                return pd.json_normalize(v)
        # otherwise normalize dict
        return pd.json_normalize(j)
    raise ValueError("Unsupported JSON structure")


def show_basic_analysis(df: pd.DataFrame):
    st.write("**Preview**")
    st.dataframe(df.head(200))
    st.write("**Summary**")
    col1, col2 = st.columns(2)
    with col1:
        st.write(df.describe(include='all').T)
    with col2:
        st.write(pd.DataFrame({"missing": df.isna().sum(), "dtype": df.dtypes.astype(str)}))


def detect_latlon(df: pd.DataFrame):
    lat_cols = [c for c in df.columns if c.lower() in ("lat", "latitude")]
    lon_cols = [c for c in df.columns if c.lower() in ("lon", "lng", "longitude")]
    if lat_cols and lon_cols:
        return lat_cols[0], lon_cols[0]
    return None, None


def main():
    st.title("GEO_IA — Demo Dashboard")

    # Load secrets (Streamlit Cloud) or env vars
    api_key_secret = None
    try:
        api_key_secret = st.secrets.get("GDRIVE_API_KEY")
    except Exception:
        api_key_secret = None

    sa_json = None
    try:
        sa_json = st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    except Exception:
        sa_json = None

    # support base64-encoded JSON secret
    sa_b64 = None
    try:
        sa_b64 = st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON_BASE64")
    except Exception:
        sa_b64 = None

    # If service account JSON provided as secret (raw JSON or base64), write to temp file and set env var
    if sa_b64:
        try:
            import base64

            decoded = base64.b64decode(sa_b64)
            sa_text = decoded.decode("utf-8")
        except Exception:
            sa_text = None
    else:
        sa_text = sa_json

    if sa_text:
        sa_path = os.path.join(tempfile.gettempdir(), "service_account.json")
        with open(sa_path, "w", encoding="utf-8") as f:
            f.write(sa_text)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = sa_path

    st.sidebar.header("Source")
    mode = st.sidebar.selectbox("Carregar a partir de", ["Upload local", "Links (Drive share)", "Pasta do Drive (API key)"])

    files = {}

    if mode == "Upload local":
        uploaded = st.sidebar.file_uploader("Envie um ou mais JSON", accept_multiple_files=True, type=['json'])
        if uploaded:
            for f in uploaded:
                files[f.name] = f.read()

    elif mode == "Links (Drive share)":
        text = st.sidebar.text_area("Cole links de compartilhamento do Drive (um por linha)")
        if st.sidebar.button("Carregar links"):
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                fid = extract_id_from_share_url(line)
                try:
                    b = download_public_file(fid)
                    files[f"{fid}.json"] = b
                except Exception as e:
                    st.sidebar.error(f"Erro ao baixar {line}: {e}")

    else:
        folder_url = st.sidebar.text_input("Cole a URL da pasta do Drive")
        # prefer secret if present
        api_key_input = st.sidebar.text_input("(Opcional) API Key do Google", type="password", value=api_key_secret or "")
        api_key = api_key_input if api_key_input else api_key_secret
        if st.sidebar.button("Listar arquivos na pasta"):
            if not folder_url:
                st.sidebar.error("Cole a URL da pasta do Drive")
            elif not api_key:
                st.sidebar.error("Forneça uma API Key do Google")
            else:
                fid = extract_id_from_share_url(folder_url)
                try:
                    items = list_folder_files(fid, api_key)
                    # include JSON and HDF5 files
                    choices = {f['name']: f['id'] for f in items if f['name'].lower().endswith(('.json', '.h5', '.hdf5'))}
                    pick = st.sidebar.multiselect("Escolha arquivos (JSON / HDF5)", list(choices.keys()))
                    for name in pick:
                        b = download_public_file(choices[name])
                        files[name] = b
                except Exception as e:
                    st.sidebar.error(f"Erro listando pasta: {e}")

    if not files:
        st.info("Forneça arquivos JSON (upload, links ou pasta) para começar")
        return

    st.sidebar.header("Arquivos carregados")
    sel = st.sidebar.selectbox("Escolha um arquivo", list(files.keys()))
    
    if not sel:
        return
    
    content = files[sel]

    # If HDF5 file selected, handle separately
    if sel.lower().endswith('.h5') or sel.lower().endswith('.hdf5'):
        # write bytes to temp file
        with tempfile.NamedTemporaryFile(suffix='.h5', delete=False) as tmp:
            if isinstance(content, bytes):
                tmp.write(content)
            else:
                # content may be a stream-like
                try:
                    tmp.write(content.read())
                except Exception:
                    tmp.write(bytes(content))
            tmp_path = tmp.name

        st.header(f"HDF5 file: {sel}")

        def list_datasets(h5file):
            datasets = []
            def visitor(name, obj):
                if isinstance(obj, h5py.Dataset):
                    datasets.append(name)
            h5file.visititems(visitor)
            return datasets

        try:
            with h5py.File(tmp_path, 'r') as f:
                ds = list_datasets(f)
                st.write('Grupos / datasets encontrados:')
                st.write(ds)
                if ds:
                    pick = st.selectbox('Escolha dataset para visualizar', ds)
                    if pick and pick in f:
                        dataset = f[pick]
                        if isinstance(dataset, h5py.Dataset):
                            arr = dataset[()]
                        else:
                            st.error("Item selecionado não é um dataset")
                            return
                    else:
                        st.error("Dataset não encontrado")
                        return
                    st.write('Shape:', getattr(arr, 'shape', None), 'dtype:', getattr(arr, 'dtype', None))
                    # If 1D or 2D numeric array, show head as table
                    if isinstance(arr, (np.ndarray,)):
                        if arr.ndim == 1:
                            df = pd.DataFrame(arr, columns=[pick.split('/')[-1]])
                            st.dataframe(df.head(100))
                        elif arr.ndim == 2:
                            df = pd.DataFrame(arr)
                            st.dataframe(df.head(100))
                        else:
                            st.write('Dataset with more than 2 dimensions; showing a small slice:')
                            sample = arr.reshape(arr.shape[0], -1)[:100]
                            st.dataframe(pd.DataFrame(sample))
                    else:
                        st.write('Tipo de dataset não suportado para preview.')
        except Exception as e:
            st.error(f'Erro lendo HDF5: {e}')
        return

    try:
        df = load_json_bytes(content)
    except Exception as e:
        st.error(f"Erro lendo JSON: {e}")
        return

    st.header(f"Análise: {sel}")
    show_basic_analysis(df)

    st.subheader("Visualizações")
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

    if numeric_cols:
        st.write("**Numéricos**")
        ncol = st.selectbox("Escolha coluna numérica", numeric_cols, key='num')
        fig = px.histogram(df, x=ncol, nbins=50, title=f'Histograma — {ncol}')
        st.plotly_chart(fig, use_container_width=True)

    if cat_cols:
        st.write("**Categóricos**")
        ccol = st.selectbox("Escolha coluna categórica", cat_cols, key='cat')
        vc = df[ccol].value_counts().iloc[:30]
        fig2 = px.bar(x=vc.index.astype(str), y=vc.values, title=f'Top categorias — {ccol}')
        st.plotly_chart(fig2, use_container_width=True)

    # time series
    time_cols = [c for c in df.columns if 'date' in c.lower() or 'time' in c.lower()]
    if time_cols:
        tcol = st.selectbox("Coluna de tempo detectada", time_cols, key='time')
        try:
            s = pd.to_datetime(df[tcol], errors='coerce')
            df['_time_'] = s
            if df['_time_'].notna().any() and numeric_cols:
                xcol = st.selectbox("Agregue série por", numeric_cols, key='series')
                res = df.dropna(subset=['_time_', xcol]).set_index('_time_').resample('D')[xcol].count()
                fig3 = px.line(res.reset_index(), x=res.index, y=res.values, title=f'Série diária — {xcol}')
                st.plotly_chart(fig3, use_container_width=True)
        except Exception:
            pass

    lat, lon = detect_latlon(df)
    if lat and lon:
        st.subheader('Mapa (lat / lon detectados)')
        map_df = df.dropna(subset=[lat, lon])[[lat, lon]].rename(columns={lat: 'lat', lon: 'lon'})
        st.map(map_df)
        figmap = px.scatter_geo(df.dropna(subset=[lat, lon]), lat=lat, lon=lon, hover_name=cat_cols[0] if cat_cols else None)
        st.plotly_chart(figmap, use_container_width=True)

    st.sidebar.header("Exportar")
    if st.sidebar.button("Baixar CSV do arquivo selecionado"):
        todownload = df.to_csv(index=False).encode('utf-8')
        st.sidebar.download_button("Download CSV", data=todownload, file_name=sel.replace('.json', '.csv'))

    st.markdown("---")
    st.write("**Ajuda / notas**: Use a opção de `Pasta do Drive` com uma API Key se quiser listar automaticamente arquivos no diretório. Para arquivos públicos pequenos, cole o link de compartilhamento e o app tentará baixar direto.")


if __name__ == '__main__':
    main()
