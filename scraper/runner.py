import queue as tq

from playwright.sync_api import sync_playwright

from scraper.auth import login
from scraper.upload import send_wfa
from scraper.extractor import (
    get_wfm,
    get_scenario_labels,
    get_current_scenario_label,
    select_scenario,
    get_scenario_data,
    get_chart_data,
    extract_oos_equity_steps,
    extract_oos_via_svg_attrs,
    extract_oos_via_hover,
)
from analysis.metrics import compute_all_metrics
from analysis.verdict import calcular_veredicto, veredicto_global
from output.json_writer import save as save_json
from output.html_report import save as save_html


def _collect_scenario(
    page, label: str, index: int, total: int, wfm: list, push,
    scoring_config=None, veredicto_thresholds=None,
) -> dict:
    """Extrai dados, calcula métricas e veredicto do cenário atualmente exibido."""
    scenario_data = get_scenario_data(page)
    chart_data = get_chart_data(page)

    meses_total = 0
    try:
        meses_total = int(str(scenario_data["cards"].get("meses") or "0").strip())
    except (ValueError, TypeError):
        pass

    # Extrai valores financeiros R$ OOS por step do gráfico de barras
    n_steps = len(scenario_data["tabela_wfa"])
    wfm_row = wfm[index] if index < len(wfm) else {}

    # Tentativa 1: atributos SVG das barras (val, j, seriesIndex) — mais rápido
    oos_equity_steps = extract_oos_via_svg_attrs(page, n_steps)
    if oos_equity_steps:
        push({"type": "log", "msg": f"[{label}] ✓ Equity OOS via SVG attrs: {len(oos_equity_steps)} steps"})

    # Tentativa 2: window.Apex._chartInstances (JS config)
    if not oos_equity_steps:
        oos_equity_steps = extract_oos_equity_steps(chart_data, n_steps)
        if oos_equity_steps:
            push({"type": "log", "msg": f"[{label}] ✓ Equity OOS via Apex config: {len(oos_equity_steps)} steps"})

    # Tentativa 3: mouse sobre o canvas + leitura do tooltip
    if not oos_equity_steps:
        push({"type": "log", "msg": f"[{label}] Tentando hover no gráfico..."})
        oos_equity_steps = extract_oos_via_hover(page, n_steps)
        if oos_equity_steps:
            push({"type": "log", "msg": f"[{label}] ✓ Equity OOS via hover: {len(oos_equity_steps)} steps"})
        else:
            push({"type": "log", "msg": f"[{label}] ⚠ Equity OOS não encontrado — coluna exibirá —"})

    metrics = compute_all_metrics(scenario_data, meses_total, oos_equity_steps, wfm_row=wfm_row)
    verdict = calcular_veredicto(metrics, scoring=scoring_config, thresholds=veredicto_thresholds)

    cenario = {
        "indice": index,
        "label": label,
        "cards": scenario_data["cards"],
        "zscore_raw": scenario_data.get("zscore_raw"),
        "tabela_wfa": scenario_data["tabela_wfa"],
        "parametros_frequentes": scenario_data["parametros_frequentes"],
        "charts": chart_data,
        "oos_equity_steps": oos_equity_steps,   # R$ por step (para o template)
        "metrics": metrics,
        "veredicto": verdict,
        "wfm_row": wfm_row,
    }

    push({
        "type": "scenario_done",
        "index": index,
        "label": label,
        "veredicto": verdict["veredicto"],
        "total_pts": verdict["total"],
        "scores": verdict["scores"],
        "metrics": {
            "zscore": metrics["zscore"],
            "wfe_medio": metrics["wfe_medio"],
            "wfe_sem_outliers": metrics["wfe_sem_outliers"],
            "pct_steps_positivos": metrics["pct_steps_positivos"],
            "max_consecutivos": metrics["consecutivos_negativos"]["max_consecutivos"],
            "max_representatividade": round(
                metrics["representatividade"]["max_representatividade"] * 100, 1
            ),
        },
        "wfm_row": wfm[index] if index < len(wfm) else {},
    })

    return cenario


def run_with_progress(
    wfa_path: str,
    email: str,
    password: str,
    filename: str,
    sync_queue: tq.Queue,
    scoring_config: dict | None = None,
    veredicto_thresholds: dict | None = None,
    estrategia: str = "",
    max_cenarios: int = 0,
) -> None:
    """Executa a extração completa usando a Playwright sync API (sem asyncio)."""

    def push(msg: dict):
        sync_queue.put(msg)

    push({"type": "log", "msg": "Iniciando browser Chromium..."})

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        push({"type": "log", "msg": "Fazendo login no BotSpot..."})
        login(page, email, password)
        push({"type": "log", "msg": "✓ Login realizado"})

        push({"type": "log", "msg": f"Enviando arquivo: {filename}..."})
        send_wfa(page, wfa_path)
        push({"type": "log", "msg": "✓ Upload concluído — /wfareport habilitado"})

        push({"type": "log", "msg": "Extraindo Walk Forward Matrix..."})
        wfm = get_wfm(page)
        push({"type": "log", "msg": f"✓ Walk Forward Matrix: {len(wfm)} cenários encontrados"})

        # ── Lê todos os labels (abre o dropdown uma vez para forçar render) ──
        all_labels = get_scenario_labels(page)

        # ── Identifica o cenário já carregado automaticamente ──────────────
        current_label = get_current_scenario_label(page)
        if current_label and current_label in all_labels:
            # Remove da lista e coloca no início
            all_labels.remove(current_label)
            all_labels = [current_label] + all_labels
        elif current_label and current_label not in all_labels:
            all_labels = [current_label] + all_labels

        if max_cenarios and 0 < max_cenarios < len(all_labels):
            all_labels = all_labels[:max_cenarios]
            push({"type": "log", "msg": f"⚙ Limitado a {max_cenarios} cenário(s) (modo teste)"})

        n = len(all_labels)
        push({"type": "progress_init", "total": n})

        cenarios = []

        # ── Cenário 0: já está carregado, coletar sem mudar ────────────────
        push({"type": "scenario_start", "index": 0, "label": all_labels[0], "total": n})
        push({"type": "log", "msg": f"[1/{n}] Coletando cenário já carregado: {all_labels[0]}"})
        cenario = _collect_scenario(page, all_labels[0], 0, n, wfm, push, scoring_config, veredicto_thresholds)
        cenarios.append(cenario)

        # ── Cenários 1-11: selecionar via dropdown e coletar ────────────────
        for i in range(1, n):
            label = all_labels[i]
            push({"type": "scenario_start", "index": i, "label": label, "total": n})
            push({"type": "log", "msg": f"[{i+1}/{n}] Selecionando: {label}"})

            select_scenario(page, label)
            cenario = _collect_scenario(page, label, i, n, wfm, push, scoring_config, veredicto_thresholds)
            cenarios.append(cenario)

        browser.close()

    v_global = veredicto_global(cenarios)
    result = {
        "arquivo_wfa": filename,
        "veredicto_global": v_global,
        "wfm": wfm,
        "cenarios": cenarios,
    }

    json_path = save_json(result, estrategia=estrategia)
    html_path = save_html(result, estrategia=estrategia)

    json_web = "/" + json_path.replace("\\", "/")
    html_web = "/" + html_path.replace("\\", "/")

    aprovados  = sum(1 for c in cenarios if c["veredicto"]["veredicto"] == "APROVADO")
    atencao    = sum(1 for c in cenarios if c["veredicto"]["veredicto"] == "ATENÇÃO")
    reprovados = sum(1 for c in cenarios if c["veredicto"]["veredicto"] == "REPROVADO")

    push({
        "type": "done",
        "veredicto_global": v_global,
        "json_path": json_web,
        "html_path": html_web,
        "arquivo": filename,
        "aprovados": aprovados,
        "atencao": atencao,
        "reprovados": reprovados,
    })
