BASE_URL = "https://botspot.com.br"
LOGIN_URL = f"{BASE_URL}/login"
UPLOAD_URL = f"{BASE_URL}/wfa"
REPORT_URL = f"{BASE_URL}/wfareport"

TIMEOUTS = {
    "login": 15_000,
    "upload": 900_000,   # 15 min — processamento do WFA pode levar 5-10 min
    "page_load": 45_000,
    "scenario_switch": 45_000,
    "spinner_appear": 5_000,
}

# Faixas em ordem decrescente de valor (primeira faixa que o valor atinge é usada)
SCORING = {
    "representatividade": {
        "max": 15,
        "tipo": "max_rep_pct",   # scoring via _score_por_maximo em verdict.py
        "faixas": [
            {"maximo": 25.0, "pts": 15},    # max_rep ≤ 25% → excelente consistência
            {"maximo": 30.0, "pts": 6},     # max_rep ≤ 30% → aceitável
            {"maximo": 9999.0, "pts": -15}, # max_rep > 30% → grave instabilidade (penalidade)
        ],
    },
    "consecutivos_negativos": {
        "max": 15,
        "faixas": [
            {"condicao": "nenhum", "pts": 15},
            {"condicao": "par_curto", "pts": 9},
            {"condicao": "par_longo_ou_ano", "pts": -15},
            {"condicao": "dois_ou_mais_pares", "pts": 0},
        ],
    },
    "pct_wfe_positivo": {
        "max": 15,
        "faixas": [
            {"minimo": 70.0, "pts": 15},
            {"minimo": 65.0, "pts": 8},
            {"minimo": 50.0, "pts": 4},
            {"minimo": 49.0, "pts": -15},
            {"minimo": 0.0,  "pts": 0},
        ],
    },
    "zscore": {
        "max": 15,
        "faixas": [
            {"minimo": 3.0, "pts": 15},
            {"minimo": 2.7, "pts": 7},
            {"minimo": 2.5, "pts": 5},
            {"minimo": 2.49, "pts": -15},
            {"minimo": 0.0, "pts": 0},
        ],
    },
    "wfe_medio": {
        "max": 15,
        "faixas": [
            {"minimo": 70.0, "pts": 15},
            {"minimo": 65.0, "pts": 8},
            {"minimo": 50.0, "pts": 5},
            {"minimo": 49.9, "pts": -15},
            {"minimo": 0.0,  "pts": 0},
        ],
    },
    "wfe_sem_outliers": {
        "max": 15,
        "faixas": [
            {"minimo": 70.0, "pts": 15},
            {"minimo": 65.0, "pts": 12},
            {"minimo": 50.0, "pts": 9},
            {"minimo": 49.9, "pts": -15},
            {"minimo": 0.0,  "pts": 0},
        ],
    },
    "significancia": {
        "max": 10,
        "tipo": "categorico",
        "pts": {
            "alta":  10,
            "media": 5,    # normalizado sem acento (Média → media)
            "baixa": -5,
        },
        "default": 0,      # valor não reconhecido ou ausente
    },
}

VEREDICTO_THRESHOLDS = {
    "aprovado": 75,
    "atencao": 50,
}
