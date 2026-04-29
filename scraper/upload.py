import time
from pathlib import Path
from playwright.sync_api import Page
from config import UPLOAD_URL, TIMEOUTS


def send_wfa(page: Page, wfa_path: str) -> None:
    path = Path(wfa_path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {wfa_path}")

    page.goto(UPLOAD_URL)
    page.wait_for_load_state("networkidle", timeout=TIMEOUTS["page_load"])

    # Aguarda o dropzone estar disponível
    page.wait_for_selector(".dropzone", timeout=TIMEOUTS["page_load"])

    # Dropzone.js usa um input[type="file"] oculto internamente.
    # set_input_files funciona em elementos ocultos e dispara o evento change
    # que o Dropzone.js ouve para registrar o arquivo.
    page.locator('input[type="file"]').first.set_input_files(str(path))

    # Aguarda o Dropzone.js processar o arquivo (thumbnail aparece)
    time.sleep(1.5)

    # Clica em "Enviar"
    page.locator('button:has-text("Enviar")').first.click()

    # Aguarda a URL mudar para /wfareport.
    # BotSpot é uma SPA React com roteamento client-side (history.pushState):
    # o evento 'load' nunca dispara após a navegação, por isso usamos
    # wait_until="commit" (só confirma a mudança de URL) + polling manual.
    page.wait_for_function(
        "() => window.location.pathname.includes('wfareport')",
        timeout=TIMEOUTS["upload"],
    )

    # Aguarda os dados carregarem na nova rota
    page.wait_for_load_state("networkidle", timeout=TIMEOUTS["page_load"])
    page.wait_for_selector(".card", timeout=TIMEOUTS["page_load"])
