from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timedelta
from typing import List
import os
import sys
import pytz

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db, init_db, Driver, Vehicle, Alert, TZ
from backend.schemas import (
    Driver as DriverSchema, DriverCreate,
    Vehicle as VehicleSchema, VehicleCreate,
    Alert as AlertSchema, AlertCreate,
    AlertWithDetails, DashboardStats
)

def format_brazil_time(dt):
    if dt.tzinfo is None:
        dt = TZ.localize(dt)
    else:
        dt = dt.astimezone(TZ)
    return dt.strftime("%d/%m/%Y %H:%M:%S")

app = FastAPI(title="DriveSafe AI API")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

init_db()

active_connections: List[WebSocket] = []

@app.on_event("startup")
def startup_event():
    db = next(get_db())

    if db.query(Driver).count() == 0:
        sample_driver = Driver(name="João Silva", license_number="SP123456", phone="11999999999")
        db.add(sample_driver)

        sample_driver2 = Driver(name="Maria Santos", license_number="RJ789012", phone="21988888888")
        db.add(sample_driver2)

        sample_vehicle = Vehicle(plate="ABC-1234", model="Volvo FH", type="Caminhão")
        db.add(sample_vehicle)

        sample_vehicle2 = Vehicle(plate="DEF-5678", model="Mercedes-Benz OF", type="Ônibus")
        db.add(sample_vehicle2)

        db.commit()

@app.get("/")
def read_root():
    return FileResponse(os.path.join(BASE_DIR, "dashboard", "index.html"))

@app.get("/api/drivers", response_model=List[DriverSchema])
def get_drivers(db: Session = Depends(get_db)):
    return db.query(Driver).all()

@app.post("/api/drivers", response_model=DriverSchema)
def create_driver(driver: DriverCreate, db: Session = Depends(get_db)):
    db_driver = Driver(**driver.model_dump())
    db.add(db_driver)
    db.commit()
    db.refresh(db_driver)
    return db_driver

@app.get("/api/drivers/{driver_id}", response_model=DriverSchema)
def get_driver(driver_id: int, db: Session = Depends(get_db)):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Motorista não encontrado")
    return driver

@app.get("/api/vehicles", response_model=List[VehicleSchema])
def get_vehicles(db: Session = Depends(get_db)):
    return db.query(Vehicle).all()

@app.post("/api/vehicles", response_model=VehicleSchema)
def create_vehicle(vehicle: VehicleCreate, db: Session = Depends(get_db)):
    db_vehicle = Vehicle(**vehicle.model_dump())
    db.add(db_vehicle)
    db.commit()
    db.refresh(db_vehicle)
    return db_vehicle

@app.get("/api/alerts", response_model=List[AlertWithDetails])
def get_alerts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    alerts = db.query(Alert).order_by(desc(Alert.timestamp)).offset(skip).limit(limit).all()
    result = []
    for alert in alerts:
        alert_dict = AlertWithDetails(
            id=alert.id,
            driver_id=alert.driver_id,
            vehicle_id=alert.vehicle_id,
            alert_type=alert.alert_type,
            risk_level=alert.risk_level,
            duration=alert.duration,
            timestamp=alert.timestamp,
            driver_name=alert.driver.name if alert.driver else None,
            vehicle_plate=alert.vehicle.plate if alert.vehicle else None,
            timestamp_brazil=format_brazil_time(alert.timestamp)
        )
        result.append(alert_dict)
    return result

@app.post("/api/alerts", response_model=AlertSchema)
def create_alert(alert: AlertCreate, db: Session = Depends(get_db)):
    db_alert = Alert(**alert.model_dump())
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)

    for connection in active_connections:
        try:
            alert_dict = AlertWithDetails(
                id=db_alert.id,
                driver_id=db_alert.driver_id,
                vehicle_id=db_alert.vehicle_id,
                alert_type=db_alert.alert_type,
                risk_level=db_alert.risk_level,
                duration=db_alert.duration,
                timestamp=db_alert.timestamp,
                driver_name=db_alert.driver.name if db_alert.driver else None,
                vehicle_plate=db_alert.vehicle.plate if db_alert.vehicle else None,
                timestamp_brazil=format_brazil_time(db_alert.timestamp)
            )
            import json
            connection.send_text(json.dumps({
                "type": "new_alert",
                "data": alert_dict.model_dump()
            }, default=str))
        except:
            pass

    return db_alert

@app.get("/api/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    today = datetime.now(TZ).date()
    start_of_day = datetime.combine(today, datetime.min.time())

    total_alerts_today = db.query(func.count(Alert.id)).filter(Alert.timestamp >= start_of_day).scalar()

    total_drivers = db.query(func.count(Driver.id)).scalar()
    total_vehicles = db.query(func.count(Vehicle.id)).scalar()

    high_risk_alerts = db.query(func.count(Alert.id)).filter(
        Alert.timestamp >= start_of_day,
        Alert.risk_level >= 3
    ).scalar()

    recent_alerts = get_alerts(skip=0, limit=10, db=db)

    return DashboardStats(
        total_alerts_today=total_alerts_today,
        total_drivers=total_drivers,
        total_vehicles=total_vehicles,
        high_risk_alerts=high_risk_alerts,
        recent_alerts=recent_alerts
    )

@app.get("/api/drivers/{driver_id}/alerts")
def get_driver_alerts(driver_id: int, db: Session = Depends(get_db)):
    alerts = db.query(Alert).filter(Alert.driver_id == driver_id).order_by(desc(Alert.timestamp)).all()
    return alerts

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "dashboard", "static")), name="static")
