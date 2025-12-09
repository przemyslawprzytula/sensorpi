"""FastAPI server for the greenhouse dashboard.

This runs on the server (192.168.1.20), provides:
- REST API for sensor data and configuration
- WebSocket for real-time updates
- Static file serving for web dashboard
- Proxy to RPi API for relay control
"""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import httpx
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import Session, sessionmaker

from sensorpi.api import schemas
from sensorpi.config.settings import Settings
from sensorpi.database import models

LOGGER = logging.getLogger(__name__)

# Global state
_settings: Settings | None = None
_engine = None
_SessionLocal = None
_rpi_base_url: str = ""

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        LOGGER.info("WebSocket client connected. Total: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        LOGGER.info("WebSocket client disconnected. Total: %d", len(self.active_connections))

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        if not self.active_connections:
            return
        data = json.dumps(message, default=str)
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except Exception:
                disconnected.add(connection)
        # Clean up disconnected
        for conn in disconnected:
            self.active_connections.discard(conn)


manager = ConnectionManager()


def get_db() -> Session:
    """Get database session."""
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized")
    db = _SessionLocal()
    try:
        return db
    finally:
        pass  # Session managed by caller


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    global _settings, _engine, _SessionLocal, _rpi_base_url

    # Load settings
    _settings = Settings()

    # Initialize database
    _engine = create_engine(_settings.database.dsn, pool_pre_ping=True)
    _SessionLocal = sessionmaker(bind=_engine)

    # RPi API URL
    rpi_cfg = _settings.get("rpi", {})
    rpi_host = rpi_cfg.get("host", "192.168.1.200")
    rpi_port = rpi_cfg.get("port", 5000)
    _rpi_base_url = f"http://{rpi_host}:{rpi_port}"

    LOGGER.info("Server API starting, RPi API at %s", _rpi_base_url)

    # Start background task for polling new readings
    task = asyncio.create_task(poll_new_readings())

    yield

    # Shutdown
    task.cancel()
    if _engine:
        _engine.dispose()


app = FastAPI(
    title="SensorPi Greenhouse Dashboard",
    description="API for greenhouse monitoring and control",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Health & Status ---

@app.get("/api/health", response_model=schemas.HealthResponse)
async def health_check():
    """Check system health."""
    db_ok = False
    rpi_ok = False

    # Check database
    try:
        db = get_db()
        db.execute(models.Sensor.__table__.select().limit(1))
        db.close()
        db_ok = True
    except Exception as e:
        LOGGER.error("Database health check failed: %s", e)

    # Check RPi API
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{_rpi_base_url}/health")
            rpi_ok = resp.status_code == 200
    except Exception as e:
        LOGGER.debug("RPi health check failed: %s", e)

    return schemas.HealthResponse(
        status="ok" if (db_ok and rpi_ok) else "degraded",
        database=db_ok,
        rpi_api=rpi_ok,
    )


@app.get("/api/status", response_model=schemas.SystemStatus)
async def system_status():
    """Get overall system status."""
    db = get_db()
    try:
        sensor_count = db.query(func.count(models.Sensor.id)).scalar() or 0
        reading_count = db.query(func.count(models.SensorReading.id)).scalar() or 0

        latest = db.query(models.SensorReading).order_by(
            desc(models.SensorReading.recorded_at)
        ).first()

        # Check RPi connection
        rpi_connected = False
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{_rpi_base_url}/health")
                rpi_connected = resp.status_code == 200
        except Exception:
            pass

        return schemas.SystemStatus(
            rpi_connected=rpi_connected,
            rpi_address=_rpi_base_url,
            database_connected=True,
            sensor_count=sensor_count,
            reading_count=reading_count,
            automation_enabled=_settings.automation.get("enabled", False) if _settings else False,
            last_reading_at=latest.recorded_at if latest else None,
        )
    finally:
        db.close()


# --- Sensors ---

@app.get("/api/sensors", response_model=List[schemas.SensorWithLatestReading])
async def get_sensors():
    """Get all sensors with their latest readings."""
    db = get_db()
    try:
        sensors = db.query(models.Sensor).all()
        result = []

        for sensor in sensors:
            latest = db.query(models.SensorReading).filter(
                models.SensorReading.sensor_fk == sensor.id
            ).order_by(desc(models.SensorReading.recorded_at)).first()

            result.append(schemas.SensorWithLatestReading(
                id=sensor.id,
                sensor_id=sensor.sensor_id,
                sensor_type=sensor.sensor_type.value,
                measurement=sensor.measurement,
                unit=sensor.unit,
                location=sensor.location,
                created_at=sensor.created_at,
                latest_value=latest.value if latest else None,
                latest_recorded_at=latest.recorded_at if latest else None,
            ))

        return result
    finally:
        db.close()


@app.get("/api/sensors/{sensor_id}", response_model=schemas.SensorWithLatestReading)
async def get_sensor(sensor_id: str):
    """Get single sensor by ID."""
    db = get_db()
    try:
        sensor = db.query(models.Sensor).filter(
            models.Sensor.sensor_id == sensor_id
        ).first()

        if not sensor:
            raise HTTPException(status_code=404, detail=f"Sensor {sensor_id} not found")

        latest = db.query(models.SensorReading).filter(
            models.SensorReading.sensor_fk == sensor.id
        ).order_by(desc(models.SensorReading.recorded_at)).first()

        return schemas.SensorWithLatestReading(
            id=sensor.id,
            sensor_id=sensor.sensor_id,
            sensor_type=sensor.sensor_type.value,
            measurement=sensor.measurement,
            unit=sensor.unit,
            location=sensor.location,
            created_at=sensor.created_at,
            latest_value=latest.value if latest else None,
            latest_recorded_at=latest.recorded_at if latest else None,
        )
    finally:
        db.close()


@app.get("/api/sensors/{sensor_id}/readings", response_model=List[schemas.SensorReadingResponse])
async def get_sensor_readings(
    sensor_id: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = Query(default=100, le=1000),
):
    """Get readings for a sensor."""
    db = get_db()
    try:
        sensor = db.query(models.Sensor).filter(
            models.Sensor.sensor_id == sensor_id
        ).first()

        if not sensor:
            raise HTTPException(status_code=404, detail=f"Sensor {sensor_id} not found")

        query = db.query(models.SensorReading).filter(
            models.SensorReading.sensor_fk == sensor.id
        )

        if start:
            query = query.filter(models.SensorReading.recorded_at >= start)
        if end:
            query = query.filter(models.SensorReading.recorded_at <= end)

        readings = query.order_by(
            desc(models.SensorReading.recorded_at)
        ).limit(limit).all()

        return [
            schemas.SensorReadingResponse(
                id=r.id,
                sensor_fk=r.sensor_fk,
                value=r.value,
                recorded_at=r.recorded_at,
            )
            for r in reversed(readings)  # Return in chronological order
        ]
    finally:
        db.close()


@app.get("/api/sensors/{sensor_id}/timeseries", response_model=schemas.SensorTimeSeries)
async def get_sensor_timeseries(
    sensor_id: str,
    hours: int = Query(default=24, le=168),  # Max 1 week
):
    """Get time series data for charting."""
    db = get_db()
    try:
        sensor = db.query(models.Sensor).filter(
            models.Sensor.sensor_id == sensor_id
        ).first()

        if not sensor:
            raise HTTPException(status_code=404, detail=f"Sensor {sensor_id} not found")

        start_time = datetime.utcnow() - timedelta(hours=hours)

        readings = db.query(models.SensorReading).filter(
            models.SensorReading.sensor_fk == sensor.id,
            models.SensorReading.recorded_at >= start_time,
        ).order_by(models.SensorReading.recorded_at).all()

        return schemas.SensorTimeSeries(
            sensor_id=sensor.sensor_id,
            sensor_type=sensor.sensor_type.value,
            unit=sensor.unit,
            location=sensor.location,
            data=[
                schemas.TimeSeriesPoint(timestamp=r.recorded_at, value=r.value)
                for r in readings
            ],
        )
    finally:
        db.close()


# --- Relays (proxy to RPi) ---

@app.get("/api/relays", response_model=schemas.RelaysResponse)
async def get_relays():
    """Get all relay states from RPi."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{_rpi_base_url}/relays")
            resp.raise_for_status()
            data = resp.json()

            return schemas.RelaysResponse(
                relays=[
                    schemas.RelayInfo(
                        id=r["id"],
                        name=r["name"],
                        state=r["state"],
                        pin=r.get("pin"),
                    )
                    for r in data["relays"]
                ],
                dependencies=data.get("dependencies", {}),
                nc_wiring=data.get("nc_wiring", False),
            )
    except httpx.HTTPError as e:
        LOGGER.error("Failed to get relays from RPi: %s", e)
        raise HTTPException(status_code=503, detail="RPi API unavailable")


@app.post("/api/relays/{device_id}", response_model=schemas.RelaySetResponse)
async def set_relay(device_id: str, request: schemas.RelaySetRequest):
    """Set relay state on RPi."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{_rpi_base_url}/relays/{device_id}",
                json={"state": request.state.value},
            )

            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Relay {device_id} not found")
            resp.raise_for_status()

            data = resp.json()

            # Broadcast relay update to WebSocket clients
            await manager.broadcast({
                "type": "relay_update",
                "data": {
                    "relay_id": device_id,
                    "state": request.state.value,
                    "changed_by": "api",
                },
                "timestamp": datetime.utcnow().isoformat(),
            })

            return schemas.RelaySetResponse(
                id=data["id"],
                state=data["state"],
                message=data["message"],
            )
    except httpx.HTTPError as e:
        LOGGER.error("Failed to set relay on RPi: %s", e)
        raise HTTPException(status_code=503, detail="RPi API unavailable")


@app.post("/api/relays/emergency-stop")
async def emergency_stop():
    """Turn off all relays."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(f"{_rpi_base_url}/relays/all-off")
            resp.raise_for_status()

            # Broadcast to WebSocket clients
            await manager.broadcast({
                "type": "relay_update",
                "data": {"emergency_stop": True},
                "timestamp": datetime.utcnow().isoformat(),
            })

            return resp.json()
    except httpx.HTTPError as e:
        LOGGER.error("Emergency stop failed: %s", e)
        raise HTTPException(status_code=503, detail="RPi API unavailable")


# --- Automation ---

@app.get("/api/automation", response_model=schemas.AutomationConfig)
async def get_automation():
    """Get automation configuration."""
    if not _settings:
        raise HTTPException(status_code=503, detail="Settings not loaded")

    auto_cfg = _settings.automation
    return schemas.AutomationConfig(
        enabled=auto_cfg.get("enabled", False),
        rules=[
            schemas.AutomationRule(
                name=r.get("name", ""),
                device_id=r.get("device_id", ""),
                condition_type=r.get("condition_type", "threshold"),
                conditions=[
                    schemas.RuleCondition(
                        sensor_type=c.get("sensor_type"),
                        operator=c.get("operator"),
                        threshold=c.get("threshold"),
                    )
                    for c in r.get("conditions", [])
                ],
                is_active=r.get("is_active", True),
            )
            for r in auto_cfg.get("rules", [])
        ],
    )


# --- WebSocket ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle client messages
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                msg = json.loads(data)

                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat(),
                    }))
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_text(json.dumps({
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat(),
                }))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        LOGGER.error("WebSocket error: %s", e)
        manager.disconnect(websocket)


async def poll_new_readings():
    """Background task to poll for new readings and broadcast."""
    last_reading_id = 0

    while True:
        try:
            await asyncio.sleep(5)  # Check every 5 seconds

            if _SessionLocal is None:
                continue

            db = _SessionLocal()
            try:
                # Get new readings since last check
                new_readings = db.query(models.SensorReading).filter(
                    models.SensorReading.id > last_reading_id
                ).order_by(models.SensorReading.id).all()

                for reading in new_readings:
                    sensor = db.query(models.Sensor).filter(
                        models.Sensor.id == reading.sensor_fk
                    ).first()

                    if sensor:
                        await manager.broadcast({
                            "type": "sensor_update",
                            "data": {
                                "sensor_id": sensor.sensor_id,
                                "sensor_type": sensor.sensor_type.value,
                                "value": reading.value,
                                "unit": sensor.unit,
                                "location": sensor.location,
                                "recorded_at": reading.recorded_at.isoformat(),
                            },
                            "timestamp": datetime.utcnow().isoformat(),
                        })

                    last_reading_id = reading.id
            finally:
                db.close()

        except asyncio.CancelledError:
            break
        except Exception as e:
            LOGGER.error("Error in poll_new_readings: %s", e)


# --- Static Files & Dashboard ---

# Mount static files (will be created later)
static_path = Path(__file__).parent.parent / "web" / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard page."""
    template_path = Path(__file__).parent.parent / "web" / "templates" / "dashboard.html"
    if template_path.exists():
        return FileResponse(template_path)

    # Return placeholder if template doesn't exist yet
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head><title>SensorPi Dashboard</title></head>
    <body>
        <h1>SensorPi Dashboard</h1>
        <p>Dashboard template not found. Please create web/templates/dashboard.html</p>
        <p>API endpoints available at /api/</p>
    </body>
    </html>
    """)


def run_server():
    """Run the FastAPI server."""
    import uvicorn

    settings = Settings()
    api_cfg = settings.api

    uvicorn.run(
        "sensorpi.api.server_api:app",
        host=api_cfg.get("host", "0.0.0.0"),
        port=api_cfg.get("port", 8000),
        reload=api_cfg.get("debug", False),
    )


if __name__ == "__main__":
    run_server()
