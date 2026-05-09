# CLAUDE.md — Extração WFA

Instruções permanentes para o Claude Code neste projeto. Seguir sempre, sem precisar ser lembrado a cada sessão.

---

## Projeto

**WFA Extractor** — automação FastAPI para extração e avaliação de estratégias de trading via Walk Forward Analysis no BotSpot.com.br.

- **Stack**: Python 3.11+, FastAPI, Uvicorn, Playwright (sync, thread separado), Jinja2, Pandas, NumPy
- **Frontend**: HTML/CSS/JS puro em `templates/index.html` (sem framework)
- **Comunicação em tempo real**: SSE (Server-Sent Events) via `GET /stream/{job_id}`
- **Encoding crítico**: arquivos `.set` e relatórios HTML do MT5 usam **UTF-16 LE com BOM**

### Estrutura de pastas

```
app.py                  # FastAPI — endpoints + SSE
config.py               # Constantes: URLs, timeouts, scoring
main.py                 # Entrypoint uvicorn
scraper/
  runner.py             # Orquestração Playwright (login + batch)
  extractor.py          # Extração de cenários WFA do DOM
  auth.py               # Login BotSpot
  upload.py             # Upload do arquivo .wfa
analysis/
  verdict.py            # Veredicto por cenário + global (scoring + vetos)
  metrics.py            # Cálculo de métricas (WFE, Z-score, etc.)
output/
  html_report.py        # Geração de relatório HTML via Jinja2
  json_writer.py        # Serialização JSON dos resultados
templates/
  index.html            # UI principal (abas: Extração, Histórico)
output/templates/
  report.html.j2        # Template do relatório de análise
```

---

## Comportamento padrão — seguir sempre

### Ao concluir qualquer feature ou correção
1. **Testar** a mudança antes de declarar conclusão. Nunca dizer "pronto" sem verificar que o código executa sem erro.
2. **Propor atualização** de `README.md` e `BACKLOG.md` com o que mudou.
3. **Propor commit** com mensagem descritiva no padrão `feat:` / `fix:` / `docs:` / `refactor:`.

### Ao iniciar implementação de feature nova
1. Confirmar o **escopo** antes de codificar: "isso vai neste projeto? É MVP ou completo? Qual branch?"
2. Para mudanças de risco médio ou alto, **trabalhar em branch separado** (`feat/nome-da-feature`), nunca direto no `main`.
3. Se a feature for grande (>1 arquivo novo ou >100 linhas), **perguntar apenas o que bloqueia** — não fazer rodadas longas de Q&A se for possível usar defaults razoáveis.

### Ao encontrar ambiguidade
- Usar o **comportamento mais conservador** e informar o que foi assumido.
- Não inventar comportamento novo silenciosamente.

---

## Convenções de código

- **Python**: type hints em funções públicas; docstring em funções com lógica não óbvia; sem dependências novas sem aprovação explícita.
- **JavaScript**: sem frameworks; `const`/`let` (nunca `var`); propriedades de objeto em ASCII (sem acentos em chaves JS — ex: `media` não `média`).
- **Jinja2**: lógica mínima nos templates; filtros customizados definidos em `html_report.py`.
- **SSE**: eventos terminam com `"done"`, `"batch_done"` ou `"error"` — o stream fecha neles.

---

## Decisões de design já tomadas — não revisar sem pedido explícito

| Decisão | Escolha |
|---|---|
| Verificação de cenário | Lookup por valor IS/OOS (`find_wfm_row_by_label`), nunca por índice |
| Veredicto global | Baseado em distribuição por período OOS, não badge único |
| Vetos de cenário | 5 regras hard que forçam REPROVADO independente de pontuação |
| Batch WFA | Login único, processa arquivos sequencialmente, continua em caso de erro |
| Playwright no Windows | Sync API em thread separada (não `asyncio`) |

---

## Registro de aprendizados

Sempre que um erro for corrigido ou uma decisão técnica não óbvia for tomada, registrar aqui antes de fechar a tarefa. O objetivo é evitar repetir o mesmo erro em sessões futuras.

### Erros já cometidos — não repetir

| Erro | Causa | Correção |
|---|---|---|
| WFM linha errada no relatório | Usava `wfm[loop.index0]` (índice absoluto) em vez de buscar pela combinação IS/OOS | `find_wfm_row_by_label()` faz lookup por valor, não por posição |
| Script JS silenciosamente quebrado no Edge | Propriedade de objeto com acento: `'média':` não é JS válido em todos os parsers | Usar sempre ASCII em chaves JS: `media`, `atencao`, `aprovado` |
| Feature declarada "pronta" sem teste real | Confiança excessiva na lógica sem verificação de execução | Nunca declarar pronto sem testar — ver seção "Comportamento padrão" |
| Feature grande implementada no projeto errado | Planejamento iniciado sem confirmar destino (projeto/branch) | Confirmar escopo antes de qualquer planejamento |

### Como registrar um novo aprendizado

Ao corrigir qualquer bug não trivial ou tomar uma decisão de design relevante, adicionar uma linha na tabela acima com:
- **Erro**: o que deu errado ou qual decisão foi tomada
- **Causa**: por que aconteceu
- **Correção**: o que fazer na próxima vez

---

## O que NÃO fazer

- **Não adicionar dependências** (pip) sem confirmar com o usuário.
- **Não refatorar código não relacionado** à tarefa em curso.
- **Não fazer commits direto no `main`** para features novas — propor branch.
- **Não declarar "testado" ou "funcionando"** sem ter executado o código ou verificado a lógica concretamente.
- **Não iniciar planejamento longo** de uma feature sem confirmar antes que ela pertence a este projeto e a este repositório.
