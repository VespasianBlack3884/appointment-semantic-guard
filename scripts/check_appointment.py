import json

from appointment_dedupe.infrai_client import InfraiClient
from appointment_dedupe.models import AppointmentRecord
from appointment_dedupe.workflow import AppointmentWorkflow


def main() -> None:
    client = InfraiClient()
    try:
        decision = AppointmentWorkflow(client).assess(
            AppointmentRecord(
                appointment_id="appt-1042",
                patient_id="patient-88",
                clinic="Riverside Cardiology",
                starts_at="2026-09-08T09:30:00+08:00",
                reason="follow up after heart monitor review",
            )
        )
        print(json.dumps(decision.model_dump(), indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    main()

