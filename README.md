🚗 GEO_IA: Monitoramento de Tráfego - Foz do Iguaçu
Este é um dashboard interativo desenvolvido com Streamlit para visualização e análise de dados de tráfego em tempo real e históricos da cidade de Foz do Iguaçu. O projeto integra dados do Waze armazenados no Google Drive para gerar insights sobre mobilidade urbana.

🌟 Funcionalidades Atualizadas
Mapa de Incidentes: Visualização georreferenciada de acidentes, vias fechadas e perigos usando folium.

Mapa de Congestionamento: Escala dinâmica de cores (Verde para livre, Vermelho para parado) baseada na velocidade real das vias.

Indicadores de Performance (KPIs): Painéis que mostram a velocidade média da cidade, temperatura e um índice de gravidade dos incidentes.

Filtros Inteligentes: Filtragem por data (calendário), intervalo de horários, tipo de alerta e busca por nome de rua.

Sincronização com Google Drive: Carregamento automático de arquivos .h5 (HDF5) via Service Account do Google Cloud.

Auto-Refresh: O dashboard se atualiza automaticamente a cada 10 minutos para refletir o estado atual do trânsito.

🚀 Como Executar o Projeto
1. Requisitos de Ambiente
Para evitar erros de memória (malloc ou segmentation fault), este projeto requer Python 3.11 ou 3.12.

Bash
# No terminal (Codespace ou Local)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
2. Configuração de Credenciais
O app utiliza o sistema de Secrets do Streamlit. Crie um arquivo .streamlit/secrets.toml e adicione suas credenciais do Google Cloud:

Ini, TOML
[gcp_service_account]
type = "service_account"
project_id = "seu-projeto-id"
private_key = "-----BEGIN PRIVATE KEY-----\nSUA_CHAVE\n-----END PRIVATE KEY-----\n"
client_email = "seu-email-da-service-account@..."
# ... preencha com os demais campos do seu JSON original
3. Rodar o Dashboard
Bash
streamlit run streamlit_app.py
🛠️ Tecnologias e Bibliotecas
Interface: Streamlit

Mapas: Folium & Streamlit-Folium

Análise de Dados: Pandas, NumPy e PyTables (para arquivos .h5)

Gráficos: Plotly Express

Nuvem: Google Drive API v3

⚠️ Notas Técnicas de Estabilidade
Durante o desenvolvimento no GitHub Codespaces e Streamlit Cloud, aplicamos as seguintes correções de estabilidade:

Versão do Python: Forçada para 3.11 através do arquivo .python-version para evitar conflitos com o motor HDF5 em versões experimentais.

Gerenciamento de Memória: Configurado OPENBLAS_NUM_THREADS = 1 para prevenir erros de segmentação em ambientes de container.

Compatibilidade NumPy: O projeto utiliza numpy < 2.0.0 para garantir que a leitura de arquivos binários .h5 seja estável.

📂 Estrutura do Repositório
streamlit_app.py: Código principal do dashboard.

requirements.txt: Lista de dependências Python.

.python-version: Define a versão estável do interpretador para o deploy.

GEO_IA/: Pasta raiz do workspace no Codespaces.

Desenvolvido para análise geoespacial de tráfego. 🛰️🚦
