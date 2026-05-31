from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class DriverBase(BaseModel):
    name: str
    license_number: str
    phone: Optional[str] = None

class DriverCreate(DriverBase):
    pass

class Driver(DriverBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class VehicleBase(BaseModel):
    plate: str
    model: str
    type: str

class VehicleCreate(VehicleBase):
    pass

class Vehicle(VehicleBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class AlertBase(BaseModel):
    alert_type: str
    risk_level: int
    duration: float

class AlertCreate(AlertBase):
    driver_id: int
    vehicle_id: int

class Alert(AlertBase):
    id: int
    driver_id: int
    vehicle_id: int
    timestamp: datetime
    
    class Config:
        from_attributes = True

class AlertWithDetails(Alert):
    driver_name: Optional[str] = None
    vehicle_plate: Optional[str] = None
    timestamp_brazil: Optional[str] = None

class DashboardStats(BaseModel):
    total_alerts_today: int
    total_drivers: int
    total_vehicles: int
    high_risk_alerts: int
    recent_alerts: List[AlertWithDetails]
