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
        "max": 20,
        "faixas": [
            {"condicao": "zero", "pts": 20},
            {"condicao": "um", "pts": 8},
            {"condicao": "dois_ou_mais", "pts": 0},
        ],
    },
    "consecutivos_negativos": {
        "max": 20,
        "faixas": [
            {"condicao": "nenhum", "pts": 20},
            {"condicao": "par_curto", "pts": 12},
            {"condicao": "par_longo_ou_ano", "pts": 4},
            {"condicao": "dois_ou_mais_pares", "pts": 0},
        ],
    },
    "pct_wfe_positivo": {
        "max": 20,
        "faixas": [
            {"minimo": 80.0, "pts": 20},
            {"minimo": 65.0, "pts": 17},
            {"minimo": 50.0, "pts": 13},
            {"minimo": 35.0, "pts": 6},
            {"minimo": 0.0,  "pts": 0},
        ],
    },
    "zscore": {
        "max": 15,
        "faixas": [
            {"minimo": 5.0, "pts": 15},
            {"minimo": 4.0, "pts": 12},
            {"minimo": 3.0, "pts": 9},
            {"minimo": 2.0, "pts": 4},
            {"minimo": 0.0, "pts": 0},
        ],
    },
    "wfe_medio": {
        "max": 13,
        "faixas": [
            {"minimo": 90.0, "pts": 13},
            {"minimo": 80.0, "pts": 11},
            {"minimo": 70.0, "pts": 8},
            {"minimo": 60.0, "pts": 4},
            {"minimo": 0.0,  "pts": 0},
        ],
    },
    "wfe_sem_outliers": {
        "max": 12,
        "faixas": [
            {"minimo": 90.0, "pts": 12},
            {"minimo": 80.0, "pts": 10},
            {"minimo": 70.0, "pts": 7},
            {"minimo": 60.0, "pts": 3},
            {"minimo": 0.0,  "pts": 0},
        ],
    },
}

VEREDICTO_THRESHOLDS = {
    "aprovado": 75,
    "atencao": 50,
}
