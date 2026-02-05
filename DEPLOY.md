# Deploy — GEO_IA Streamlit Dashboard

This file lists simple options to publish the `streamlit_app.py` online.

1) Streamlit Community Cloud (recommended, easiest)

- Push this repo to GitHub.
- Go to https://share.streamlit.io and sign in with GitHub.
- Click "New app" → select your repo, branch `master`, and entrypoint `streamlit_app.py`.
- Deploy. For public Drive access no extra secrets are required. To list private folder contents, add a Google API key in the app sidebar (use Streamlit secrets or paste in sidebar).

2) Docker (Railway / Render / any container host)

- Build locally:

```bash
docker build -t geo_ia_streamlit:latest .
docker run -p 8501:8501 geo_ia_streamlit:latest
```

- For cloud hosts, push the image to your registry and create a service exposing port `8501`.

3) Heroku (legacy, works with Procfile)

- Create an app: `heroku create your-app-name`.
- Push the repo (ensure `requirements.txt` and `Procfile` present):

```bash
git push heroku master
heroku ps:scale web=1
heroku open
```

4) Notes about Google Drive files

- Public files: the app downloads via the `uc?export=download&id=` URL and should work for public links.
- Folder listing: the Drive API requires an API key. You can paste the key in the sidebar or store in Streamlit secrets (`.streamlit/secrets.toml`) and read it in the app.

5) Next steps I can help with

- Create a GitHub Actions workflow to build and push Docker images.
- Prepare a ready-to-deploy branch and help connect Streamlit Cloud.
