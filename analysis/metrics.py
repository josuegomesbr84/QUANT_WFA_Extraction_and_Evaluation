import re
import numpy as np


def parse_currency(value: str) -> float:
    """Converte string monetária (R$ 1.234,56 ou -1.234,56) para float."""
    if not value:
        return 0.0
    cleaned = value.replace("R$", "").replace("\xa0", "").strip()
    # Remove separador de milhar (ponto) e troca vírgula decimal por ponto
    cleaned = re.sub(r'\.(?=\d{3})', '', cleaned).replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_percentage(value: str) -> float:
    """Converte string de percentual (72,5% ou -10%) para float."""
    if not value:
        return 0.0
    cleaned = value.replace("%", "").replace(",", ".").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_zscore(zscore_raw: str | None) -> float:
    """Extrai valor numérico do Z-Score a partir do texto bruto."""
    if not zscore_raw:
        return 0.0
    match = re.search(r'-?[\d]+[,.]?[\d]*', str(zscore_raw))
    if match:
        return float(match.group().replace(",", "."))
    return 0.0


def calc_representatividade(oos_values: list[float]) -> dict:
    """
    Representatividade de cada step = |resultado_oos| / |equity_acumulado|.
    Flag quando um único step impacta mais de 25% do equity acumulado naquele ponto.
    """
    equity_acumulado = 0.0
    steps_acima = 0
    max_rep = 0.0
    detalhes = []

    for v in oos_values:
        equity_acumulado += v
        rep = abs(v) / abs(equity_acumulado) if equity_acumulado != 0 else 0.0
        max_rep = max(max_rep, rep)
        if rep > 0.25:
            steps_acima += 1
        detalhes.append(round(rep, 4))

    return {
        "steps_acima_25pct": steps_acima,
        "max_representatividade": round(max_rep, 4),
        "detalhes": detalhes,
    }


def calc_consecutivos_negativos(oos_values: list[float], meses_por_step: float = 0.0) -> dict:
    """
    Detecta sequências de 2+ steps consecutivos negativos.
    Identifica se alguma sequência cobre >= 12 meses (ano negativo).
    """
    max_consecutivos = 0
    atual = 0
    grupos: list[int] = []

    for v in oos_values:
        if v < 0:
            atual += 1
            max_consecutivos = max(max_consecutivos, atual)
        else:
            if atual >= 2:
                grupos.append(atual)
            atual = 0
    if atual >= 2:
        grupos.append(atual)

    tem_ano_negativo = False
    if meses_por_step > 0:
        for g in grupos:
            if g * meses_por_step >= 12:
                tem_ano_negativo = True
                break

    return {
        "max_consecutivos": max_consecutivos,
        "grupos": grupos,
        "qtd_pares_ou_mais": len(grupos),
        "tem_ano_negativo": tem_ano_negativo,
    }


def calc_pct_wfe_positivo(wfe_values: list[float]) -> float:
    """Percentual de steps com WFE > 0."""
    if not wfe_values:
        return 0.0
    positivos = sum(1 for w in wfe_values if w > 0)
    return round(positivos / len(wfe_values) * 100, 2)


def calc_wfe_sem_outliers(wfe_values: list[float]) -> float:
    """WFE médio após remoção de outliers pelo método IQR (1.5×IQR)."""
    if len(wfe_values) < 4:
        return round(float(np.mean(wfe_values)), 2) if wfe_values else 0.0

    arr = np.array(wfe_values, dtype=float)
    q1, q3 = np.percentile(arr, [25, 75])
    iqr = q3 - q1
    filtered = arr[(arr >= q1 - 1.5 * iqr) & (arr <= q3 + 1.5 * iqr)]

    return round(float(np.mean(filtered)) if len(filtered) > 0 else float(np.mean(arr)), 2)


def compute_all_metrics(scenario_data: dict, meses_total: int = 0) -> dict:
    """Calcula todas as métricas analíticas para um cenário."""
    tabela = scenario_data.get("tabela_wfa", [])

    oos_values = [parse_currency(r.get("out_of_sample", "")) for r in tabela]
    wfe_values = [parse_percentage(r.get("wfe", "")) for r in tabela]

    n_steps = len(tabela)
    meses_por_step = (meses_total / n_steps) if n_steps > 0 and meses_total > 0 else 0.0

    zscore = parse_zscore(scenario_data.get("zscore_raw"))
    wfe_medio = round(float(np.mean(wfe_values)), 2) if wfe_values else 0.0
    wfe_sem_outliers = calc_wfe_sem_outliers(wfe_values)
    pct_positivos = calc_pct_wfe_positivo(wfe_values)
    representatividade = calc_representatividade(oos_values)
    consecutivos = calc_consecutivos_negativos(oos_values, meses_por_step)

    return {
        "n_steps": n_steps,
        "zscore": zscore,
        "wfe_medio": wfe_medio,
        "wfe_sem_outliers": wfe_sem_outliers,
        "pct_steps_positivos": pct_positivos,
        "representatividade": representatividade,
        "consecutivos_negativos": consecutivos,
        "oos_values": oos_values,
        "wfe_values": wfe_values,
    }
