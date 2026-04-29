import json
import os
from datetime import datetime
from pathlib import Path


class _SafeEncoder(json.JSONEncoder):
    """Garante serialização de tipos numpy e outros não-padrão."""
    def default(self, obj):
        try:
            import numpy as np
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
        except ImportError:
            pass
        return super().default(obj)


def _slug(name: str) -> str:
    """Remove caracteres inválidos para nome de arquivo e substitui espaços por _."""
    import re
    name = name.strip()
    name = re.sub(r'[\\/:*?"<>|]', '', name)   # chars proibidos no Windows
    name = re.sub(r'\s+', '_', name)             # espaços → underscore
    return name or "estrategia"


def save(data: dict, output_dir: str = "resultados", estrategia: str = "") -> str:
    Path(output_dir).mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slug(estrategia) if estrategia else None
    base = f"Avalia_WFA_{slug}_{timestamp}" if slug else f"resultado_{timestamp}"
    filepath = os.path.join(output_dir, f"{base}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, cls=_SafeEncoder)

    return filepath
