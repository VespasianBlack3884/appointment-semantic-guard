from fastapi import FastAPI, HTTPException

from .infrai_client import InfraiClient, InfraiError
from .models import AppointmentDecision, AppointmentRecord
from .workflow import AppointmentWorkflow

service = FastAPI(title="Appointment duplicate review")


@service.post("/appointments/assess", response_model=AppointmentDecision)
def assess_appointment(record: AppointmentRecord) -> AppointmentDecision:
    client = InfraiClient()
    try:
        return AppointmentWorkflow(client).assess(record)
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    finally:
        client.close()

