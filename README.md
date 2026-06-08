# 🚦 GEO_IA: Sistema de Suporte à Decisão em Mobilidade Urbana — Foz do Iguaçu


> Dashboard interativo para visualização, análise e **suporte à decisão** em tempo real e histórico de tráfego urbano em Foz do Iguaçu — PR, integrando dados do **Waze for Cities**, algoritmos **multicritério (MCDA)** e **modelos preditivos** de impacto viário.

***

## 🏛️ Vínculo Institucional

Este projeto é desenvolvido no âmbito do **Plano de Trabalho PID4021-2025**, programa de bolsas de iniciação científica **CNPq**, intitulado:

> *"Exploração de Dados Disponíveis na Plataforma Waze Partner Hub para Análise de Mobilidade Urbana"*

| | |
|---|---|
| **Bolsista** | Luis Enrique Santacruz Alvarez |
| **Orientador** | Prof. Diego Moraes Flores |
| **Coorientador** | Prof. Dr. Ricardo Morel Hartmann |
| **Instituição** | [Universidade Federal da Integração Latino-Americana (UNILA)](https://portal.unila.edu.br) |
| **Instituto** | [ILATIT — Instituto Latino-Americano de Tecnologia, Infraestrutura e Território](https://portal.unila.edu.br/institutos/ilatit) |
| **Grande Área / Área** | Ciências Exatas e da Terra / Geociências — Geocartografia |
| **Status** | 🟡 Em andamento |

O projeto também conta com suporte do **Laboratório de Pesquisa em Computação Aplicada (LACA/UNILA)**, coordenado pelos professores Joylan Nunes Maciel, Willian Zalewski e Marcelo Kapp, localizado no Itaipu Parquetec — [LACA](https://divulga.unila.edu.br/laca/).

***

## 🎯 Objetivos do Projeto

O projeto propõe a exploração aprofundada dos dados da plataforma **Waze Partner Hub** para compreender padrões de mobilidade urbana e propor aplicações práticas. Os objetivos específicos são:

- 📌 Mapear os tipos de dados disponíveis no Waze Partner Hub (tráfego, incidentes, rotas, etc.)
- 📊 Identificar padrões de congestionamento e eventos recorrentes
- 🗺️ Desenvolver visualizações que facilitem a interpretação dos dados
- 🤖 Aplicar algoritmos de análise multicritério (MCDA) e modelos preditivos à gestão viária
- 🏛️ Propor aplicações para gestores públicos e empresas de transporte

***

## 🌍 Aplicações dos Dados

O projeto é **open source** e voltado para qualquer pessoa ou organização interessada em mobilidade urbana. Algumas das possíveis aplicações:

- 🏙️ **Gestão pública de trânsito** — apoio à tomada de decisão sobre sinalização, rotas alternativas e planejamento viário
- 🎓 **Pesquisa acadêmica** — estudos de mobilidade em cidades de fronteira e análise de séries temporais de tráfego
- 🏗️ **Planejamento urbano** — identificação de pontos críticos para obras e melhorias de infraestrutura
- 🚑 **Segurança pública** — análise georreferenciada de acidentes para ações preventivas
- 📦 **Logística e entregas** — otimização de rotas com base em dados históricos de congestionamento
- 🗺️ **Turismo e mobilidade regional** — mapeamento de fluxos em uma das cidades mais visitadas do Brasil

***

## 🌟 Funcionalidades

### 🗺️ Mapas Interativos
- **Mapa de Incidentes** — visualização georreferenciada de acidentes, vias fechadas e perigos, com marcadores coloridos por severidade e popups detalhados via Folium.
- **Mapa de Congestionamentos** — escala dinâmica de cores (🟢 livre → 🔴 parado) baseada na velocidade real medida nas vias.
- **Mapa de Calor** — densidade espacial de ocorrências por região da cidade, com legendas interpretativas de criticidade.
- **Controles de Mapa** — posição do mouse em tempo real, botão de tela cheia e bounding box restrito ao município de Foz do Iguaçu.

### 📊 Análise de Dados e KPIs
- **Indicadores de Performance (KPIs)** — total de alertas, congestionamentos ativos, velocidade média da rede e gargalo operacional prioritário.
- **Gráficos Interativos** — distribuição temporal por hora, frequência por tipo de alerta, ranking de vias críticas por dia da semana e evolução histórica via Plotly.
- **Dados Detalhados** — tabelas filtráveis com todos os registros brutos, exportáveis em CSV para alertas e congestionamentos separadamente.

### 🤖 Módulo de Suporte à Decisão (SAD / MCDA)

#### 📊 Análise de Criticidade Viária (MCDA)
Algoritmo multicritério que combina **volume de congestionamentos** e **atraso médio em segundos** para gerar um **Índice de Criticidade (0–100)** por logradouro, permitindo priorização de intervenções urbanas:

```
Criticidade = (Volume_Jams / max_volume) × 0.4 + (Atraso_Médio / max_delay) × 0.6
```

- Ranking interativo das Top 10 vias com maior índice de criticidade
- Tabela estruturada com volume de retenções, atraso médio e índice geral
- Destinado ao apoio de decisões da **Foztrans** e planejadores urbanos

#### 🔮 Modelo Preditivo de Impacto Temporal

**Seção 1 — Simulador de Atraso por Extensão de Fila:**
Regressão linear calibrada com dados históricos do dataset WazeFoz que estima o atraso veicular (em minutos) a partir da extensão espacial de uma retenção viária:

```
Atraso (s) = Comprimento (m) × 0.15 + 12
```

- Slider interativo de 50 m a 5.000 m
- Curva de regressão com ponto de cenário atual destacado
- Métrica em tempo real exibindo o atraso estimado

**Seção 2 — Propensão por Via e Dia da Semana:**
Análise histórica completa (independente do filtro de data) que identifica quais vias têm maior propensão ao congestionamento em cada dia da semana:

- **Heatmap Via × Dia** — matriz colorida (YlOrRd) com % de ocorrências históricas por via e dia
- **Filtro por dia** — selectbox para rankear as 10 vias mais críticas em um dia específico
- **Tabela "Pior Dia por Via"** — identifica automaticamente o dia da semana mais crítico por logradouro

**Seção 3 — Comparador Mensal 2025 vs 2026:**
Ferramenta de análise comparativa interanual com os seguintes controles e visualizações:

| Controle | Descrição |
|---|---|
| Ano A / Ano B | Seleciona os dois anos a comparar (detectado automaticamente no dataset) |
| Dia da Semana | Filtra ocorrências por dia específico (ex: somente Sextas-feiras) |
| Categorias | Multiselect com ACIDENTE, CONGESTIONAMENTO, PERIGO, VIA FECHADA, ALERTA, etc. |

Gráficos gerados automaticamente:

| Visualização | O que mostra |
|---|---|
| **Linha comparativa** | Evolução total mês a mês dos dois anos sobrepostos |
| **Barras por categoria** | Grade com painel individual para cada tipo de incidente |
| **Variação % mês a mês** | Barras 🟢 (redução) e 🔴 (aumento) por mês |
| **Tabela resumo** | Mês / Ano A / Ano B / Δ (%) exportável |

### 🔍 Filtros Inteligentes
- Filtragem por **data** (calendário interativo)
- Filtragem por **intervalo de horário** (slider 0–23h)
- Filtragem por **tipo de alerta** (acidente, obra, perigo, etc.)
- Os módulos preditivos e de comparação temporal utilizam o **histórico completo** para maior relevância estatística

### ☁️ Integração com Nuvem
- Sincronização automática com **Google Drive** via Service Account do Google Cloud
- Suporte a **duas pastas de dados simultâneas** (alertas e congestionamentos) com deduplicação automática por UUID
- Carregamento de arquivos `.h5` (HDF5) com dados históricos e em tempo real
- **Auto-Refresh** a cada 10 minutos com cache de recursos e dados independentes

***

## 🚀 Como Executar o Projeto

### 1. Pré-requisitos

> ⚠️ Para evitar erros de memória (`malloc` ou `segmentation fault`), este projeto requer **Python 3.11 ou 3.12**.

```bash
# Criar e ativar ambiente virtual
python -m venv .venv

source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate         # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 2. Configuração de Credenciais

O app utiliza o sistema de **Secrets do Streamlit**. Crie o arquivo `.streamlit/secrets.toml` com suas credenciais do Google Cloud:

```toml
[gcp_service_account]
type = "service_account"
project_id = "seu-projeto-id"
private_key_id = "seu-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nSUA_CHAVE\n-----END PRIVATE KEY-----\n"
client_email = "sua-service-account@seu-projeto.iam.gserviceaccount.com"
client_id = "seu-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
```

> 💡 O arquivo `.json` da Service Account pode ser obtido no [Google Cloud Console](https://console.cloud.google.com/).

### 3. Rodar o Dashboard

```bash
streamlit run streamlit_app.py
```

Acesse em: `http://localhost:8501`

***

## 🛠️ Tecnologias e Bibliotecas

| Categoria | Tecnologia |
|---|---|
| Interface | [Streamlit](https://streamlit.io) |
| Mapas | [Folium](https://python-visualization.github.io/folium/) & [streamlit-folium](https://folium.streamlit.app/) |
| Análise de Dados | [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/) |
| Armazenamento | [PyTables](https://www.pytables.org/) (arquivos `.h5` / HDF5) |
| Gráficos | [Plotly Express](https://plotly.com/python/plotly-express/) |
| Nuvem | [Google Drive API v3](https://developers.google.com/drive/api/v3/about-sdk) |
| Algoritmos | MCDA Ponderado, Regressão Linear Inferencial, Análise de Propensão Histórica |
| Fonte de Dados | [Waze for Cities](https://www.waze.com/wazeforcities/) |

***

## 📂 Estrutura do Repositório

```
GEO_IA/
│
├── streamlit_app.py          # Código principal do dashboard (7 blocos)
├── requirements.txt          # Dependências Python
├── .python-version           # Versão estável do interpretador (3.11)
│
├── .streamlit/
│   └── secrets.toml          # Credenciais Google Cloud (não versionar!)
│
└── README.md
```

### Arquitetura do `streamlit_app.py`

O código está organizado em **7 blocos funcionais**:

| Bloco | Conteúdo |
|---|---|
| **Bloco 1** | Configuração base do app, CSS global, variáveis de sessão e timezone |
| **Bloco 2** | Conexão Google Drive, ingestão HDF5, normalização de timestamps, extração de coordenadas e tradução PT-BR |
| **Bloco 3** | Mapas Folium com plugins (MousePosition, Fullscreen), geração de mapas de incidentes e congestionamentos |
| **Bloco 4** | Sidebar, filtros interativos e carregamento global de dados |
| **Upgrade SAD** | Funções MCDA (`calculate_road_criticism`) e modelo preditivo (`predict_traffic_delay_impact`) |
| **Bloco 5** | Cabeçalho, KPIs e indicadores dinâmicos |
| **Bloco 6** | 7 abas de visualização: Incidentes, Congestionamentos, Mapa de Calor, Gráficos, Criticidade MCDA, Modelo Preditivo, Dados |
| **Bloco 7** | Rodapé institucional com logotipos e créditos |

***

## ⚠️ Notas Técnicas de Estabilidade

Durante o desenvolvimento no **GitHub Codespaces** e **Streamlit Cloud**, foram aplicadas as seguintes correções de estabilidade:

| Aspecto | Configuração Aplicada |
|---|---|
| Versão Python | Fixada em `3.11` via arquivo `.python-version` |
| Memória OpenBLAS | `OPENBLAS_NUM_THREADS=1` para prevenir segfaults em containers |
| Compatibilidade NumPy | `numpy < 2.0.0` para leitura estável de arquivos `.h5` binários |
| Cache de dados | `@st.cache_data(ttl=600)` para alertas e congestionamentos com TTL de 10 min |
| Cache de recursos | `@st.cache_resource` para o cliente Google Drive API |

***

## 🤝 Parcerias

- **Foztrans** — Empresa de Transporte e Trânsito de Foz do Iguaçu
- **Guarda Municipal de Foz do Iguaçu** — Programa Vida no Trânsito
- **CNPq** — Conselho Nacional de Desenvolvimento Científico e Tecnológico

***

## 📚 Referências

- Waze Partner Hub. (2025). *Waze Partner Hub Documentation*. Disponível em: [https://www.waze.com/partner-hub](https://www.waze.com/partner-hub)
- Banister, D. (2008). The sustainable mobility paradigm. *Transport Policy*, 15(2), 73–80.
- Goodchild, M. F. (2007). Citizens as sensors: The world of volunteered geography. *GeoJournal*, 69(4), 211–221.
- Zhang, L., et al. (2011). Big data for urban transportation. *IEEE Intelligent Transportation Systems Magazine*, 3(4), 22–32.
- Bucsky, P. (2020). Crowdsourced traffic data. *Transportation Research Part A*, 137, 385–397.
- Gonzalez, H., et al. (2008). Adaptive real-time traffic prediction using Waze data. *Transportation Research Part C*, 16(6), 673–695.
- Herrera, J. C., et al. (2010). Evaluation of traffic data via GPS-enabled mobile phones. *Transportation Research Part C*, 18(4), 568–583.
- Hwang, C. L., & Yoon, K. (1981). *Multiple Attribute Decision Making: Methods and Applications*. Springer-Verlag.

***

## 📄 Licença

Este projeto está licenciado sob a [MIT License](LICENSE).

***

*Desenvolvido para análise geoespacial e suporte à decisão em tráfego urbano. 🛰️🚦*  
*Universidade Federal da Integração Latino-Americana (UNILA) — Foz do Iguaçu, PR, Brasil.*
