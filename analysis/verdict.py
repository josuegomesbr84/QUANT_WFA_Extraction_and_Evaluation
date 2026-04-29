from config import SCORING, VEREDICTO_THRESHOLDS


def _score_por_minimo(value: float, faixas: list[dict]) -> int:
    """Seleciona pontuação pela primeira faixa cujo mínimo o valor atinge (ordem decrescente)."""
    for faixa in faixas:
        if value >= faixa["minimo"]:
            return faixa["pts"]
    return 0


def score_representatividade(steps_acima: int) -> int:
    faixas = SCORING["representatividade"]["faixas"]
    if steps_acima == 0:
        return faixas[0]["pts"]
    if steps_acima == 1:
        return faixas[1]["pts"]
    return 0


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
    steps_acima = rep["steps_acima_25pct"]
    if steps_acima == 0:
        r_pts = rep_faixas[0]["pts"]
    elif steps_acima == 1:
        r_pts = rep_faixas[1]["pts"]
    else:
        r_pts = rep_faixas[2]["pts"]

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
    }

    total = sum(scores.values())

    if total >= th["aprovado"]:
        veredicto = "APROVADO"
    elif total >= th["atencao"]:
        veredicto = "ATENÇÃO"
    else:
        veredicto = "REPROVADO"

    return {"scores": scores, "total": total, "veredicto": veredicto}


def veredicto_global(cenarios: list[dict]) -> str:
    """Veredicto global baseado na distribuição dos veredictos individuais."""
    contagem = {"APROVADO": 0, "ATENÇÃO": 0, "REPROVADO": 0}
    for c in cenarios:
        v = c.get("veredicto", {}).get("veredicto", "REPROVADO")
        contagem[v] = contagem.get(v, 0) + 1

    total = len(cenarios)
    if total == 0:
        return "REPROVADO"

    if contagem["APROVADO"] / total > 0.5:
        return "APROVADO"
    if contagem["REPROVADO"] / total >= 0.5:
        return "REPROVADO"
    return "ATENÇÃO"
