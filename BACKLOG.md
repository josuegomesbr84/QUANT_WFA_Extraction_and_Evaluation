# BACKLOG — WFA Extractor (BotSpot)

Histórico completo de entregas desde o início do projeto.

---

## 🏗️ FASE 1 — Estrutura Base e Pipeline de Extração

- ✅ Definição da arquitetura do projeto (pastas, módulos, stack tecnológica)
- ✅ `scraper/auth.py` — Login no botspot.com.br via Playwright sync API
- ✅ `scraper/upload.py` — Upload do arquivo `.wfa` e aguardo do redirect para `/wfareport`
- ✅ `scraper/extractor.py` — Extração DOM: cards de indicadores, tabela WFA, parâmetros frequentes
- ✅ `scraper/extractor.py` — Extração de dados ApexCharts via injeção de JavaScript (`window.Apex._chartInstances`)
- ✅ `scraper/extractor.py` — Seleção de cenários via dropdown Bootstrap (click + wait spinner)
- ✅ `scraper/extractor.py` — Extração do Z-Score via popup "Mais > Distribuição"
- ✅ `scraper/extractor.py` — Detecção dinâmica de labels de cenário no DOM
- ✅ `scraper/runner.py` — Orquestração completa da extração (login → upload → WFM → cenários)
- ✅ `analysis/metrics.py` — Cálculo de representatividade por step
- ✅ `analysis/metrics.py` — Detecção de steps negativos consecutivos e detecção de ano negativo
- ✅ `analysis/metrics.py` — Cálculo de WFE médio e WFE médio sem outliers (método IQR)
- ✅ `analysis/metrics.py` — Percentual de steps com WFE positivo
- ✅ `analysis/verdict.py` — Sistema de pontuação por critério e veredicto (APROVADO / ATENÇÃO / REPROVADO)
- ✅ `analysis/verdict.py` — Veredicto global baseado na distribuição dos cenários
- ✅ `output/json_writer.py` — Serialização completa do resultado em JSON com timestamp
- ✅ `output/html_report.py` — Geração de relatório HTML via template Jinja2
- ✅ `output/templates/report.html.j2` — Template self-contained com CSS inline
- ✅ `config.py` — Centralização de URLs, timeouts, seletores e parâmetros de scoring
- ✅ `.env` / `.env.example` — Gerenciamento seguro de credenciais
- ✅ `requirements.txt` — Dependências do projeto

---

## 🔧 FASE 2 — Correção Crítica: Playwright Sync API

- ✅ Migração de `async_playwright` + `asyncio.run()` para `sync_playwright`
  - Motivo: `NotImplementedError` em threads secundárias no Windows (SelectorEventLoop)
  - Arquivos: `runner.py`, `auth.py`, `upload.py`, `extractor.py`
- ✅ `app.py` — Servidor FastAPI com SSE (Server-Sent Events) para progress em tempo real
- ✅ `app.py` — Thread separada para execução do scraper sem bloquear o event loop do uvicorn

---

## 🎨 FASE 3 — Interface Web (UI)

- ✅ `templates/index.html` — Interface web completa (upload, log em tempo real, resultado)
- ✅ `templates/index.html` — Tema escuro (dark mode) com toggle 🌙/☀️ e persistência via `localStorage`
- ✅ `WFA_Extractor.bat` — Arquivo batch para iniciar o servidor com duplo clique
- ✅ `templates/index.html` — Painel "⚙ Critérios de Avaliação" colapsável com campos editáveis
  - 6 critérios editáveis: Representatividade, Consecutivos, WFE%, Z-Score, WFE Médio, WFE s/ Outliers
  - Thresholds de veredicto editáveis (APROVADO / ATENÇÃO)
  - Persistência dos valores editados via `localStorage`
- ✅ `app.py` — Recebimento de `scoring_config` e `veredicto_thresholds` via FormData (JSON)
- ✅ `runner.py` — Repasse de configs dinâmicas para `calcular_veredicto`
- ✅ `analysis/verdict.py` — Suporte a configuração dinâmica de scoring como parâmetro opcional

---

## 📊 FASE 4 — Novas Colunas na Tabela WFA do Relatório

- ✅ `analysis/metrics.py` — `detect_wfe_outliers()`: detecção de outliers de WFE pelo método IQR
- ✅ `analysis/metrics.py` — `compute_all_metrics()`: passa a aceitar `oos_equity_steps` opcional
- ✅ `scraper/extractor.py` — `extract_oos_equity_steps()`: busca valores R$ OOS por step nos charts ApexCharts
- ✅ `scraper/runner.py` — Integração: extrai `oos_equity_steps` do gráfico e passa para métricas
- ✅ `output/templates/report.html.j2` — 3 novas colunas na tabela interna de cada cenário:
  - **Equity OOS (R$)** — valor financeiro real por step (do gráfico de barras)
  - **Rep. %** — representatividade de cada step sobre o equity final
  - **Outlier WFE** — badge ⚠ para steps com WFE fora do intervalo IQR
- ✅ `output/templates/report.html.j2` — Cabeçalho "CAGR / AVG DD" acima de In Sample / Out of Sample

---

## 📐 FASE 5 — Substituição da Métrica de Representatividade

- ✅ `analysis/metrics.py` — Nova fórmula: `rep_step = |OOS_step| / |equity_final_total|`
  - Denominador fixo = soma de todos os steps (não mais acumulado até o step)
  - Elimina artefato: step 1 não dá mais sempre 100%
- ✅ `analysis/metrics.py` — `calc_representatividade()` retorna `max_representatividade`, `equity_final`, `detalhes[]`
- ✅ `config.py` — Nova estrutura de scoring com campo `maximo` e penalidade:
  - ≤ 25% → +20 pts
  - ≤ 30% → +8 pts
  - > 30% → **−20 pts** (penalidade — pontuação total pode ficar negativa)
- ✅ `analysis/verdict.py` — Helper `_score_por_maximo()` para scoring com faixas por máximo
- ✅ `analysis/verdict.py` — `calcular_veredicto()` usa `max_representatividade * 100` com as novas faixas
- ✅ `output/templates/report.html.j2` — Chip atualizado: "Máx. Rep. / Equity Final"
- ✅ `templates/index.html` — Painel de critérios: 3 faixas editáveis de representatividade (`rep_f1_max`, `rep_f1_pts`, `rep_f2_max`, `rep_f2_pts`, `rep_f3_pts`)

---

## 🐛 FASE 6 — Correções em Andamento: Equity OOS (R$)

- ✅ `analysis/metrics.py` — Adicionado `oos_rep_values` ao retorno de `compute_all_metrics` (valores usados como numerador na representatividade)
- ✅ `output/templates/report.html.j2` — Coluna Equity OOS usa `c.oos_equity_steps` (mostra `—` se gráfico não encontrado)
- ✅ `scraper/extractor.py` — `_coerce_apex_numeric()`: suporte a formatos dict `{x,y}` e tupla `[ts,val]`
- ✅ `scraper/extractor.py` — `extract_oos_equity_steps()`: prioridade por nome ("oos") > tipo ("bar") > outros
- ✅ `scraper/extractor.py` — `get_chart_data()`: 3 estratégias de acesso às instâncias ApexCharts
- ✅ `scraper/runner.py` — Log de debug quando extração do gráfico falha (salva JSON bruto)
- ✅ `scraper/runner.py` — `headless=False` para acompanhamento visual da execução
- ✅ `scraper/extractor.py` — `extract_oos_via_hover()`: extração via dispatch de `MouseEvent('mousemove')` no SVG via `page.evaluate()`
  - Abordagem: JavaScript despacha eventos diretamente no SVG (não depende do viewport)
  - ApexCharts atualiza tooltip sincronamente — leitura imediata sem sleep
  - Salva `resultados/debug_tooltips.txt` com tooltips brutos por step
- 🔄 **Coluna Equity OOS (R$) ainda exibindo `—`** — extração via JS mousemove dispatch implementada, aguardando validação

---

## 📋 PENDENTE / BACKLOG FUTURO

- ⬜ Voltar `headless=True` após confirmar funcionamento da extração de Equity OOS
- ⬜ Remover código de debug (`debug_tooltips.txt`, `debug_chart_data_cenario_0.json`) após validação
- ⬜ Validar cálculo de representatividade com valores R$ reais (atualmente usa CAGR/AVG DD como fallback)
- ⬜ Testar extração end-to-end com múltiplos arquivos `.wfa` (diferentes números de steps/cenários)
- ⬜ Histórico de extrações: listar relatórios anteriores na UI
- ⬜ Campo "Estratégia" com persistência entre sessões

---

## 🗂️ Arquivos do Projeto

| Arquivo | Responsabilidade |
|---|---|
| `app.py` | Servidor FastAPI + SSE + rotas |
| `config.py` | Parâmetros globais, scoring, timeouts |
| `main.py` | Entry point CLI |
| `WFA_Extractor.bat` | Inicialização com duplo clique |
| `scraper/auth.py` | Login BotSpot |
| `scraper/upload.py` | Upload `.wfa` |
| `scraper/extractor.py` | Extração DOM + ApexCharts + hover |
| `scraper/runner.py` | Orquestração completa |
| `analysis/metrics.py` | Cálculo de todas as métricas |
| `analysis/verdict.py` | Scoring e veredicto |
| `output/json_writer.py` | Exportação JSON |
| `output/html_report.py` | Geração do relatório HTML |
| `output/templates/report.html.j2` | Template do relatório |
| `templates/index.html` | Interface web |
