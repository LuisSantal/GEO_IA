FROM python:3.11-slim
WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*

# copy sources
COPY . /app

# install python deps
RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8501

ENV PORT=8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.port", "${PORT}", "--server.address", "0.0.0.0"]
