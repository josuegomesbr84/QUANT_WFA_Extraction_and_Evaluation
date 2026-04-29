import sys
import asyncio

# No Windows o SelectorEventLoop padrão não suporta subprocessos (Playwright).
# ProactorEventLoop suporta — deve ser definido antes de qualquer loop ser criado.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import json
import logging
import os
import queue as tq
import threading
import traceback
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from scraper.runner import run_with_progress

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("wfa")

Path("tmp").mkdir(exist_ok=True)
Path("resultados").mkdir(exist_ok=True)

# Mapeia job_id → asyncio.Queue (usada pelo SSE)
_jobs: dict[str, asyncio.Queue] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/resultados", StaticFiles(directory="resultados"), name="resultados")


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(Path("templates/index.html").read_text(encoding="utf-8"))


@app.post("/extrair")
async def extrair(
    background_tasks: BackgroundTasks,
    wfa_file: UploadFile = File(...),
    email: str = Form(""),
    password: str = Form(""),
    estrategia: str = Form(""),
    scoring_config: str = Form(""),
    veredicto_thresholds: str = Form(""),
):
    job_id = str(uuid.uuid4())
    async_queue: asyncio.Queue = asyncio.Queue()
    _jobs[job_id] = async_queue

    tmp_path = f"tmp/{job_id}.wfa"
    content = await wfa_file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

    resolved_email = email.strip() or os.getenv("BOTSPOT_EMAIL", "")
    resolved_password = password.strip() or os.getenv("BOTSPOT_PASSWORD", "")
    filename = wfa_file.filename or Path(tmp_path).name

    sc = None
    th = None
    try:
        if scoring_config.strip():
            sc = json.loads(scoring_config)
    except Exception as e:
        log.warning("scoring_config inválido, usando padrão: %s", e)
    try:
        if veredicto_thresholds.strip():
            th = json.loads(veredicto_thresholds)
    except Exception as e:
        log.warning("veredicto_thresholds inválido, usando padrão: %s", e)

    log.info("Job criado: %s  arquivo=%s  estrategia=%r  scoring_custom=%s", job_id, filename, estrategia, sc is not None)
    background_tasks.add_task(
        _run_background, job_id, tmp_path, resolved_email, resolved_password, filename, sc, th, estrategia.strip()
    )
    return {"job_id": job_id}


async def _run_background(
    job_id: str, tmp_path: str, email: str, password: str, filename: str,
    scoring_config=None, veredicto_thresholds=None, estrategia: str = "",
):
    """
    Roda o Playwright em uma thread separada com seu próprio event loop
    (evita conflito com o event loop do uvicorn no Windows).
    Faz bridge da threading.Queue → asyncio.Queue para o SSE.
    """
    log.info("[%s] _run_background iniciado", job_id)
    async_queue = _jobs[job_id]
    sync_q: tq.Queue = tq.Queue()

    def _thread_target():
        log.info("[%s] thread de extração iniciada", job_id)
        try:
            run_with_progress(tmp_path, email, password, filename, sync_q, scoring_config, veredicto_thresholds, estrategia)
        except BaseException as e:
            tb = traceback.format_exc()
            msg = str(e) or repr(e) or type(e).__name__
            log.error("[%s] exceção na thread: %s\n%s", job_id, msg, tb)
            sync_q.put({"type": "error", "msg": msg, "detail": tb})
        finally:
            log.info("[%s] thread de extração encerrada", job_id)

    t = threading.Thread(target=_thread_target, daemon=True)
    t.start()
    log.info("[%s] thread iniciada, entrando no bridge loop", job_id)

    # Bridge: lê da threading.Queue e encaminha para a asyncio.Queue do SSE
    try:
        while True:
            try:
                msg = sync_q.get_nowait()
            except tq.Empty:
                if not t.is_alive():
                    log.warning("[%s] thread morreu sem enviar done/error", job_id)
                    await async_queue.put({
                        "type": "error",
                        "msg": "Thread de extração encerrou inesperadamente",
                        "detail": "",
                    })
                    break
                await asyncio.sleep(0.15)
                continue

            log.debug("[%s] bridge → SSE: %s", job_id, msg.get("type"))
            await async_queue.put(msg)
            if msg.get("type") in ("done", "error"):
                break
    except Exception as exc:
        log.exception("[%s] erro inesperado no bridge: %s", job_id, exc)
        try:
            await async_queue.put({"type": "error", "msg": str(exc), "detail": traceback.format_exc()})
        except Exception:
            pass
    finally:
        t.join(timeout=10)
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        log.info("[%s] _run_background finalizado", job_id)


@app.get("/stream/{job_id}")
async def stream(job_id: str):
    if job_id not in _jobs:
        log.warning("SSE: job não encontrado: %s", job_id)
        return HTMLResponse("Job não encontrado", status_code=404)

    log.info("SSE conectado: %s", job_id)
    queue = _jobs[job_id]

    async def event_generator():
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=120.0)
                except asyncio.TimeoutError:
                    yield "data: {\"type\":\"ping\"}\n\n"
                    continue

                try:
                    data = json.dumps(msg, ensure_ascii=False)
                except Exception as enc_err:
                    log.error("SSE json.dumps falhou: %s", enc_err)
                    data = json.dumps({"type": "error", "msg": f"Falha de serialização: {enc_err}", "detail": ""})

                yield f"data: {data}\n\n"
                log.debug("SSE enviou: %s", msg.get("type"))

                if msg.get("type") in ("done", "error"):
                    _jobs.pop(job_id, None)
                    break
        except asyncio.CancelledError:
            log.info("SSE cancelado (cliente desconectou): %s", job_id)
        except Exception as exc:
            log.exception("SSE erro inesperado: %s", exc)
            try:
                yield f"data: {json.dumps({'type': 'error', 'msg': str(exc), 'detail': traceback.format_exc()})}\n\n"
            except Exception:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/test-sse")
async def test_sse():
    """Endpoint de teste: envia 3 eventos SSE e encerra. Útil para diagnóstico."""
    async def gen():
        for i in range(3):
            yield f"data: {json.dumps({'type': 'log', 'msg': f'Teste SSE #{i+1}'})}\n\n"
            await asyncio.sleep(0.5)
        yield f"data: {json.dumps({'type': 'done', 'msg': 'SSE OK'})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if __name__ == "__main__":
    import webbrowser
    import uvicorn

    def _open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:8000")

    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
