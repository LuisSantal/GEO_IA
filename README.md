# GEO_IA Dashboard

Demo Streamlit dashboard to load JSON files (local or Google Drive) and generate exploratory visualizations.

Quick start

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Run the app:

```bash
streamlit run streamlit_app.py
```

Notes
- If you want the app to list files inside a Drive folder automatically, create a Google API key and paste it in the sidebar.
- For public files the app will try to download via the `uc?export=download&id=` URL scheme.
