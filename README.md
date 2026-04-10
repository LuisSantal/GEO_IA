# 🚗 GEO_IA: Monitoramento de Tráfego — Foz do Iguaçu

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red?logo=streamlit)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CAPES](https://img.shields.io/badge/Bolsista-CAPES-green)](https://www.gov.br/capes)

> Dashboard interativo para visualização e análise de dados de tráfego em tempo real e históricos da cidade de Foz do Iguaçu, integrando dados do **Waze for Cities** armazenados no Google Drive.

---

## 🏛️ Vínculo Institucional

Este projeto é desenvolvido no âmbito do **Plano de Trabalho PID4021-2025**, vinculado ao programa de bolsas de iniciação científica **CAPES**, intitulado:

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

---

## 🎯 Objetivos do Projeto

O projeto propõe a exploração aprofundada dos dados da plataforma **Waze Partner Hub** para compreender padrões de mobilidade urbana e propor aplicações práticas. Os objetivos específicos são:

- 📌 Mapear os tipos de dados disponíveis no Waze Partner Hub (tráfego, incidentes, rotas, etc.)
- 📊 Identificar padrões de congestionamento e eventos recorrentes
- 🗺️ Desenvolver visualizações que facilitem a interpretação dos dados
- 🏛️ Propor aplicações para gestores públicos e empresas de transporte

---

## 🌍 Aplicações dos Dados

O projeto é **open source** e voltado para qualquer pessoa ou organização interessada em mobilidade urbana. Algumas das possíveis aplicações:

- 🏙️ **Gestão pública de trânsito** — apoio à tomada de decisão sobre sinalização, rotas alternativas e planejamento viário
- 🎓 **Pesquisa acadêmica** — estudos de mobilidade em cidades de fronteira e análise de séries temporais de tráfego
- 🏗️ **Planejamento urbano** — identificação de pontos críticos para obras e melhorias de infraestrutura
- 🚑 **Segurança pública** — análise georreferenciada de acidentes para ações preventivas
- 📦 **Logística e entregas** — otimização de rotas com base em dados históricos de congestionamento
- 🗺️ **Turismo e mobilidade regional** — mapeamento de fluxos em uma das cidades mais visitadas do Brasil

---

## 🌟 Funcionalidades

### 🗺️ Mapas Interativos
- **Mapa de Incidentes** — visualização georreferenciada de acidentes, vias fechadas e perigos, com marcadores e popups detalhados via Folium.
- **Mapa de Congestionamentos** — escala dinâmica de cores (🟢 verde = livre → 🔴 vermelho = parado) baseada na velocidade real medida nas vias.
- **Mapa de Calor** — densidade espacial de ocorrências por região da cidade.
- **Rosa dos Ventos** — indicador de orientação geográfica integrado ao mapa.

### 📊 Análise de Dados
- **Indicadores de Performance (KPIs)** — velocidade média da cidade, temperatura e índice de gravidade dos incidentes.
- **Gráficos Interativos** — distribuição temporal de eventos, frequência por tipo de alerta e evolução histórica do tráfego via Plotly.
- **Dados Detalhados** — tabela filtrável com todos os registros brutos coletados.

### 🔍 Filtros Inteligentes
- Filtragem por **data** (calendário interativo)
- Filtragem por **intervalo de horário**
- Filtragem por **tipo de alerta** (acidente, obra, perigo, etc.)
- **Busca por nome de rua**

### ☁️ Integração com Nuvem
- Sincronização automática com **Google Drive** via Service Account do Google Cloud
- Carregamento de arquivos `.h5` (HDF5) com dados históricos e em tempo real
- **Auto-Refresh** a cada 10 minutos para refletir o estado atual do trânsito

---

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

---

## 🛠️ Tecnologias e Bibliotecas

| Categoria | Tecnologia |
|---|---|
| Interface | [Streamlit](https://streamlit.io) |
| Mapas | [Folium](https://python-visualization.github.io/folium/) & [streamlit-folium](https://folium.streamlit.app/) |
| Análise de Dados | [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/) |
| Armazenamento | [PyTables](https://www.pytables.org/) (arquivos `.h5` / HDF5) |
| Gráficos | [Plotly Express](https://plotly.com/python/plotly-express/) |
| Nuvem | [Google Drive API v3](https://developers.google.com/drive/api/v3/about-sdk) |
| Fonte de Dados | [Waze for Cities](https://www.waze.com/wazeforcities/) |

---

## 📂 Estrutura do Repositório

```
GEO_IA/
│
├── streamlit_app.py          # Código principal do dashboard
├── requirements.txt          # Dependências Python
├── .python-version           # Versão estável do interpretador (3.11)
│
├── .streamlit/
│   └── secrets.toml          # Credenciais Google Cloud (não versionar!)
│
└── README.md
```

---

## ⚠️ Notas Técnicas de Estabilidade

Durante o desenvolvimento no **GitHub Codespaces** e **Streamlit Cloud**, foram aplicadas as seguintes correções de estabilidade:

| Aspecto | Configuração Aplicada |
|---|---|
| Versão Python | Fixada em `3.11` via arquivo `.python-version` |
| Memória OpenBLAS | `OPENBLAS_NUM_THREADS=1` para prevenir segfaults em containers |
| Compatibilidade NumPy | `numpy < 2.0.0` para leitura estável de arquivos `.h5` binários |

---

## 🤝 Parcerias

- **Foztrans** — Empresa de Transporte e Trânsito de Foz do Iguaçu
- **Guarda Municipal de Foz do Iguaçu** — Programa Vida no Trânsito
- **CAPES** — Coordenação de Aperfeiçoamento de Pessoal de Nível Superior

---


## 📚 Referências

- Waze Partner Hub. (2025). *Waze Partner Hub Documentation*. Disponível em: https://www.waze.com/partner-hub
- Banister, D. (2008). The sustainable mobility paradigm. *Transport Policy*, 15(2), 73–80.
- Goodchild, M. F. (2007). Citizens as sensors: The world of volunteered geography. *GeoJournal*, 69(4), 211–221.
- Zhang, L., et al. (2011). Big data for urban transportation. *IEEE Intelligent Transportation Systems Magazine*, 3(4), 22–32.
- Bucsky, P. (2020). Crowdsourced traffic data. *Transportation Research Part A*, 137, 385–397.
- Gonzalez, H., et al. (2008). Adaptive real-time traffic prediction using Waze data. *Transportation Research Part C*, 16(6), 673–695.
- Herrera, J. C., et al. (2010). Evaluation of traffic data via GPS-enabled mobile phones. *Transportation Research Part C*, 18(4), 568–583.

## 📄 Licença

Este projeto está licenciado sob a [MIT License](LICENSE).

---

*Desenvolvido para análise geoespacial de tráfego urbano. 🛰️🚦*  
*Universidade Federal da Integração Latino-Americana (UNILA) — Foz do Iguaçu, PR, Brasil.*
