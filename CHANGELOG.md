# Changelog

Todas as mudanças notáveis deste projeto são documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [1.4.0] — 2026-05-08

### Adicionado
- **Períodos dos ciclos IS/OOS** por cenário — tabela com datas de início/fim de cada step, coletada via "Mais > Periodos" do BotSpot. Função `extract_periodos()` em `scraper/extractor.py`, com helper `_split_range()` para separar os intervalos `"início - fim"`.
- **Gráfico de Equity OOS** no detalhe de cada cenário (Chart.js 4.4.4): barras com o valor OOS individual por step (verde/vermelho por sinal) + linha do equity acumulado. Renderização lazy ao expandir o painel.

### Corrigido
- Estrutura da tabela de Periodos corrigida: são **3 colunas** (STEP | IN SAMPLE | OUT OF SAMPLE) com datas em intervalo de texto único — não 5 colunas separadas.
- Modal de Periodos agora identificado **pelo conteúdo** (`IN SAMPLE` + `OUT OF SAMPLE`), evitando capturar o modal de Distribuição residual que deixava a tabela vazia.
- Clique no item de menu "Periodos" ancorado (`^periodos$` + `is_visible()`) para não casar com textos como "Período OOS" na página.

## [1.3.0] — 2026-05-03

### Adicionado
- Enfileirador de WFAs (batch): processa múltiplos `.wfa` em sequência reaproveitando browser/login. Endpoint `POST /extrair-batch` e eventos SSE `batch_*`.
- Análise Global por OOS: breakdown de aprovados/atenção/reprovados por período OOS, com insight automático e campo `tom` (positivo/negativo/neutro).

### Corrigido
- Mismatch WFM ↔ cenários: `find_wfm_row_by_label()` busca a linha WFM por valor IS/OOS em vez de índice.

## [1.2.0] — 2026-05-02

### Adicionado
- 5 regras de veto por cenário que forçam REPROVADO independentemente da pontuação (concentração > 30%, Z-Score < 2,5, ano negativo, WFE s/ Outliers < 50%, WFE Médio < 50%).
- Badges de veto na tabela de cenários e no detalhe expansível.

## [1.1.3] — 2026-05-01

### Alterado
- Pontuação máxima reequilibrada para 100 pts (6 critérios × 15 + Significância × 10).

## [1.1.2] — 2026-05-01

### Alterado
- Critérios padrão alinhados ao painel de avaliação; penalidades negativas e casas decimais liberadas na UI.

## [1.1.1] — 2026-05-01

### Corrigido
- Botão "Iniciar Extração" travado: chave `'média':` sem aspas no JS causava erro de parse silencioso. Normalização de acentos em `metrics.py`/`config.py` e header `Cache-Control: no-store` na rota `/`.

## [1.1.0] — 2026-04-30

### Adicionado
- Critério Significância (máx 110 pts), timer de execução, botão Reiniciar Servidor, card "Equity Total OOS", veredicto global reformulado, seletor de máximo de cenários.

## [1.0.0] — 2026-04-28

### Adicionado
- Versão inicial: extração completa, 6 critérios de scoring, relatório HTML/JSON, interface web com dark mode e critérios editáveis.

[1.4.0]: #140--2026-05-08
[1.3.0]: #130--2026-05-03
[1.2.0]: #120--2026-05-02
[1.1.3]: #113--2026-05-01
[1.1.2]: #112--2026-05-01
[1.1.1]: #111--2026-05-01
[1.1.0]: #110--2026-04-30
[1.0.0]: #100--2026-04-28
