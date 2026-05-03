# WFA Extractor — BotSpot

> Automação de extração e avaliação de estratégias Walk Forward Analysis (WFA) do BotSpot.com.br.

---

## Changelog

### v1.3.0 — 2026-05-03
- **Enfileirador de WFAs (batch)** — selecione múltiplos arquivos `.wfa` e o sistema processa em sequência reaproveitando o mesmo browser/login (ganho ~30s por arquivo)
- **Lista visual da fila** — cada arquivo aparece com badge de status (⏸/🔄/✅/❌) e input editável para o nome da estratégia
- **Resiliência** — falha em um arquivo não interrompe o lote; UI mostra ❌ com tooltip da mensagem
- **Análise Global reformulada** — substitui o badge categórico (APROVADO/REPROVADO/ATENÇÃO) pelo comentário OOS como destaque; cor reflete o tom da análise (verde se há OOS bom, vermelho se nenhum se destacou)
- **Breakdown por OOS no veredicto global** — contagem de aprovados/atenção/reprovados agrupados por período OOS, com insight automático identificando quais OOS tiveram melhor desempenho
- Novo endpoint `POST /extrair-batch` (legado `/extrair` preservado)
- Eventos SSE adicionais: `batch_start`, `batch_file_start`, `batch_file_done`, `batch_file_error`, `batch_done`

### v1.2.0 — 2026-05-02
- **Regras de veto por cenário** — 5 condições que forçam REPROVADO independentemente da pontuação:
  - Mais de 2 steps com representatividade > 30% (concentração de lucro)
  - Z-Score < 2,5
  - Ano negativo detectado (sequência de steps OOS negativos cobrindo ≥ 12 meses)
  - WFE s/ Outliers < 50%
  - WFE Médio < 50%
- **Badges de veto** visíveis na tabela de cenários e no detalhe expansível (relatório HTML e UI)
- **Veredicto Global reformulado**: comentário agora exibe `x WFC(s) reprovados por [motivo]` por regra de veto disparada — omitido quando nenhuma regra dispara

### v1.1.3 — 2026-05-01
- **Pontuação máxima reequilibrada para 100 pts** — seis critérios principais passam a valer até 15 pts cada, e Significância permanece com até 10 pts
- Defaults da UI e do backend alinhados ao novo total: `15 + 15 + 15 + 15 + 15 + 15 + 10 = 100`
- `localStorage` dos critérios versionado para `wfa-criterios-v3`, evitando reaproveitar pesos antigos salvos no navegador

### v1.1.2 — 2026-05-01
- **Critérios padrão atualizados conforme painel de avaliação** — faixas de `% Steps WFE Positivo`, `Z-Score`, `WFE Médio`, `WFE s/ Outliers` e `Steps Negativos Consecutivos` alinhadas aos novos defaults
- **Penalidades negativas liberadas na UI** — campos de pontuação editáveis aceitam valores como `-20`, `-15`, `-13` e `-12`
- **Casas decimais nos thresholds/faixas** — inputs numéricos usam `step="any"` onde necessário, incluindo `2.7`, `2.49` e `49.9`
- `localStorage` dos critérios versionado para `wfa-criterios-v2`, evitando reaproveitar defaults antigos salvos no navegador

### v1.1.1 — 2026-05-01
- **Correção crítica: botão "Iniciar Extração" travado** — chave `'média':` sem aspas no JS causava erro de parse silencioso no script inteiro; o submit handler nunca registrava e o botão permanecia desabilitado para sempre
- `app.py` → header `Cache-Control: no-store` na rota `/` para garantir que o browser sempre busque o HTML mais recente
- `templates/index.html` → removido atributo `disabled` do botão; botão agora sempre habilitado com validação de arquivo no submit handler (mensagem amigável se clicar sem arquivo)
- `analysis/metrics.py` → normalização de "Média" → "media" (remoção de acento) antes do lookup no dict de scoring
- `config.py` → alias `"média"` removido; mantido apenas `"media"` (sem acento) para consistência

### v1.1.0 — 2026-04-30
- **Critério Significância** adicionado ao sistema de scoring (Alta = +10 pts, Média = +5, Baixa = −5) — pontuação máxima passa de 100 → 110 pts
- **Timer de execução** na UI: contador ⏱ MM:SS iniciado automaticamente após o login
- **Botão Reiniciar Servidor** (🔄) sem perder a URL — reinicia o processo Python via `os.execv()`
- **Card "Equity Total OOS"** no relatório HTML por cenário (quando R$ reais disponíveis)
- **Veredicto Global reformulado**: exibe % de WFCs aprovados e comentário contextual indicando a melhor configuração de período OOS
- **Seletor de número máximo de cenários** para modo teste (evita esperar todas as 12 iterações)

### v1.0.0 — 2026-04-28
- Versão inicial: extração completa, 6 critérios de scoring, relatório HTML/JSON, interface web com dark mode, critérios editáveis

---

## Índice

- [O que é este projeto?](#o-que-é-este-projeto)
- [Para Usuários — Início Rápido](#para-usuários--início-rápido)
  - [Pré-requisitos](#pré-requisitos)
  - [Configuração inicial](#configuração-inicial)
  - [Como usar](#como-usar)
  - [Entendendo a Interface](#entendendo-a-interface)
  - [Sistema de Pontuação](#sistema-de-pontuação)
  - [Interpretando os Resultados](#interpretando-os-resultados)
- [Para Desenvolvedores](#para-desenvolvedores)
  - [Instalação do Ambiente](#instalação-do-ambiente)
  - [Estrutura de Arquivos](#estrutura-de-arquivos)
  - [Arquitetura e Fluxo de Execução](#arquitetura-e-fluxo-de-execução)
  - [Módulos](#módulos)
  - [API REST](#api-rest)
  - [Configuração Avançada](#configuração-avançada)
  - [Como Estender](#como-estender)
  - [Decisões de Arquitetura](#decisões-de-arquitetura)

---

## O que é este projeto?

O **WFA Extractor** automatiza uma tarefa que antes era feita manualmente: avaliar se uma estratégia de trading (Expert Advisor) passou no teste Walk Forward Analysis (WFA) no site BotSpot.com.br.

### O problema que resolve

Após rodar uma WFA no BotSpot, o trader precisa navegar por até 12 cenários diferentes, anotar métricas como Z-Score e WFE, calcular médias e tirar conclusões. Esse processo leva 20–40 minutos por estratégia e é propenso a erro humano.

### O que a ferramenta faz

1. Faz login automático no BotSpot
2. Envia o arquivo `.wfa` e aguarda o processamento
3. Navega pelos 12 cenários automaticamente
4. Extrai todos os dados relevantes de cada cenário
5. Calcula 7 critérios de avaliação com pontuação máxima de 100 pontos
6. Emite um veredicto (**APROVADO / ATENÇÃO / REPROVADO**) por cenário e global
7. Gera relatórios HTML e JSON prontos para revisão

Todo o processo — que levaria ~30 minutos manual — é concluído de forma automática.

---

## Para Usuários — Início Rápido

### Pré-requisitos

| Requisito | Versão mínima | Como verificar |
|---|---|---|
| Python | 3.11+ | `python --version` |
| Google Chrome | qualquer | instalado no sistema |

Você também precisa de uma conta ativa em [botspot.com.br](https://botspot.com.br).

---

### Configuração inicial

**Passo 1 — Instalar dependências** (faça apenas uma vez)

Abra o Prompt de Comando na pasta do projeto e execute:

```cmd
pip install -r requirements.txt
playwright install chromium
```

**Passo 2 — Configurar credenciais**

Crie um arquivo chamado `.env` na pasta do projeto com o seguinte conteúdo:

```env
BOTSPOT_EMAIL=seu@email.com
BOTSPOT_PASSWORD=suasenha
```

> ⚠️ **Nunca compartilhe este arquivo.** Ele contém sua senha e já está configurado para ser ignorado pelo Git.

---

### Como usar

**Opção A — Duplo clique (recomendado)**

Clique duas vezes no arquivo `WFA_Extractor.bat`. Uma janela do terminal abrirá e o servidor iniciará automaticamente. Após a mensagem `Uvicorn running`, acesse:

```
http://127.0.0.1:8000
```

**Opção B — Terminal**

```cmd
python app.py
```

**No navegador:**

1. Arraste ou selecione **um ou mais** arquivos `.wfa` (drag-and-drop suporta múltiplos)
2. Para cada arquivo da fila, edite o **Nome da Estratégia** se desejar (padrão: nome do arquivo sem extensão)
3. (Opcional) Ajuste os critérios de avaliação no painel **⚙ Critérios de Avaliação**
4. Clique em **▶ Iniciar Lote**
5. Acompanhe a fila em tempo real — cada arquivo mostra ⏸ pendente / 🔄 rodando / ✅ concluído / ❌ erro
6. Ao concluir, cada arquivo gera seu próprio relatório HTML/JSON acessível pelo link na fila

> O processamento pode levar de **5 a 15 minutos por arquivo**. O browser e o login são reaproveitados entre arquivos — ganho de ~30s por arquivo no lote.

> Se um arquivo falhar, o lote continua com os próximos. O arquivo com problema fica marcado com ❌ e o erro pode ser inspecionado via tooltip.

---

### Entendendo a Interface

#### Área de Upload e Fila
- Arraste **um ou mais** arquivos `.wfa` (ou clique para selecionar múltiplos)
- Cada arquivo gera uma linha na fila com: badge de status, nome do arquivo, input editável de estratégia e botão de remover
- A estratégia é auto-preenchida com o nome do arquivo (sem `.wfa`); você pode editar antes de iniciar
- Os relatórios saem nomeados como `Avalia_WFA_[estrategia]_[timestamp].html`

#### Credenciais
- Se configurou o `.env`, deixe em branco
- Pode informar manualmente clicando em "🔑 Informar credenciais manualmente"

#### Critérios de Avaliação
- Painel colapsável com todos os 7 critérios e seus pesos
- Edite os valores para personalizar o rigor da avaliação
- Clique em **💾 Salvar como padrão** para persistir suas preferências no navegador
- Os valores padrão seguem as melhores práticas de avaliação WFA

#### Barra de Progresso e Log
- Atualizada em tempo real via Server-Sent Events (SSE)
- Cada cenário aparece com seu status (aguardando → processando → veredicto)

#### Tema Escuro
- Botão 🌙 / ☀️ no canto superior direito
- Preferência salva automaticamente no navegador

---

### Sistema de Pontuação

Cada cenário recebe uma pontuação de **0 a 100 pontos**, distribuída em 7 critérios:

| Critério | Peso Máx | O que mede |
|---|---|---|
| Representatividade por step | 15 pts | Se algum step isolado contribui mais de 25% do equity total — sinal de resultado concentrado em poucos trades |
| Steps negativos consecutivos | 15 pts | Sequências de períodos OOS negativos — quanto maior e mais longa, pior |
| % Steps com WFE positivo | 15 pts | Proporção de steps onde a estratégia foi lucrativa fora da amostra |
| Z-Score | 15 pts | Significância estatística dos resultados (quão improvável seria o desempenho por acaso) |
| WFE Médio | 15 pts | Média do Walk Forward Efficiency — relação entre lucro IS e OOS |
| WFE sem outliers (IQR) | 15 pts | Mesma média, porém com outliers removidos — mede consistência |
| **Significância WFM** | **10 pts** | Nível de significância categórico exibido na Walk Forward Matrix (Alta / Média / Baixa) |

#### Faixas de pontuação padrão

**Representatividade**
| Situação | Pontos |
|---|---|
| Máx. rep. ≤ 25% | 15 |
| Máx. rep. ≤ 30% | 6 |
| Máx. rep. > 30% | −15 |

**Steps Negativos Consecutivos**
| Situação | Pontos |
|---|---|
| Nenhum par negativo | 15 |
| 1 par curto (< 12 meses) | 9 |
| 1 par longo (≥ 12 meses / ano negativo) | −15 |
| 2 ou mais pares negativos | 0 |

**% Steps WFE Positivo**
| Mínimo | Pontos |
|---|---|
| ≥ 70% | 15 |
| ≥ 65% | 8 |
| ≥ 50% | 4 |
| ≥ 49% | −15 |
| < 49% | 0 |

**Z-Score**
| Mínimo | Pontos |
|---|---|
| ≥ 3,0 | 15 |
| ≥ 2,7 | 7 |
| ≥ 2,5 | 5 |
| ≥ 2,49 | −15 |
| < 2,49 | 0 |

**WFE Médio**
| Mínimo | Pontos |
|---|---|
| ≥ 70% | 15 |
| ≥ 65% | 8 |
| ≥ 50% | 5 |
| ≥ 49,9% | −15 |
| < 49,9% | 0 |

**WFE sem Outliers**
| Mínimo | Pontos |
|---|---|
| ≥ 70% | 15 |
| ≥ 65% | 12 |
| ≥ 50% | 9 |
| ≥ 49,9% | −15 |
| < 49,9% | 0 |

**Significância WFM**
| Nível | Pontos |
|---|---|
| Alta | +10 |
| Média | +5 |
| Baixa | −5 (penalidade) |
| Não disponível | 0 |

#### Veredicto por cenário

| Pontuação Total | Veredicto |
|---|---|
| ≥ 75 pts | ✅ APROVADO |
| 50 – 74 pts | ⚠️ ATENÇÃO |
| < 50 pts | ❌ REPROVADO |

> **Regras de veto:** independentemente da pontuação, o cenário é automaticamente **REPROVADO** se qualquer uma das condições abaixo for verdadeira:
> - Mais de 2 steps com representatividade > 30% (concentração de lucro excessiva)
> - Z-Score < 2,5 (ausência de significância estatística mínima)
> - Ano negativo detectado (≥ 12 meses consecutivos OOS negativos)
> - WFE s/ Outliers < 50%
> - WFE Médio < 50%
>
> Os relatórios indicam o motivo do veto com o badge 🚫.

#### Veredicto global

Baseado na distribuição dos 12 cenários:
- Mais de 50% APROVADO → **APROVADO**
- 50% ou mais REPROVADO → **REPROVADO**
- Demais casos → **ATENÇÃO**

O comentário global lista quantos WFCs foram reprovados por cada regra de veto (apenas as regras que dispararam são exibidas).

---

### Interpretando os Resultados

#### Por cenário (badge na tabela WFM)
**APROVADO** — A estratégia demonstrou robustez estatística consistente naquele cenário (combinação Steps/IS/OOS).

**ATENÇÃO** — Resultados mistos. Pode funcionar mas apresenta pontos de fragilidade.

**REPROVADO** — Não demonstrou robustez suficiente. Pode estar marcado também por **regras de veto** (badge 🚫) — Z-Score baixo, ano negativo, concentração de lucro, WFE médio ou s/ outliers fraco.

#### Análise Global (no topo do relatório)
- **Comentário de adaptação**: identifica em quais períodos OOS a estratégia teve mais aprovados que reprovados (ex: *"Sua estratégia parece se adaptar melhor nos períodos OOS 4 e 5"*)
- **Cor de fundo**: verde se há OOS com bom desempenho, vermelho se *nenhum* OOS apresentou maioria de aprovações (caso em que recomenda-se revisar a estratégia)
- **Breakdown por OOS**: contagem aprovado/atenção/reprovado agrupada por período
- **Vetos por regra**: lista 📌 com quantos WFCs caíram em cada regra de veto (Z-Score, concentração, ano negativo, WFE)

> Os relatórios gerados ficam em `resultados/` com o formato `Avalia_WFA_[nome]_[timestamp].html` e `.json`.

---

## Para Desenvolvedores

### Instalação do Ambiente

```bash
# Clone ou copie o projeto
cd Extraçao_WFA

# Crie um ambiente virtual (recomendado)
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

# Instale as dependências
pip install -r requirements.txt

# Instale o Chromium (browser headless)
playwright install chromium

# Configure credenciais
copy .env.example .env
# Edite .env com suas credenciais
```

**Iniciar em modo desenvolvimento (com reload automático):**

```bash
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

---

### Estrutura de Arquivos

```
Extraçao_WFA/
│
├── app.py                      # Servidor FastAPI — entry point web
├── config.py                   # URLs, timeouts e configuração de scoring
├── main.py                     # Entry point CLI (uso sem servidor web)
├── WFA_Extractor.bat           # Atalho Windows para iniciar o servidor
├── requirements.txt
├── .env                        # Credenciais (não versionar)
│
├── templates/
│   └── index.html              # Interface web (SPA vanilla JS + SSE)
│
├── scraper/
│   ├── auth.py                 # Login no BotSpot via Playwright
│   ├── upload.py               # Upload do .wfa e navegação para /wfareport
│   ├── extractor.py            # Extração DOM: cenários, cards, Z-Score, ApexCharts
│   └── runner.py               # Orquestra todo o fluxo de extração
│
├── analysis/
│   ├── metrics.py              # Cálculo das métricas analíticas (WFE, IQR, etc.)
│   └── verdict.py              # Lógica de pontuação e veredictos
│
├── output/
│   ├── json_writer.py          # Serializa resultado em JSON
│   ├── html_report.py          # Gera relatório HTML via Jinja2
│   └── templates/
│       └── report.html.j2      # Template Jinja2 do relatório detalhado
│
└── resultados/                 # Saída dos relatórios (criado automaticamente)
```

---

### Arquitetura e Fluxo de Execução

O sistema tem duas camadas: o **servidor web** (FastAPI + SSE) e o **scraper** (Playwright sync API em thread separada).

```
Browser (cliente)
    │
    │  POST /extrair  (multipart: .wfa + credenciais + scoring_config)
    ▼
app.py (FastAPI — uvicorn event loop)
    │
    ├─ Salva .wfa em tmp/{job_id}.wfa
    ├─ Parse JSON de scoring_config e veredicto_thresholds
    ├─ Cria asyncio.Queue para SSE
    └─ Inicia _run_background (BackgroundTask assíncrona)
           │
           ├─ Cria threading.Queue (sync_q) — bridge entre threads
           ├─ Inicia Thread(target=_thread_target)
           │       │
           │       └─ runner.run_with_progress()          ← thread separada
           │              │
           │              ├─ sync_playwright → Chromium (headless)
           │              ├─ auth.login()
           │              ├─ upload.send_wfa()             ← aguarda até 15 min
           │              ├─ extractor.get_wfm()           ← Walk Forward Matrix
           │              ├─ extractor.get_scenario_labels()
           │              └─ Para cada cenário (0 a N-1):
           │                     ├─ extractor.select_scenario()  (dropdown Bootstrap)
           │                     ├─ extractor.get_scenario_data()
           │                     │       ├─ Cards (meses, anos, OOS negativos)
           │                     │       ├─ Z-Score (Mais → DISTRIBUIÇÃO → popup)
           │                     │       └─ Tabela WFA do cenário
           │                     ├─ extractor.get_chart_data()   (ApexCharts JS injection)
           │                     ├─ metrics.compute_all_metrics()
           │                     └─ verdict.calcular_veredicto()
           │                            └─ push({"type": "scenario_done", ...})
           │
           └─ Bridge loop: sync_q → asyncio.Queue (a cada 150ms)

    │  GET /stream/{job_id}  (EventSource SSE)
    ▼
app.py → StreamingResponse (text/event-stream)
    │
    └─ Cada msg da asyncio.Queue → "data: {...}\n\n"

Browser (cliente)
    └─ handleEvent(msg) → atualiza UI em tempo real
```

#### Por que Playwright Sync API em thread separada?

No Windows, o `SelectorEventLoop` padrão do Python não suporta criação de subprocessos (que o Playwright precisa para iniciar o Chromium). A solução é:

1. **`WindowsProactorEventLoopPolicy`** no topo de `app.py` (antes do uvicorn criar seu loop)
2. **`sync_playwright`** (API síncrona) rodando em uma thread daemon — zero conflito com o event loop do uvicorn
3. **Bridge** `threading.Queue → asyncio.Queue` para comunicar resultados ao SSE

---

### Módulos

#### `config.py`

Fonte de verdade para todas as configurações estáticas:

```python
BASE_URL = "https://botspot.com.br"
TIMEOUTS = {
    "upload": 900_000,       # 15 min (WFA pode levar 5-10 min para processar)
    "page_load": 45_000,
    "scenario_switch": 45_000,
    "spinner_appear": 5_000,
}
SCORING = { ... }            # Faixas de pontuação por critério
VEREDICTO_THRESHOLDS = { ... }
```

Os valores de `SCORING` e `VEREDICTO_THRESHOLDS` são os **defaults**. A UI permite sobrescrevê-los por extração sem alterar este arquivo.

---

#### `scraper/auth.py`

Login via Playwright. Suporta variações de seletores (`[name="email"]`, `[type="email"]`) para robustez contra mudanças no front-end do BotSpot.

---

#### `scraper/upload.py`

1. Navega para `/wfa`
2. Injeta o arquivo no input oculto do Dropzone.js via `set_input_files`
3. Clica em "Enviar"
4. Aguarda a SPA React mudar a URL para `/wfareport` via `wait_for_function` — necessário porque React usa `history.pushState` (o evento `load` nunca dispara)

---

#### `scraper/extractor.py`

Módulo mais complexo. Funções principais:

| Função | Descrição |
|---|---|
| `get_wfm(page)` | Extrai a Walk Forward Matrix (tabela fixa com todos os cenários) |
| `get_scenario_labels(page)` | Abre o dropdown Bootstrap para forçar render dos itens, lê todos os labels |
| `get_current_scenario_label(page)` | Lê o cenário já carregado (texto do botão toggle) |
| `select_scenario(page, label)` | Abre dropdown, clica no item pelo texto, aguarda spinner sumir |
| `get_scenario_data(page)` | Extrai cards, Z-Score (via Mais→DISTRIBUIÇÃO→popup), tabela WFA |
| `get_chart_data(page)` | Injeção JS em `window.Apex._chartInstances` para extrair dados dos gráficos |

**Extração do Z-Score** (fluxo em 5 etapas):
```
click "Mais" → click "DISTRIBUIÇÃO" → aguarda popup → regex Z-Score → press Escape
```

**Seletor de cenários** — os itens são `<a class="dropdown-item" role="button">` (Bootstrap 5). O React só os renderiza no DOM quando o dropdown está aberto, por isso é necessário abrir antes de ler.

---

#### `analysis/metrics.py`

Funções puras de cálculo (sem side effects, fáceis de testar):

| Função | Descrição |
|---|---|
| `parse_currency(str)` | Converte `"R$ 1.234,56"` → `1234.56` |
| `parse_percentage(str)` | Converte `"72,5%"` → `72.5` |
| `calc_representatividade(oos_values)` | `\|step_oos\| / \|equity_acumulado\|` por step |
| `calc_consecutivos_negativos(oos_values, meses_por_step)` | Detecta grupos de 2+ negativos consecutivos |
| `calc_wfe_sem_outliers(wfe_values)` | Média após remoção de outliers pelo método IQR (1.5×IQR) |
| `calc_pct_wfe_positivo(wfe_values)` | % de steps com WFE > 0 |
| `compute_all_metrics(scenario_data, meses_total)` | Agrega todas as métricas |

---

#### `analysis/verdict.py`

```python
def calcular_veredicto(metrics: dict, scoring=None, thresholds=None) -> dict:
    """
    scoring  → sobrescreve config.SCORING (enviado pela UI)
    thresholds → sobrescreve config.VEREDICTO_THRESHOLDS
    Se None, usa os defaults de config.py.
    """
```

Retorna:
```python
{
    "scores": {
        "representatividade": 15,
        "consecutivos_negativos": 9,
        "pct_steps_positivos": 8,
        "zscore": 7,
        "wfe_medio": 8,
        "wfe_sem_outliers": 12,
        "significancia": 10,
    },
    "total": 69,
    "veredicto": "ATENÇÃO"
}
```

---

#### `output/json_writer.py` e `output/html_report.py`

Ambos aceitam `estrategia: str = ""` para nomear o arquivo:

```python
save(result, estrategia="Venus3_EURUSD_H1")
# → resultados/Avalia_WFA_Venus3_EURUSD_H1_20260429_143022.json
```

Caracteres inválidos no Windows são removidos automaticamente. Espaços viram `_`.

---

### API REST

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Serve a interface web (`templates/index.html`) |
| `POST` | `/extrair` | Inicia extração. Retorna `{"job_id": "uuid"}` |
| `GET` | `/stream/{job_id}` | Stream SSE com eventos de progresso |
| `GET` | `/resultados/*` | Serve arquivos estáticos da pasta `resultados/` |
| `GET` | `/test-sse` | Diagnóstico: envia 3 eventos SSE e encerra |

#### POST `/extrair` — parâmetros (multipart/form-data)

| Campo | Tipo | Descrição |
|---|---|---|
| `wfa_file` | File | Arquivo `.wfa` |
| `email` | string | E-mail BotSpot (opcional se .env configurado) |
| `password` | string | Senha BotSpot (opcional se .env configurado) |
| `estrategia` | string | Nome da estratégia para nomear arquivos de saída |
| `scoring_config` | JSON string | Configuração customizada de pontuação |
| `veredicto_thresholds` | JSON string | Thresholds customizados de veredicto |

#### Eventos SSE

```javascript
// Tipos de eventos emitidos pelo /stream/{job_id}
{ type: "log",           msg: "string" }
{ type: "progress_init", total: 12 }
{ type: "scenario_start", index: 0, label: "Steps: 14 - IS: 12 - OOS: 3", total: 12 }
{ type: "scenario_done",  index: 0, label: "...", veredicto: "APROVADO",
                          total_pts: 78, scores: {...}, metrics: {...}, wfm_row: {...} }
{ type: "done",           veredicto_global: "APROVADO", json_path: "...",
                          html_path: "...", arquivo: "...",
                          aprovados: 8, atencao: 3, reprovados: 1 }
{ type: "error",          msg: "string", detail: "traceback" }
{ type: "ping" }          // keepalive a cada 120s
```

---

### Configuração Avançada

#### Timeouts (`config.py`)

```python
TIMEOUTS = {
    "login":           15_000,   # 15s
    "upload":         900_000,   # 15 min — processamento do WFA
    "page_load":       45_000,   # 45s
    "scenario_switch": 45_000,   # 45s por cenário
    "spinner_appear":   5_000,   # aguarda spinner aparecer
}
```

Se o BotSpot estiver lento, aumente `upload` e `scenario_switch`.

#### Modo headed (debug visual)

Para ver o browser durante a execução, edite `scraper/runner.py`:

```python
browser = p.chromium.launch(headless=False)  # padrão: True
```

#### Variáveis de ambiente (`.env`)

```env
BOTSPOT_EMAIL=seu@email.com
BOTSPOT_PASSWORD=suasenha
```

---

### Como Estender

#### Adicionar um novo critério de pontuação

1. **`config.py`** — adicione a chave em `SCORING`:
```python
"novo_criterio": {
    "max": 10,
    "faixas": [
        {"minimo": 80.0, "pts": 10},
        {"minimo": 0.0,  "pts": 0},
    ]
}
```

2. **`analysis/metrics.py`** — adicione o cálculo em `compute_all_metrics`

3. **`analysis/verdict.py`** — adicione em `calcular_veredicto`:
```python
"novo_criterio": _score_por_minimo(metrics["novo_criterio"], sc["novo_criterio"]["faixas"]),
```

4. **`templates/index.html`** — adicione os inputs no painel de critérios e atualize `buildScoringConfig()` e `CRIT_IDS`

#### Extrair um novo campo do DOM

Adicione uma função em `scraper/extractor.py` seguindo o padrão das existentes — use `page.locator()`, `page.evaluate()` ou `page.get_by_text()`. Inclua try/except para robustez.

#### Modificar o template do relatório HTML

Edite `output/templates/report.html.j2`. É um template Jinja2 com acesso a todas as chaves do dicionário `result` (veja `runner.py` para a estrutura completa).

---

### Decisões de Arquitetura

| Decisão | Motivo |
|---|---|
| **Playwright Sync API** em vez de async | No Windows, `SelectorEventLoop` não suporta subprocessos. A sync API roda em threads normais sem conflito com o event loop do uvicorn |
| **`WindowsProactorEventLoopPolicy`** no topo de `app.py` | Deve ser definida antes de qualquer event loop ser criado — coloca o Proactor loop que suporta subprocessos no Windows |
| **threading.Queue → asyncio.Queue bridge** | Separa o mundo síncrono do Playwright do mundo assíncrono do FastAPI/SSE |
| **`wait_for_function` em vez de `wait_for_url`** | O BotSpot é uma SPA React com roteamento via `history.pushState`. O evento `load` nunca dispara após navegação client-side |
| **`set_input_files` no input oculto** | O Dropzone.js não abre o seletor nativo de arquivos — injeta via input oculto que o Dropzone já monitora |
| **Abrir dropdown antes de ler labels** | O React renderiza os itens do dropdown dinamicamente — eles só existem no DOM enquanto o menu está aberto |
| **Cenário 0 coletado sem interação** | O BotSpot já carrega um cenário automaticamente ao entrar em `/wfareport` — pular a seleção evita um ciclo desnecessário |

---

## Licença e Contato

Projeto aberto — Josue Gomes
