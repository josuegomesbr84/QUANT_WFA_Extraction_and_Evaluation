import json
import os
import re
import time
from playwright.sync_api import Page
from config import TIMEOUTS

# Padrão exato dos labels de cenário do BotSpot
_SCENARIO_RE = re.compile(r"Steps:\s*\d+\s*-\s*IS:\s*\d+\s*-\s*OOS:\s*\d+")


def find_wfm_row_by_label(label: str, wfm: list[dict]) -> dict:
    """Encontra a linha WFM correspondente ao cenário pelo IS e OOS do label.

    O label tem o formato "Steps: X - IS: Y - OOS: Z".
    Busca na lista wfm a linha onde in_sample == Y e out_of_sample == Z.
    Retorna {} se não encontrar (fallback seguro).
    """
    m = re.search(r"IS:\s*(\d+)\s*-\s*OOS:\s*(\d+)", label)
    if not m:
        return {}
    is_val, oos_val = m.group(1), m.group(2)
    for row in wfm:
        if str(row.get("in_sample", "")).strip() == is_val and \
           str(row.get("out_of_sample", "")).strip() == oos_val:
            return row
    return {}


def get_wfm(page: Page) -> list[dict]:
    """Extrai as 12 linhas da Walk Forward Matrix (tabela fixa do topo)."""
    rows = []
    tables = page.locator("table")
    count = tables.count()

    target_table = None
    for i in range(count):
        header = tables.nth(i).locator("thead").inner_text().upper()
        if "STEP" in header and "IN SAMPLE" in header and "WFE" in header and "SIGNIF" in header:
            target_table = tables.nth(i)
            break

    if target_table is None and count > 0:
        target_table = tables.first

    if target_table is None:
        return rows

    tbody_rows = target_table.locator("tbody tr")
    row_count = tbody_rows.count()

    for i in range(row_count):
        cells = tbody_rows.nth(i).locator("td")
        if cells.count() < 5:
            continue
        rows.append({
            "steps": cells.nth(0).inner_text().strip(),
            "in_sample": cells.nth(1).inner_text().strip(),
            "out_of_sample": cells.nth(2).inner_text().strip(),
            "significancia": cells.nth(3).inner_text().strip(),
            "wfe": cells.nth(4).inner_text().strip(),
        })

    return rows


# ─── Cenários: detecção dinâmica do dropdown ─────────────────────────────────

def _scan_scenario_labels_in_dom(page: Page) -> list[str]:
    """
    Varre todos os nós de texto do DOM procurando labels no padrão
    'Steps: X - IS: Y - OOS: Z'. Funciona mesmo com itens ocultos.
    """
    found = page.evaluate(r"""
        () => {
            const pat = /^Steps:\s*\d+\s*-\s*IS:\s*\d+\s*-\s*OOS:\s*\d+$/;
            const seen = new Set();
            const result = [];
            function walk(node) {
                if (node.nodeType === 3) {            // text node
                    const t = node.textContent.trim();
                    if (pat.test(t) && !seen.has(t)) { seen.add(t); result.push(t); }
                } else if (node.nodeType === 1) {     // element
                    for (const c of node.childNodes) walk(c);
                }
            }
            walk(document.body);
            return result;
        }
    """)
    return found or []


def _click_scenario_trigger(page: Page) -> bool:
    """
    Localiza e clica no trigger do dropdown de cenários.
    Tenta vários seletores CSS e valida pelo conteúdo de texto.
    Retorna True se o clique pareceu abrir algo.
    """
    # Contagem de labels antes do clique
    before = set(_scan_scenario_labels_in_dom(page))

    trigger_selectors = [
        '[aria-haspopup="menu"]',
        '[aria-haspopup="listbox"]',
        '[aria-haspopup="true"]',
        '[role="combobox"]',
        'button',
    ]
    for sel in trigger_selectors:
        for loc in page.locator(sel).all():
            try:
                txt = loc.inner_text().strip()
                if _SCENARIO_RE.search(txt) or "WFA" in txt.upper():
                    loc.click()
                    time.sleep(1.2)
                    after = set(_scan_scenario_labels_in_dom(page))
                    if len(after) > len(before):
                        return True   # dropdown abriu e novos labels apareceram
                    # não abriu — fecha e tenta próximo
                    page.keyboard.press("Escape")
                    time.sleep(0.3)
            except Exception:
                continue

    # Último recurso: clicar em qualquer elemento que contenha o padrão
    for loc in page.get_by_text(_SCENARIO_RE).all():
        try:
            loc.click()
            time.sleep(1.2)
            after = set(_scan_scenario_labels_in_dom(page))
            if len(after) > len(before):
                return True
            page.keyboard.press("Escape")
            time.sleep(0.3)
        except Exception:
            continue

    return False


def _get_dropdown_toggle(page: Page):
    """Retorna o locator do botão que abre o dropdown de cenários."""
    toggle = page.locator(".dropdown-toggle").filter(
        has_text=re.compile(r"Steps:|WFA", re.IGNORECASE)
    )
    if toggle.count() > 0:
        return toggle.first
    return page.locator(".dropdown-toggle").first


def get_current_scenario_label(page: Page) -> str:
    """
    Lê o label do cenário atualmente exibido na página
    (texto visível no botão do dropdown ou no título da seção).
    """
    # Tenta ler do botão toggle (mostra o cenário selecionado)
    toggle = _get_dropdown_toggle(page)
    try:
        txt = toggle.inner_text().strip()
        m = _SCENARIO_RE.search(txt)
        if m:
            return m.group(0).strip()
    except Exception:
        pass

    # Fallback: qualquer texto visível com o padrão
    for loc in page.get_by_text(_SCENARIO_RE).all():
        try:
            if loc.is_visible():
                txt = loc.inner_text().strip()
                m = _SCENARIO_RE.search(txt)
                if m:
                    return m.group(0).strip()
        except Exception:
            continue
    return ""


def get_scenario_labels(page: Page) -> list[str]:
    """
    Retorna os labels de todos os cenários.
    Abre o dropdown para forçar a renderização dos itens,
    lê todos, depois fecha.
    """
    try:
        page.wait_for_load_state("networkidle", timeout=TIMEOUTS["scenario_switch"])
    except Exception:
        pass
    time.sleep(1.0)

    # Tenta sem abrir (React às vezes pré-renderiza os itens)
    items = page.locator("a.dropdown-item").filter(has_text="Steps:")
    if items.count() >= 2:
        return [items.nth(i).inner_text().strip() for i in range(items.count())]

    # Abre o dropdown para forçar renderização
    toggle = _get_dropdown_toggle(page)
    toggle.click()
    time.sleep(0.8)

    try:
        page.wait_for_selector("a.dropdown-item", timeout=6_000)
    except Exception:
        pass

    items = page.locator("a.dropdown-item").filter(has_text="Steps:")
    if items.count() >= 1:
        labels = [items.nth(i).inner_text().strip() for i in range(items.count())]
        page.keyboard.press("Escape")
        time.sleep(0.3)
        return labels

    # Fallback: scan de text nodes
    page.keyboard.press("Escape")
    labels = _scan_scenario_labels_in_dom(page)
    if labels:
        return labels

    page.screenshot(path="resultados/debug_no_labels.png")
    raise RuntimeError("Labels de cenário não encontrados. Screenshot salvo em resultados/")


def select_scenario(page: Page, label: str) -> str:
    """
    Seleciona um cenário PELO LABEL via Bootstrap dropdown.
    1. Clica no toggle para abrir o menu
    2. Aguarda os itens ficarem visíveis
    3. Clica no item correto
    """
    # Abre o dropdown
    toggle = _get_dropdown_toggle(page)
    toggle.click()
    time.sleep(0.8)

    try:
        page.wait_for_selector("a.dropdown-item", timeout=6_000)
    except Exception:
        pass

    # Clica no item pelo texto
    item = page.locator("a.dropdown-item").filter(has_text=label).first
    item.click()

    # Aguarda re-render
    try:
        page.wait_for_selector(
            '.spinner, [class*="loading"], [class*="spinner"]',
            state="visible",
            timeout=TIMEOUTS["spinner_appear"],
        )
        page.wait_for_selector(
            '.spinner, [class*="loading"], [class*="spinner"]',
            state="hidden",
            timeout=TIMEOUTS["scenario_switch"],
        )
    except Exception:
        time.sleep(2)

    try:
        page.wait_for_load_state("networkidle", timeout=TIMEOUTS["scenario_switch"])
    except Exception:
        time.sleep(2)

    return label


# ─── Extração de dados do cenário selecionado ─────────────────────────────────

def _extract_zscore(page: Page) -> str | None:
    """
    Acessa Mais > DISTRIBUIÇÃO na seção WFA e extrai o Z-Score do popup.
    """
    try:
        # ── 1. Clica no botão "Mais" da seção WFA ────────────────────────
        mais = page.locator('button:has-text("Mais")').last
        if mais.count() == 0:
            mais = page.get_by_role("button", name=re.compile(r"mais", re.IGNORECASE)).last
        mais.click()
        time.sleep(0.5)

        # ── 2. Clica na opção "DISTRIBUIÇÃO" / "Distribuição" ─────────────
        dist = page.get_by_text(re.compile(r"distribui", re.IGNORECASE))
        dist.first.click()
        time.sleep(1.0)

        # ── 3. Aguarda o popup aparecer ───────────────────────────────────
        popup_sel = (
            '[role="dialog"], [class*="modal"], [class*="Modal"], '
            '[class*="popup"], [class*="Popup"], [class*="dialog"]'
        )
        try:
            page.wait_for_selector(popup_sel, timeout=8_000)
            popup_text = page.locator(popup_sel).first.inner_text()
        except Exception:
            # Fallback: lê o body todo (popup pode não ter role="dialog")
            popup_text = page.locator("body").inner_text()

        # ── 4. Extrai o Z-Score do texto ──────────────────────────────────
        zscore = None
        match = re.search(r'Z[\s\-]?Score[:\s]+([0-9]+[,.]?[0-9]*)', popup_text, re.IGNORECASE)
        if match:
            zscore = match.group(1).replace(",", ".")

        # ── 5. Fecha o popup ──────────────────────────────────────────────
        page.keyboard.press("Escape")
        time.sleep(0.5)

        return zscore

    except Exception:
        # Fallback: tenta extrair do texto da página sem abrir popup
        try:
            body_text = page.locator("body").inner_text()
            match = re.search(r'Z[\s\-]?Score[:\s]+([0-9]+[,.]?[0-9]*)', body_text, re.IGNORECASE)
            if match:
                return match.group(1).replace(",", ".")
        except Exception:
            pass
        return None


def get_scenario_data(page: Page) -> dict:
    """Extrai cards de indicadores, Z-Score, tabela WFA e parâmetros frequentes."""
    cards = {"meses": None, "anos": None, "oos_negativos": None}
    card_elements = page.locator(".card")
    card_count = card_elements.count()

    for i in range(card_count):
        try:
            text = card_elements.nth(i).inner_text().strip().lower()
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if len(lines) < 2:
                continue
            label, valor = lines[0], lines[1]
            if "mês" in label or "mes" in label:
                cards["meses"] = valor
            elif "ano" in label:
                cards["anos"] = valor
            elif "oos" in label or "negativ" in label:
                cards["oos_negativos"] = valor
        except Exception:
            continue

    zscore_raw = _extract_zscore(page)

    # Tabela WFA do cenário ativo
    wfa_rows = []
    tables = page.locator("table")
    table_count = tables.count()

    for t in range(table_count):
        try:
            header_text = tables.nth(t).locator("thead").inner_text().upper()
            if "STEP" in header_text and "WFE" in header_text and "SIGNIF" not in header_text:
                tbody_rows = tables.nth(t).locator("tbody tr")
                row_count = tbody_rows.count()
                for r in range(row_count):
                    cells = tbody_rows.nth(r).locator("td")
                    cell_count = cells.count()
                    if cell_count < 4:
                        continue
                    wfa_rows.append({
                        "step": cells.nth(0).inner_text().strip(),
                        "in_sample": cells.nth(1).inner_text().strip(),
                        "out_of_sample": cells.nth(2).inner_text().strip(),
                        "wfe": cells.nth(3).inner_text().strip(),
                        "operacoes_is": cells.nth(4).inner_text().strip() if cell_count > 4 else "",
                        "operacoes_oos": cells.nth(5).inner_text().strip() if cell_count > 5 else "",
                        "parametros": cells.nth(6).inner_text().strip() if cell_count > 6 else "",
                    })
                if wfa_rows:
                    break
        except Exception:
            continue

    # Parâmetros frequentes
    parametros_frequentes = []
    try:
        all_cards = page.locator(".card")
        for i in range(all_cards.count()):
            try:
                text = all_cards.nth(i).inner_text().strip()
                if "/" in text and ("%" in text or "=" in text):
                    parametros_frequentes.append(text)
            except Exception:
                continue
    except Exception:
        pass

    return {
        "cards": cards,
        "zscore_raw": zscore_raw,
        "tabela_wfa": wfa_rows,
        "parametros_frequentes": parametros_frequentes[:6],
    }


def _coerce_apex_numeric(data: list) -> list[float] | None:
    """
    Converte um array `series.data` do ApexCharts em list[float], aceitando os formatos:
    - números puros: [1.5, -2.3, ...]
    - dicts: [{'x': 'A', 'y': 1.5}, ...]
    - tuplas/listas: [[ts, 1.5], ...]
    Retorna None se algum item não puder ser convertido.
    """
    out: list[float] = []
    for item in data:
        try:
            if item is None:
                out.append(0.0)
            elif isinstance(item, (int, float)):
                out.append(float(item))
            elif isinstance(item, dict):
                y = item.get("y")
                if y is None:
                    return None
                out.append(float(y))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                out.append(float(item[1]))
            else:
                out.append(float(item))
        except (TypeError, ValueError):
            return None
    return out


def extract_oos_via_svg_attrs(page: Page, n_steps: int) -> list[float]:
    """
    Lê os valores das barras diretamente dos atributos SVG do ApexCharts.

    O ApexCharts escreve o valor real de cada barra como atributo `val`
    nos elementos <path class="apexcharts-bar-area">. Cada série de barras
    fica agrupada por índice `j` (posição no eixo X) e `seriesIndex`.

    Estratégia:
    1. Coleta todos os .apexcharts-bar-area com atributo `val`
    2. Agrupa por seriesIndex — pega a série com n_steps elementos
    3. Ordena por j (índice do step) e retorna os valores
    """
    raw = page.evaluate("""
        () => {
            const bars = document.querySelectorAll('.apexcharts-bar-area');
            const result = [];
            bars.forEach(function(el) {
                result.push({
                    val:         el.getAttribute('val'),
                    j:           el.getAttribute('j'),
                    seriesIndex: el.getAttribute('seriesIndex') ||
                                 el.getAttribute('data\\:realIndex') || '0',
                    cls:         el.getAttribute('class') || '',
                });
            });
            return result;
        }
    """)

    if not raw:
        return []

    # Agrupa por seriesIndex
    from collections import defaultdict
    groups: dict[str, list[dict]] = defaultdict(list)
    for item in raw:
        if item.get("val") is None:
            continue
        groups[item.get("seriesIndex", "0")].append(item)

    # Prefere série com exatamente n_steps barras; se não, a mais próxima
    best = None
    for series_items in groups.values():
        if len(series_items) == n_steps:
            best = series_items
            break
    if best is None:
        return []

    # Ordena por j (índice do step, string numérica)
    try:
        best.sort(key=lambda x: int(x.get("j") or 0))
    except (ValueError, TypeError):
        pass

    values: list[float] = []
    for item in best:
        try:
            values.append(float(item["val"]))
        except (TypeError, ValueError):
            values.append(0.0)

    if all(v == 0.0 for v in values):
        return []
    return values


def extract_oos_equity_steps(chart_data: list[dict], n_steps: int) -> list[float]:
    """
    Extrai os valores financeiros OOS por step dos gráficos ApexCharts.
    Procura uma série com exatamente n_steps pontos de dados, preferindo
    séries cujo tipo é 'bar' ou 'column' (gráfico financeiro OOS por step).
    Aceita dados em formato numérico, dict {x,y} ou tupla [ts, val].
    Retorna lista vazia se nenhuma série compatível for encontrada.
    """
    if not chart_data or n_steps <= 0:
        return []

    candidates: list[tuple[int, list[float]]] = []  # (priority, values)

    for chart in chart_data:
        chart_type = (chart.get("type") or "").lower()
        for series in (chart.get("series") or []):
            data = series.get("data") or []
            if len(data) != n_steps:
                continue

            values = _coerce_apex_numeric(data)
            if values is None or len(values) != n_steps:
                continue

            # Pula séries com tudo zero (provavelmente não é o gráfico financeiro)
            if all(v == 0 for v in values):
                continue

            # Prioridade: nome contém "oos" > tipo bar/column > qualquer outro
            series_name = (series.get("name") or "").lower()
            series_type = (series.get("type") or chart_type).lower()

            if "oos" in series_name:
                priority = 0
            elif series_type in ("bar", "column"):
                priority = 1
            else:
                priority = 2

            candidates.append((priority, values))

    if not candidates:
        return []

    candidates.sort(key=lambda c: c[0])
    return candidates[0][1]


def _parse_tooltip_number(text: str) -> float | None:
    """
    Extrai o primeiro número válido de uma string de tooltip.
    Suporta formatos: 1900.00 / 1.900,00 / -500 / R$ 1.500,00
    """
    # Remove prefixo monetário e espaços
    text = text.replace("R$", "").replace("\xa0", "").strip()
    # Tenta padrão BR: 1.234,56
    m = re.search(r'-?[\d]{1,3}(?:\.[\d]{3})*,[\d]+', text)
    if m:
        raw = m.group().replace(".", "").replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            pass
    # Tenta padrão EN: 1,234.56 ou simples 1234.56
    m = re.search(r'-?[\d]+(?:[.,][\d]+)?', text)
    if m:
        raw = m.group().replace(",", "")
        try:
            return float(raw)
        except ValueError:
            pass
    return None


def extract_oos_via_hover(page: Page, n_steps: int) -> list[float]:
    """
    Extrai valores OOS por step usando mouse real do Playwright.

    Problema anterior: o gráfico estava fora do viewport (y > 900px),
    então page.mouse.move() não atingia o SVG.

    Solução: usar JS para rolar o canvas para o centro do viewport (instant),
    obter as coordenadas corretas APÓS o scroll, e só então mover o mouse.
    Com o canvas dentro do viewport, os eventos mousemove chegam ao ApexCharts.
    """
    import os as _os

    # ── 1. Rola o canvas para o viewport e devolve as coordenadas ─────────
    chart_info = page.evaluate("""
        (n_steps) => {
            // Localiza canvas com barras (qualquer canvas com bar-area)
            let canvas = null;
            for (const c of document.querySelectorAll('.apexcharts-canvas')) {
                if (c.querySelectorAll('.apexcharts-bar-area, path[class*="bar"]').length >= n_steps) {
                    canvas = c;
                    break;
                }
            }
            // Fallback: último canvas da página (gráfico de steps fica no final)
            if (!canvas) {
                const all = document.querySelectorAll('.apexcharts-canvas');
                if (all.length > 0) canvas = all[all.length - 1];
            }
            if (!canvas) return null;

            // Rola para o centro — behavior:'instant' é síncrono
            canvas.scrollIntoView({block: 'center', behavior: 'instant'});

            // getBoundingClientRect() agora retorna coords dentro do viewport
            const rect = canvas.getBoundingClientRect();
            const padFrac = 0.08;
            const plotX0  = rect.left + rect.width * padFrac;
            const plotW   = rect.width * (1 - 2 * padFrac);
            const stepW   = plotW / n_steps;
            const chartY  = rect.top + rect.height * 0.40;

            const coords = [];
            for (let i = 0; i < n_steps; i++) {
                coords.push({x: plotX0 + stepW * (i + 0.5), y: chartY});
            }
            return {
                coords,
                rect: {left: rect.left, top: rect.top, w: rect.width, h: rect.height},
            };
        }
    """, n_steps)

    if not chart_info:
        return []

    coords     = chart_info["coords"]
    tooltip_loc = page.locator(".apexcharts-tooltip").first
    values: list[float] = []
    raw_tooltips: list[str] = []

    # Ativa o gráfico com um primeiro movimento
    page.mouse.move(coords[0]["x"], coords[0]["y"])
    time.sleep(0.5)

    for i, coord in enumerate(coords):
        page.mouse.move(coord["x"], coord["y"])
        time.sleep(0.5)

        tooltip_text = ""
        try:
            tooltip_loc.wait_for(state="visible", timeout=2_000)
            tooltip_text = tooltip_loc.inner_text(timeout=1_000)
        except Exception:
            pass

        raw_tooltips.append(
            f"[step {i+1} x={coord['x']:.0f} y={coord['y']:.0f}] {repr(tooltip_text)}"
        )

        # Extrai valor da linha "Período OOS: ..."
        value = None
        lines = [l.strip() for l in tooltip_text.splitlines() if l.strip()]
        for line in lines:
            if "oos" in line.lower() or "período" in line.lower() or "periodo" in line.lower():
                value = _parse_tooltip_number(line)
                if value is not None:
                    break
        # Fallback: primeiro número após o label do step (linha 0 = nº do step)
        if value is None and len(lines) > 1:
            for line in lines[1:]:
                value = _parse_tooltip_number(line)
                if value is not None:
                    break

        values.append(value if value is not None else 0.0)

    # ── Salva debug ───────────────────────────────────────────────────────
    try:
        _os.makedirs("resultados", exist_ok=True)
        with open("resultados/debug_tooltips.txt", "w", encoding="utf-8") as _f:
            _f.write(f"canvasRect: {chart_info.get('rect')}\n\n")
            _f.write("\n".join(raw_tooltips))
    except Exception:
        pass

    # Move mouse para fora do gráfico
    try:
        page.mouse.move(0, 0)
    except Exception:
        pass

    if all(v == 0.0 for v in values):
        return []
    return values if len(values) == n_steps else []


def get_chart_data(page: Page) -> list[dict]:
    """
    Extrai dados dos gráficos ApexCharts via injeção de JavaScript.
    Tenta múltiplas estratégias para acessar as instâncias:
    1. window.Apex._chartInstances (API pública do ApexCharts)
    2. window.ApexCharts.getChartByID via elementos DOM
    3. Acesso via atributo interno __apexcharts__ nos elementos
    """
    return page.evaluate("""
        () => {
            function serializeInstance(c) {
                try {
                    return {
                        id: c.id,
                        type: c.w && c.w.config && c.w.config.chart
                            ? c.w.config.chart.type : null,
                        series: c.w && c.w.config ? c.w.config.series : [],
                        categories: c.w && c.w.config && c.w.config.xaxis
                            ? c.w.config.xaxis.categories : []
                    };
                } catch(e) {
                    return null;
                }
            }

            try {
                var instances = [];

                // Estratégia 1: window.Apex._chartInstances
                if (window.Apex && Array.isArray(window.Apex._chartInstances) && window.Apex._chartInstances.length > 0) {
                    instances = window.Apex._chartInstances;
                }

                // Estratégia 2: window.ApexCharts.getChartByID a partir dos IDs no DOM
                if (instances.length === 0 && window.ApexCharts) {
                    var canvases = document.querySelectorAll('.apexcharts-canvas');
                    canvases.forEach(function(el) {
                        var id = el.id ? el.id.replace('apexcharts', '') : null;
                        if (id) {
                            try {
                                var inst = window.ApexCharts.getChartByID(id);
                                if (inst) instances.push(inst);
                            } catch(e) {}
                        }
                    });
                }

                // Estratégia 3: propriedade interna nos elementos canvas
                if (instances.length === 0) {
                    var canvases = document.querySelectorAll('.apexcharts-canvas');
                    canvases.forEach(function(el) {
                        // ApexCharts armazena a instância em el.__apexcharts__ ou el._chart
                        var inst = el.__apexcharts__ || el._chart || null;
                        if (inst) instances.push(inst);
                    });
                }

                var result = instances.map(serializeInstance).filter(function(x) { return x !== null; });
                return result;
            } catch (e) {
                return [{_error: e.toString()}];
            }
        }
    """)
