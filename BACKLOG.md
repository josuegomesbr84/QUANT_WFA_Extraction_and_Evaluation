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
  - 7 critérios editáveis: Representatividade, Consecutivos, WFE%, Z-Score, WFE Médio, WFE s/ Outliers, Significância
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

## 🐛 FASE 6 — Correções: Equity OOS (R$)

- ✅ `analysis/metrics.py` — Adicionado `oos_rep_values` ao retorno de `compute_all_metrics` (valores usados como numerador na representatividade)
- ✅ `output/templates/report.html.j2` — Coluna Equity OOS usa `c.oos_equity_steps` (mostra `—` se gráfico não encontrado)
- ✅ `scraper/extractor.py` — `_coerce_apex_numeric()`: suporte a formatos dict `{x,y}` e tupla `[ts,val]`
- ✅ `scraper/extractor.py` — `extract_oos_equity_steps()`: prioridade por nome ("oos") > tipo ("bar") > outros
- ✅ `scraper/extractor.py` — `get_chart_data()`: 3 estratégias de acesso às instâncias ApexCharts
- ✅ `scraper/runner.py` — Log de debug quando extração do gráfico falha (salva JSON bruto)
- ✅ `scraper/runner.py` — `headless=False` para acompanhamento visual da execução
- ✅ `scraper/extractor.py` — `extract_oos_via_hover()`: extração via `scrollIntoView` + `page.mouse.move()` com leitura de tooltip
- ✅ `scraper/extractor.py` — `extract_oos_via_svg_attrs()`: leitura direta do atributo `val` nos elementos `<path class="apexcharts-bar-area">` — abordagem mais robusta, sem depender de eventos
- ✅ `scraper/runner.py` — Pipeline de 3 tentativas para Equity OOS: SVG attrs → Apex config JS → hover

---

## ⚙️ FASE 7 — Modo Teste: Seletor de Cenários

- ✅ `templates/index.html` — Input numérico "Cenários:" ao lado do botão "▶ Iniciar Extração" (padrão 12, mín 1, máx 99)
- ✅ `app.py` — Parâmetro `max_cenarios: int = Form(0)` na rota `/extrair`, repassado até `run_with_progress`
- ✅ `scraper/runner.py` — Fatiamento de `all_labels[:max_cenarios]` antes do loop, com log de aviso

---

## 🚀 FASE 8 — v1.1.0: Novas Features (2026-04-30)

- ✅ **Timer de execução** — contador ⏱ MM:SS na UI iniciado ao receber "Login realizado" via SSE
  - `templates/index.html` — funções `startTimer()` / `stopTimer()`, elemento `#elapsed-timer`
  - Para automaticamente no `done` e no `error`

- ✅ **Significância como 7º critério de avaliação** — pontuação máxima: 100 → **110 pts**
  - `scraper/extractor.py` — campo `significancia` já extraído em `get_wfm()` (coluna do WFM)
  - `scraper/runner.py` — `wfm_row` extraído e armazenado no dict de cada cenário
  - `analysis/metrics.py` — `compute_all_metrics()` aceita `wfm_row`, extrai e normaliza `significancia` (lowercase)
  - `config.py` — novo critério `"significancia"` com `tipo: "categorico"` e pts por nível (Alta/Média/Baixa)
  - `analysis/verdict.py` — helper `_score_categorico()`, score incluído em `calcular_veredicto()`
  - `output/templates/report.html.j2` — chip "Significância" na metrics-row e score-item na scores-grid
  - `templates/index.html` — seção editável "Significância" com 3 inputs (Alta/Média/Baixa) no painel de critérios, com persistência `localStorage` e serialização em `buildScoringConfig()`

- ✅ **Botão Reiniciar Servidor (🔄)** — sem perder a URL
  - `app.py` — endpoint `POST /admin/restart` com `os.execv()`, bloqueado se houver jobs ativos
  - `templates/index.html` — botão fixo `right:62px`, polling automático até servidor voltar + `location.reload()`

- ✅ **Card "Equity Total OOS" no relatório** — exibido quando R$ reais disponíveis
  - `output/html_report.py` — filtro Jinja2 `fmt_currency` (formato R$ brasileiro)
  - `output/templates/report.html.j2` — chip `{% if c.oos_equity_steps %}` com `equity_final | fmt_currency`

- ✅ **Veredicto Global reformulado** — de string simples para dict rico
  - `analysis/verdict.py` — `veredicto_global()` retorna `{veredicto, pct_aprovados, contagem, comentario}`
  - `analysis/verdict.py` — `_gerar_comentario()`: agrupa cenários por OOS em meses, identifica melhor configuração
  - `scraper/runner.py` — push `"done"` envia dict completo (compatível com código existente)
  - `output/templates/report.html.j2` — exibe `pct_aprovados` e `comentario` no bloco veredicto-global
  - `templates/index.html` — `renderResults()` adaptado para dict, exibe % WFCs aprovados e insight 💡

- ✅ **README atualizado** — changelog v1.0.0/v1.1.0, tabela de scoring com 7 critérios/110 pts

- ✅ **Commit v1.1.0** — `git commit 4093761`

---

## 🐛 FASE 9 — v1.1.1: Correção Crítica do Botão "Iniciar Extração" (2026-05-01)

- ✅ **Correção JS: chave `'média':` causava erro de parse silencioso** — todo o `<script>` falhava em browsers (especialmente Edge) que rejeitam caracteres Unicode não-ASCII em nomes de propriedade sem aspas de objeto literal
  - `templates/index.html` — `buildScoringConfig()`: `'média':` substituído por `media:` (ASCII puro); `'default':` substituído por `def_pts:` (evita palavra reservada)
  - Impacto: `form.addEventListener('submit', ...)` nunca era registrado → botão permanecia desabilitado para sempre mesmo após seleção de arquivo

- ✅ **`app.py` — header `Cache-Control: no-store, no-cache, must-revalidate`** na rota `GET /` para garantir que o browser sempre busque o HTML mais recente do servidor (evita servir versão quebrada do cache mesmo após fix)

- ✅ **`templates/index.html` — removido atributo `disabled` do botão `#btn-run`** — botão agora sempre habilitado; validação de arquivo movida para o submit handler com mensagem de erro amigável ("Selecione um arquivo .wfa antes de iniciar a extração.") em vez de depender do evento `change` para habilitar o botão

- ✅ **`analysis/metrics.py` — normalização de significância**: `"Média"` → `"media"` (remoção de acento com `.replace("é", "e").replace("ê", "e")`) antes do lookup no dict de scoring

- ✅ **`config.py` — alias `"média"` removido** do `SCORING["significancia"]["pts"]`; mantido apenas `"media"` (sem acento) para consistência com a normalização do `metrics.py`

- ✅ **README atualizado** — changelog v1.1.1 adicionado

---

## ⚙️ FASE 10 — v1.1.2: Ajuste dos Defaults dos Critérios de Avaliação (2026-05-01)

- ✅ **`config.py` — defaults de scoring alinhados ao painel de avaliação**
  - `% Steps WFE Positivo`: 70/65/50/49 com pontuações `20/10/5/-20`
  - `Z-Score`: 3/2.7/2.5/2.49 com pontuações `15/7/5/-15`
  - `WFE Médio`: 70/65/50/49.9 com pontuações `13/7/4/-13`
  - `WFE s/ Outliers`: 70/65/50/49.9 com pontuações `12/10/7/-12`
  - `Steps Negativos Consecutivos`: 1 par longo / ano negativo passa de `4` para **`-20`**

- ✅ **`templates/index.html` — defaults visuais atualizados para bater com a imagem de referência**
  - Campos de pontuação editáveis aceitam penalidades negativas (`-20`, `-15`, `-13`, `-12`)
  - Campos numéricos relevantes usam `step="any"` para aceitar casas decimais como `2.7`, `2.49` e `49.9`
  - Chave de persistência dos critérios alterada para `wfa-criterios-v2`, evitando reaproveitar valores antigos do navegador

- ✅ **README atualizado** — changelog v1.1.2 e tabelas de scoring revisadas

---

## ⚖️ FASE 11 — v1.1.3: Pontuação Máxima Reequilibrada para 100 pts (2026-05-01)

- ✅ **`config.py` — pesos reequilibrados para total máximo de 100 pts**
  - Representatividade, Consecutivos Negativos, % WFE Positivo, Z-Score, WFE Médio e WFE s/ Outliers passam a valer até **15 pts** cada
  - Significância permanece valendo até **10 pts**
  - Total máximo: `15 + 15 + 15 + 15 + 15 + 15 + 10 = 100`

- ✅ **`templates/index.html` — painel de critérios atualizado**
  - Labels de máximo e defaults dos inputs ajustados para a nova escala
  - Barras de detalhamento dos scores por critério usam os novos máximos
  - Chave de persistência alterada para `wfa-criterios-v3`, evitando reaproveitar pesos antigos salvos no navegador

- ✅ **`output/templates/report.html.j2` — relatório HTML alinhado à escala de 100 pts**
  - Máximos exibidos nos cards de score atualizados para `/ 15 pts`
  - Cores dos scores individuais recalibradas para a nova escala

- ✅ **README atualizado** — changelog v1.1.3 e tabelas de scoring revisadas para 100 pts

---

## 🚦 FASE 10 — v1.2.0: Regras de Veto por Cenário (2026-05-02)

- ✅ **5 regras de veto** em `analysis/verdict.py` — `calcular_veredicto()` força `"REPROVADO"` independentemente da pontuação:
  - Mais de 2 steps com `representatividade > 30%` (concentração de lucro)
  - Z-Score < 2,5 (significância estatística insuficiente)
  - `tem_ano_negativo == True` (sequência de ≥ 12 meses OOS negativos)
  - WFE s/ Outliers < 50%
  - WFE Médio < 50%
- ✅ **Campo `"vetos": [...]`** adicionado ao retorno de `calcular_veredicto()` — lista de chaves das regras que dispararam (vazia se nenhuma)
- ✅ **`_gerar_comentario()` reformulada** em `analysis/verdict.py` — substitui o insight de "melhor OOS" por contagem de WFCs reprovados por regra; string vazia quando nenhuma regra dispara (comentário ocultado)
- ✅ **`scraper/runner.py`** — push `scenario_done` inclui `"vetos"` e objeto completo `"representatividade"` (em vez de apenas `max_representatividade` flat)
- ✅ **`output/templates/report.html.j2`**:
  - Tabela WFM: badges `🚫 Z-Score`, `🚫 Concentração` etc. ao lado do badge de veredicto
  - Detalhe expansível: caixa vermelha com razões completas do veto
  - Comentário global: linhas `📌 x WFC(s) reprovados por [motivo]` renderizadas individualmente
- ✅ **`templates/index.html`**:
  - Tabela de cenários: badges de veto ao lado do badge de veredicto
  - Detalhe expansível (`buildDetail`): caixa vermelha no topo com razões do veto
  - Comentário global (`renderResults`): split por `\n`, cada linha com `📌`
- ✅ **README e BACKLOG atualizados** — seção de veto documentada na tabela de scoring

---

## 📦 FASE 11 — v1.3.0: Análise Global Reformulada + Enfileirador de WFAs (2026-05-03)

### Análise Global por OOS

- ✅ **`analysis/verdict.py`** — `_gerar_por_oos()` agrupa cenários pelo período OOS e conta APROVADO/ATENÇÃO/REPROVADO em cada grupo (sorted numericamente)
- ✅ **`_comentario_oos()`** gera insight automático: "Sua estratégia parece se adaptar melhor nos períodos OOS X e Y" se algum grupo tem `aprovado > reprovado`; "Nenhum período OOS apresentou maioria de aprovações" caso contrário
- ✅ **Campo `tom`** ("positivo" / "negativo" / "neutro") no `veredicto_global` — drives da cor de fundo no relatório
- ✅ **Substituição do badge categórico** (APROVADO/REPROVADO/ATENÇÃO) pelo `comentario_oos` como destaque na "Análise Global" do relatório HTML e da UI

### Mismatch WFM ↔ Cenários

- ✅ **`scraper/extractor.py`** — `find_wfm_row_by_label()`: extrai IS/OOS do label e busca a linha WFM pelo valor (não pelo índice)
- ✅ **`scraper/runner.py`** — `_collect_scenario()` usa lookup por valor; `wfm[index]` removido
- ✅ **`output/templates/report.html.j2`** — `c.wfm_row` em vez de `wfm[loop.index0]`

### Enfileirador de WFAs (Batch Processing)

- ✅ **`scraper/runner.py`** — refatorado em três funções:
  - `_process_single_wfa(page, ...)`: assume browser/login prontos; navega para `/wfa`, faz upload, extrai cenários, gera relatórios; retorna dict (não emite `done`)
  - `run_batch_with_progress(files, ...)`: abre browser+login uma única vez, itera arquivos com try/except por arquivo, emite `batch_file_*` e `batch_done` terminal
  - `run_with_progress(...)`: wrapper retrocompatível para single-file
- ✅ **`app.py`**:
  - Novo endpoint `POST /extrair-batch` aceitando `wfa_files: list[UploadFile]` e `estrategias` (JSON list)
  - `_run_batch_background()`: bridge SSE encerra em `batch_done|error`
  - Limpeza de `tmp/{job_id}/` no finally
  - `/stream/{job_id}` reconhece `batch_done` como terminal
- ✅ **`templates/index.html`**:
  - Input `<multiple>` aceitando vários `.wfa`
  - Estado JS `batchFiles[]` com auto-derivação da estratégia (nome sem `.wfa`)
  - Lista visual da fila: badge ⏸/🔄/✅/❌, input editável de estratégia, botão remover
  - Spinner CSS animado para estado "rodando"
  - `handleEvent()` trata `batch_start`, `batch_file_start`, `batch_file_done`, `batch_file_error`, `batch_done`
  - Botão "Iniciar Lote" / "Novo Lote"
- ✅ **Resiliência**: falha de login aborta lote; falha em arquivo individual marca ❌ e segue para o próximo
- ✅ **Performance**: login único reaproveitado entre arquivos (~30s economizados por arquivo)

### Documentação

- ✅ README atualizado: changelog v1.3.0, seção "Como Usar" com fluxo de lote, "Interpretando os Resultados" com regras de veto e Análise Global
- ✅ BACKLOG: nova FASE 11 documentando todas as entregas

---

## 📋 PENDENTE / BACKLOG FUTURO

- ⬜ Voltar `headless=True` após confirmar funcionamento da extração de Equity OOS
- ⬜ Remover código de debug (`debug_tooltips.txt`, `debug_chart_data_cenario_0.json`) após validação
- ⬜ Validar cálculo de representatividade com valores R$ reais (atualmente usa CAGR/AVG DD como fallback quando extração SVG falha)
- ⬜ Testar extração end-to-end com múltiplos arquivos `.wfa` (diferentes números de steps/cenários)
- ⬜ Campo "Estratégia" com persistência entre sessões

---

## 🗂️ Arquivos do Projeto

| Arquivo | Responsabilidade |
|---|---|
| `app.py` | Servidor FastAPI + SSE + rotas (inclui `/admin/restart`) |
| `config.py` | Parâmetros globais, scoring (7 critérios), timeouts |
| `main.py` | Entry point CLI |
| `WFA_Extractor.bat` | Inicialização com duplo clique |
| `BACKLOG.md` | Histórico de entregas e pendências |
| `README.md` | Documentação do projeto (changelog, scoring, guia dev) |
| `scraper/auth.py` | Login BotSpot |
| `scraper/upload.py` | Upload `.wfa` |
| `scraper/extractor.py` | Extração DOM + ApexCharts + SVG attrs + hover |
| `scraper/runner.py` | Orquestração completa + pipeline Equity OOS |
| `analysis/metrics.py` | Cálculo de todas as métricas (incl. significância) |
| `analysis/verdict.py` | Scoring, veredicto por cenário e veredicto global com insight |
| `output/json_writer.py` | Exportação JSON |
| `output/html_report.py` | Geração do relatório HTML (filtros Jinja2) |
| `output/templates/report.html.j2` | Template do relatório |
| `templates/index.html` | Interface web (timer, restart, critérios editáveis) |
