import os
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def _slug(name: str) -> str:
    import re
    name = name.strip()
    name = re.sub(r'[\\/:*?"<>|]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name or "estrategia"


def save(data: dict, output_dir: str = "resultados", estrategia: str = "") -> str:
    Path(output_dir).mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slug(estrategia) if estrategia else None
    base = f"Avalia_WFA_{slug}_{timestamp}" if slug else f"relatorio_{timestamp}"
    filepath = os.path.join(output_dir, f"{base}.html")

    templates_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)

    def fmt_pct(v):
        try:
            return f"{float(v):.1f}%"
        except Exception:
            return str(v)

    def fmt_pts(v):
        try:
            return f"{int(v)} pts"
        except Exception:
            return str(v)

    env.filters["fmt_pct"] = fmt_pct
    env.filters["fmt_pts"] = fmt_pts

    template = env.get_template("report.html.j2")
    html = template.render(**data, now=datetime.now().strftime("%d/%m/%Y %H:%M"))

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filepath
