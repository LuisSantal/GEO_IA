# 🚦 GEO_IA: Sistema de Suporte à Decisão e Auditoria de Infraestrutura Viária — Foz do Iguaçu

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge.svg)](https://wazefoz.streamlit.app/)
[![License: MIT](https://img.shields.shields.shields.org/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.shields.io/badge/Python-3.11%20%7C%203.12-blue)](https://www.python.org/downloads/)

> **GEO_IA** é a arquitetura algorítmica e computacional *open-source* implantada na plataforma web **WazeFoz** ([wazefoz.streamlit.app](https://wazefoz.streamlit.app/)). O sistema opera como um Sistema de Apoio à Decisão (SAD) voltado à gestão de ativos viários, mapeamento de estrangulamentos de fluxo e comprovação técnica de prioridades para intervenções físicas e engenharia geométrica em Foz do Iguaçu (PR).

***

## 🏛️ Vínculo Institucional e Fomento

Este projeto é desenvolvido no âmbito do **Plano de Trabalho PID4021-2025**, programa de bolsas de iniciação científica do **CNPq**, intitulado:

> *"Exploração de Dados Disponíveis na Plataforma Waze Partner Hub para Análise de Mobilidade Urbana"*

| Diretriz | Informações Estruturais do Projeto |
|---|---|
| **Bolsista** | Luis Enrique Santacruz Alvarez |
| **Orientador** | Prof. Diego Moraes Flores |
| **Coorientador** | Prof. Dr. Ricardo Morel Hartmann |
| **Instituição** | [Universidade Federal da Integração Latino-Americana (UNILA)](https://portal.unila.edu.br) |
| **Instituto** | [ILATIT — Instituto Latino-Americano de Tecnologia, Infraestrutura e Território](https://portal.unila.edu.br/institutos/ilatit) |
| **Grande Área** | Ciências Exatas e da Terra / Geociências — Geocartografia |
| **Suporte** | [LACA — Laboratório de Computação Aplicada](https://divulga.unila.edu.br/laca/) (Itaipu Parquetec) |
| **Coordenadores LACA** | Profs. Joylan Nunes Maciel, Willian Zalewski e Marcelo Kapp |
| **Status** | 🟡 Em andamento |

***

## 🎯 Objetivos do Projeto

O projeto realiza a extração, normalização e reprocessamento matemático dos fluxos massivos do programa **Waze for Cities Data** (antigo *Waze Partner Hub*) para compreender os padrões de mobilidade urbana em regiões transfronteiriças. Os objetivos específicos são:

- 📌 **Mapeamento de Dados:** Estruturar os schemas de dados geoespaciais disponíveis (alertas pontuais e retenções lineares).
- 📊 **Auditoria Funcional:** Identificar padrões de congestionamento crônicos e eixos de estresse estrutural na malha.
- 🗺️ **Visualização Avançada:** Desenvolver interfaces cartográficas interativas de alta fidelidade para interpretação ágil de gargalos.
- 🤖 **Tomada de Decisão Científica:** Implementar algoritmos de análise multicritério (MCDA) e modelos preditivos de engenharia de tráfego.

***

## 🌍 Aplicações Práticas dos Resultados

Como uma plataforma de código aberto, o sistema fornece insumos quantitativos para diferentes esferas:

- 🏙️ **Gestão Pública de Trânsito** — Embasamento técnico e comprovação de prioridades para intervenções geométricas, semafóricas e sinalização.
- 🏗️ **Planejamento de Infraestrutura Viária** — Identificação de trechos em fadiga operacional para justificar duplicações e recapeamento asfáltico.
- 🎓 **Pesquisa Acadêmica** — Modelagem e análise de séries temporais aplicadas à mobilidade pendular internacional na Tríplice Fronteira.
- 📦 **Logística e Segurança** — Otimização de eixos logísticos com base no impacto de atraso acumulado e taxas de acidentes.

***

## 🌟 Funcionalidades e Arquitetura do SAD

### 🗺️ Camadas Cartográficas Dinâmicas (Módulo Descritivo)
- **Mapa de Incidentes:** Georreferenciamento de sinistros, obras e perigos na via com marcadores coloridos por nível de criticidade e popups geoespaciais detalhados via Folium.
- **Mapa de Congestionamentos:** Renderização linear dos segmentos viários com escala dinâmica de saturação baseada na velocidade real aferida (🟢 livre $\rightarrow$ 🔴 travado).
- **Mapa de Calor:** Superfície contínua de Densidade de Kernel para delimitação geoestatística de *hotspots* críticos.
- **Controles Integrados:** Captura de posição do cursor em tempo real, botão fullscreen e bounding box restrita estritamente às coordenadas do município de Foz do Iguaçu ($[-25.70, -25.40]$ Lat, $[-54.75, -54.45]$ Lon).

### 📊 Análise de Criticidade Viária Multicritério (Módulo Analítico MCDA)
Algoritmo de suporte à decisão que roda no backend (`calculate_road_criticism`) combinando o **volume acumulado de congestionamentos** e o **atraso médio em segundos** para gerar o **Índice de Criticidade ($I_{crit}$)** por logradouro viário, rankeando o nível de urgência de investimentos estruturais:

$$I_{crit} = \left( \left( \frac{V_{via}}{V_{max}} \times 0.4 \right) + \left( \frac{A_{via}}{A_{max}} \times 0.6 \right) \right) \times 100$$

* $V_{via}$ / $V_{max}$: Frequência volumétrica de retenções da via em relação ao pico registrado na malha urbana global.
* $A_{via}$ / $A_{max}$: Severidade temporal (atraso médio em segundos) do trecho em relação ao limite máximo observado.

### 🔮 Módulo Computacional Preditivo de Impacto Temporal

#### Seção 1 — Simulador de Atraso por Extensão de Fila
Modelo matemático inferencial calibrado estatisticamente com dados históricos locais que estima o atraso acumulado esperado ($D_{pred}$, em segundos) com base exclusiva no comprimento espacial della fila de congestionamento ($L$, em metros):

$$D_{pred} = (L \times 0.15) + 12.0$$

* Inclui controle deslizante interativo (*slider* de 50 m a 5.000 m) para simulação de cenários proativos e testes de estresse viário.

#### Seção 2 — Matriz de Propensão Via × Dia da Semana
Processamento estatístico contínuo sobre o banco histórico bruto que identifica quais vias têm maior propensão probabilística ao congestionamento em cada dia da semana. Exibido através de um mapa de calor adiacional bidimensional (YlOrRd do Plotly Express), revelando de forma inédita que os gargalos aduaneiros locais concentram-se nas **quintas-feiras e sábados**.

#### Seção 3 — Comparador Mensal Interanual (2025 vs. 2026)
Ferramenta analítica longitudinal para validação de impacto de políticas públicas anteriores, cruzando dados sob múltiplos parâmetros:

| Filtro e Controle | Descrição de Operação |
|---|---|
| **Ano A / Ano B** | Seleção pareada dos anos históricos presentes nas bases binárias. |
| **Dia da Semana** | Isolamento de tendências para dias específicos (ex: comportamento apenas aos Sábados). |
| **Categorias** | Multiselect estruturado por tipologia (ACIDENTE, CONGESTIONAMENTO, PERIGO, VIA FECHADA). |

Gera automaticamente curvas de linha sobrepostas de evolução macroscópica mensal, grades de barras segregadas por categoria de incidentes e indicadores gráficos de variação percentual ($\Delta\%$) mensal.

### 🔍 Filtros Inteligentes e Ingestão em Nuvem
- Filtragem temporal responsiva por calendário e sliders de horários (0h às 23h).
- Sincronização em tempo real com o Google Drive via Google Drive API v3 (Service Account GCP).
- Suporte à leitura de arquivos binários de Big Data HDF5 (`.h5`) com desduplicação automática em tempo de execução baseada no identificador único universal (`UUID`) de alertas e congestionamentos.
- Ciclos automáticos de atualização (*Auto-Refresh*) a cada 10 minutos com cache inteligente de recursos.

***

## 🚀 Como Executar o Projeto Localmente

### 1. Preparação do Ambiente Virtual
Para prevenir falhas de compilação em dependências C e estouros de memória, utilize estritamente o interpretador **Python 3.11**:

```bash
# Clonar o repositório
git clone [https://github.com/LuisSantal/GEO_IA.git](https://github.com/LuisSantal/GEO_IA.git)
cd GEO_IA

# Instanciar e ativar o ambiente virtual
python3.11 -m venv .venv
source .venv/bin/activate       # No Linux/macOS
.venv\Scripts\activate          # No Windows

# Instalar dependências travadas
pip install -r requirements.txt
