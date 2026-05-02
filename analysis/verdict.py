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

    # --- Regras de veto (sobrepõem pontuação) ---
    vetos = []

    rep_detalhes = metrics.get("representatividade", {}).get("detalhes", [])
    steps_acima_30 = sum(1 for d in rep_detalhes if d > 0.30)
    if steps_acima_30 > 2:
        vetos.append("representatividade")

    if metrics.get("zscore", 0) < 2.5:
        vetos.append("zscore")

    if metrics.get("consecutivos_negativos", {}).get("tem_ano_negativo", False):
        vetos.append("ano_negativo")

    if metrics.get("wfe_sem_outliers", 0) < 50:
        vetos.append("wfe_sem_outliers")

    if metrics.get("wfe_medio", 0) < 50:
        vetos.append("wfe_medio")

    if vetos:
        veredicto = "REPROVADO"

    return {"scores": scores, "total": total, "veredicto": veredicto, "vetos": vetos}


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
    """Conta quantos WFCs foram vetados por cada regra de veto."""
    _LABELS = {
        "zscore":             "WFC(s) reprovados por Z-Score < 2,5",
        "representatividade": "WFC(s) reprovados por concentração de lucro (representatividade)",
        "ano_negativo":       "WFC(s) reprovados por ano negativo",
        "wfe_sem_outliers":   "WFC(s) reprovados por WFE s/ Outliers < 50%",
        "wfe_medio":          "WFC(s) reprovados por WFE Médio < 50%",
    }
    contadores = {k: 0 for k in _LABELS}
    for c in cenarios:
        for v in c.get("veredicto", {}).get("vetos", []):
            if v in contadores:
                contadores[v] += 1

    linhas = [
        f"{contadores[k]} {label}"
        for k, label in _LABELS.items()
        if contadores[k] > 0
    ]
    return "\n".join(linhas)
