from config import SCORING, VEREDICTO_THRESHOLDS


def _score_por_minimo(value: float, faixas: list[dict]) -> int:
    """Seleciona pontuação pela primeira faixa cujo mínimo o valor atinge (ordem decrescente)."""
    for faixa in faixas:
        if value >= faixa["minimo"]:
            return faixa["pts"]
    return 0


def _score_por_maximo(value: float, faixas: list[dict]) -> int:
    """Seleciona pontuação pela primeira faixa cujo máximo o valor não ultrapassa (ordem crescente).
    Usado para métricas inversas onde menor valor é melhor (ex: representatividade)."""
    for faixa in faixas:
        if value <= faixa["maximo"]:
            return faixa["pts"]
    return faixas[-1]["pts"]


def score_representatividade(max_rep_pct: float) -> int:
    """Pontuação de representatividade baseada no step mais dominante (% do equity final)."""
    faixas = SCORING["representatividade"]["faixas"]
    return _score_por_maximo(max_rep_pct, faixas)


def score_consecutivos(max_consec: int, tem_ano_negativo: bool, qtd_pares: int) -> int:
    faixas = SCORING["consecutivos_negativos"]["faixas"]
    if max_consec < 2:
        return faixas[0]["pts"]  # nenhum par negativo
    if qtd_pares >= 2:
        return 0                 # dois ou mais pares
    if tem_ano_negativo:
        return faixas[2]["pts"]  # par longo (≥ 12 meses)
    return faixas[1]["pts"]      # par curto (< 12 meses)


def score_pct_positivos(pct: float) -> int:
    return _score_por_minimo(pct, SCORING["pct_wfe_positivo"]["faixas"])


def score_zscore(zscore: float) -> int:
    return _score_por_minimo(zscore, SCORING["zscore"]["faixas"])


def score_wfe_medio(wfe: float) -> int:
    return _score_por_minimo(wfe, SCORING["wfe_medio"]["faixas"])


def score_wfe_sem_outliers(wfe: float) -> int:
    return _score_por_minimo(wfe, SCORING["wfe_sem_outliers"]["faixas"])


def _score_categorico(valor: str, cfg: dict) -> int:
    """Scoring por valor categórico (ex: Alta / Média / Baixa)."""
    key = (valor or "").strip().lower()
    return cfg.get("pts", {}).get(key, cfg.get("default", 0))


def calcular_veredicto(metrics: dict, scoring=None, thresholds=None) -> dict:
    """Calcula pontuação total e veredicto para um cenário.

    Args:
        metrics: dicionário com métricas calculadas pelo analysis.metrics.
        scoring: configuração de pontuação customizada (mesma estrutura de config.SCORING).
                 Se None, usa config.SCORING.
        thresholds: thresholds de veredicto customizados (mesma estrutura de config.VEREDICTO_THRESHOLDS).
                    Se None, usa config.VEREDICTO_THRESHOLDS.
    """
    sc = scoring if scoring is not None else SCORING
    th = thresholds if thresholds is not None else VEREDICTO_THRESHOLDS

    rep = metrics["representatividade"]
    consec = metrics["consecutivos_negativos"]

    # ── Representatividade ────────────────────────────────────────────────────
    rep_faixas = sc["representatividade"]["faixas"]
    max_rep_pct = rep["max_representatividade"] * 100   # fração → percentual
    r_pts = _score_por_maximo(max_rep_pct, rep_faixas)

    # ── Consecutivos Negativos ────────────────────────────────────────────────
    consec_faixas = sc["consecutivos_negativos"]["faixas"]
    max_consec = consec["max_consecutivos"]
    tem_ano = consec["tem_ano_negativo"]
    qtd_pares = consec["qtd_pares_ou_mais"]
    if max_consec < 2:
        c_pts = consec_faixas[0]["pts"]   # nenhum par
    elif qtd_pares >= 2:
        c_pts = consec_faixas[3]["pts"]   # dois ou mais pares
    elif tem_ano:
        c_pts = consec_faixas[2]["pts"]   # par longo / ano negativo
    else:
        c_pts = consec_faixas[1]["pts"]   # par curto

    scores = {
        "representatividade": r_pts,
        "consecutivos_negativos": c_pts,
        "pct_steps_positivos": _score_por_minimo(
            metrics["pct_steps_positivos"], sc["pct_wfe_positivo"]["faixas"]
        ),
        "zscore": _score_por_minimo(metrics["zscore"], sc["zscore"]["faixas"]),
        "wfe_medio": _score_por_minimo(metrics["wfe_medio"], sc["wfe_medio"]["faixas"]),
        "wfe_sem_outliers": _score_por_minimo(
            metrics["wfe_sem_outliers"], sc["wfe_sem_outliers"]["faixas"]
        ),
        "significancia": _score_categorico(
            metrics.get("significancia", ""), sc.get("significancia", SCORING["significancia"])
        ),
    }

    total = sum(scores.values())

    if total >= th["aprovado"]:
        veredicto = "APROVADO"
    elif total >= th["atencao"]:
        veredicto = "ATENÇÃO"
    else:
        veredicto = "REPROVADO"

    return {"scores": scores, "total": total, "veredicto": veredicto}


def veredicto_global(cenarios: list[dict]) -> dict:
    """Veredicto global baseado na distribuição dos veredictos individuais.

    Retorna dict com:
        veredicto: "APROVADO" | "ATENÇÃO" | "REPROVADO"
        pct_aprovados: int (0-100)
        contagem: dict com contagens por veredicto
        comentario: str com insight sobre melhor configuração OOS
    """
    contagem = {"APROVADO": 0, "ATENÇÃO": 0, "REPROVADO": 0}
    for c in cenarios:
        v = c.get("veredicto", {}).get("veredicto", "REPROVADO")
        contagem[v] = contagem.get(v, 0) + 1

    total = len(cenarios)
    if total == 0:
        return {"veredicto": "REPROVADO", "pct_aprovados": 0, "contagem": contagem, "comentario": ""}

    pct_aprovados = round(contagem["APROVADO"] / total * 100)

    if contagem["APROVADO"] / total > 0.5:
        veredicto = "APROVADO"
    elif contagem["REPROVADO"] / total >= 0.5:
        veredicto = "REPROVADO"
    else:
        veredicto = "ATENÇÃO"

    return {
        "veredicto": veredicto,
        "pct_aprovados": pct_aprovados,
        "contagem": contagem,
        "comentario": _gerar_comentario(cenarios),
    }


def _gerar_comentario(cenarios: list[dict]) -> str:
    """Detecta qual configuração de OOS obteve melhor pontuação média."""
    from analysis.metrics import parse_percentage

    grupos: dict[str, list[int]] = {}
    for c in cenarios:
        wfm_row = c.get("wfm_row") or {}
        oos_pct = parse_percentage(wfm_row.get("out_of_sample", ""))
        if not oos_pct:
            continue

        meses = 0
        try:
            meses = int(str(c.get("cards", {}).get("meses") or "0"))
        except Exception:
            pass
        steps = len(c.get("tabela_wfa", []))

        if meses > 0 and steps > 0:
            n = round(meses * (oos_pct / 100) / steps)
            key = f"{n} mês" if n == 1 else f"{n} meses"
        else:
            key = f"{oos_pct:.0f}% OOS"

        score = c.get("veredicto", {}).get("total", 0)
        grupos.setdefault(key, []).append(score)

    if len(grupos) < 2:
        return ""

    melhor = max(grupos, key=lambda k: sum(grupos[k]) / len(grupos[k]))
    avg = round(sum(grupos[melhor]) / len(grupos[melhor]))
    return f"Melhores resultados nos WFCs com OOS de {melhor} (média {avg} pts)."
