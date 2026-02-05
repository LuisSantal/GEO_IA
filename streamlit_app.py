import streamlit as st
import pandas as pd
import json
import io
import plotly.express as px
from datetime import datetime
from utils.drive_loader import extract_id_from_share_url, download_public_file, list_folder_files


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
        api_key = st.sidebar.text_input("(Opcional) API Key do Google", type="password")
        if st.sidebar.button("Listar arquivos na pasta"):
            if not folder_url:
                st.sidebar.error("Cole a URL da pasta do Drive")
            else:
                fid = extract_id_from_share_url(folder_url)
                try:
                    items = list_folder_files(fid, api_key)
                    choices = {f['name']: f['id'] for f in items if f['name'].lower().endswith('.json')}
                    pick = st.sidebar.multiselect("Escolha arquivos JSON", list(choices.keys()))
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
    content = files[sel]

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
