import json
import os
import re
import time
from playwright.sync_api import Page
from config import TIMEOUTS

# Padrão exato dos labels de cenário do BotSpot
_SCENARIO_RE = re.compile(r"Steps:\s*\d+\s*-\s*IS:\s*\d+\s*-\s*OOS:\s*\d+")


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


def get_chart_data(page: Page) -> list[dict]:
    """Extrai dados dos gráficos ApexCharts via injeção de JavaScript."""
    return page.evaluate("""
        () => {
            try {
                var instances = (window.Apex && window.Apex._chartInstances)
                    ? window.Apex._chartInstances : [];
                return instances.map(function(c) {
                    return {
                        id: c.id,
                        type: c.w && c.w.config && c.w.config.chart
                            ? c.w.config.chart.type : null,
                        series: c.w && c.w.config ? c.w.config.series : [],
                        categories: c.w && c.w.config && c.w.config.xaxis
                            ? c.w.config.xaxis.categories : []
                    };
                });
            } catch (e) {
                return [];
            }
        }
    """)
