"""Modo teste (só admin): monitoramento ao vivo neste computador, marcação de piscadas e análise de vídeo."""
import socket
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy.orm import Session

from backend import config
from backend.auth import Principal, audit, require_roles
from backend.database import Company, Device, Driver, Vehicle, get_db
from backend.schemas import AnalysisOut, MarkIn, TestStartIn, TestStateOut
from backend.security import generate_device_token
from backend.test_session import AnalysisJobs, LiveTestSession, availability

router = APIRouter(prefix="/api/test-mode", tags=["modo teste"])
admin_only = require_roles("admin")
session = LiveTestSession()
jobs = AnalysisJobs(Path(config.ANALYSES_DIR))


def state_out() -> TestStateOut:
    available, reason = availability()
    return TestStateOut(available=available, reason=reason, **session.state())


def shutdown() -> None:
    session.stop(wait=True)


@router.get("", response_model=TestStateOut)
def test_state(principal: Principal = Depends(admin_only)):
    return state_out()


@router.post("/start", response_model=TestStateOut)
def start_test(payload: TestStartIn, request: Request, principal: Principal = Depends(admin_only),
               db: Session = Depends(get_db)):
    available, reason = availability()
    if not available:
        raise HTTPException(status_code=409, detail=reason)
    if session.running:
        raise HTTPException(status_code=409, detail="Já existe um teste rodando. Pare antes de começar outro.")
    company = db.get(Company, payload.company_id)
    if company is None:
        raise HTTPException(status_code=400, detail="Escolha a empresa do teste.")
    for model, value, label in ((Driver, payload.driver_id, "Motorista"), (Vehicle, payload.vehicle_id, "Veículo")):
        if value and (db.get(model, value) is None or db.get(model, value).company_id != company.id):
            raise HTTPException(status_code=400, detail=f"{label} não pertence a esta empresa.")

    # Um "dispositivo de testes" por computador e empresa; token novo a cada teste.
    name = f"Computador de testes ({socket.gethostname()})"[:100]
    device = db.query(Device).filter(Device.company_id == company.id, Device.name == name).first()
    token, token_hash, prefix = generate_device_token()
    if device is None:
        device = Device(company_id=company.id, name=name, token_hash=token_hash, token_prefix=prefix)
        db.add(device)
    else:
        device.token_hash, device.token_prefix, device.revoked_at = token_hash, prefix, None
    device.driver_id = payload.driver_id or None
    device.vehicle_id = payload.vehicle_id or None
    db.flush()
    audit(db, principal, "teste_iniciado", target=f"dispositivo:{device.id}", details={"camera": payload.camera},
          request=request, company_id=company.id)
    db.commit()

    port = (request.scope.get("server") or ("127.0.0.1", 8000))[1]
    server_url = config.INTERNAL_URL or f"http://127.0.0.1:{port}"
    try:
        session.start(payload.model_dump(), device.id, token, server_url)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return state_out()


@router.post("/stop", response_model=TestStateOut)
def stop_test(principal: Principal = Depends(admin_only)):
    session.stop(wait=True)
    return state_out()


@router.post("/recalibrate", status_code=204)
def recalibrate_test(principal: Principal = Depends(admin_only)):
    if not session.running:
        raise HTTPException(status_code=409, detail="Nenhum teste rodando.")
    session.recalibrate()


@router.post("/marks", status_code=201)
def add_mark(payload: MarkIn, principal: Principal = Depends(admin_only)):
    try:
        mark = session.mark(payload.kind, payload.note)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"mark": mark, "total": len(session.marks)}


def _csv_download(content: str, filename: str) -> Response:
    return Response(content.encode("utf-8"), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/marks.csv")
def download_marks(principal: Principal = Depends(admin_only)):
    return _csv_download(session.marks_csv(), "teste-marcacoes.csv")


@router.get("/blinks.csv")
def download_blinks(principal: Principal = Depends(admin_only)):
    return _csv_download(session.blinks_csv(), "teste-piscadas.csv")


@router.get("/blink-check")
def blink_check(tolerance: float = Query(0.6, ge=0.1, le=2.0), principal: Principal = Depends(admin_only)):
    return session.blink_check(tolerance)


@router.get("/video.mjpg")
def live_video(principal: Principal = Depends(admin_only)):
    if not session.running:
        raise HTTPException(status_code=404, detail="Nenhum teste rodando.")
    return StreamingResponse(session.mjpeg(), media_type="multipart/x-mixed-replace; boundary=frame",
                             headers={"Cache-Control": "no-store"})


@router.put("/analyses", response_model=AnalysisOut, status_code=201)
async def upload_analysis(request: Request, name: str = Query(..., min_length=3, max_length=200), phone: bool = False,
                          principal: Principal = Depends(admin_only)):
    try:
        job = jobs.new(name, phone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    size = 0
    try:
        with open(jobs.video_path(job), "wb") as handle:
            async for chunk in request.stream():
                size += len(chunk)
                if size > config.MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="O vídeo passou do tamanho máximo permitido.")
                handle.write(chunk)
    except BaseException:
        jobs.discard(job["id"])
        raise
    if size == 0:
        jobs.discard(job["id"])
        raise HTTPException(status_code=400, detail="O arquivo chegou vazio.")
    jobs.run(job["id"])
    return AnalysisOut(**jobs.public(job))


@router.get("/analyses", response_model=List[AnalysisOut])
def list_analyses(principal: Principal = Depends(admin_only)):
    return [AnalysisOut(**job) for job in jobs.list()]


@router.get("/analyses/{job_id}", response_model=AnalysisOut)
def get_analysis(job_id: str, principal: Principal = Depends(admin_only)):
    job = jobs.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")
    return AnalysisOut(**jobs.public(job))


@router.get("/analyses/{job_id}/files/{name}")
def download_analysis_file(job_id: str, name: str, principal: Principal = Depends(admin_only)):
    path = jobs.file_path(job_id, name)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    return FileResponse(path, filename=name)
