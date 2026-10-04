from appointment_dedupe.models import AppointmentRecord
from appointment_dedupe.workflow import AppointmentWorkflow


class FakeIndex:
    def embed(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    def query(
        self, collection: str, embedding: list[float], patient_id: str
    ) -> list[dict[str, object]]:
        return [
            {
                "id": "appt-previous",
                "metadata": {
                    "search_text": "clinic: Riverside Cardiology; starts: Tuesday 9:30; appointment reason: heart monitor followup"
                },
            }
        ]

    def rerank(self, query: str, candidates: list[str]) -> list[dict[str, object]]:
        return [{"index": 0, "score": 0.94}]

def test_similar_appointment_is_held_for_review() -> None:
    index = FakeIndex()
    record = AppointmentRecord(
        appointment_id="appt-new",
        patient_id="patient-88",
        clinic="Riverside Cardiology",
        starts_at="2026-09-08T09:30:00+08:00",
        reason="review results from cardiac monitor",
    )

    decision = AppointmentWorkflow(index).assess(record)

    assert decision.status == "review_required"
    assert decision.duplicate_of == "appt-previous"
    assert "cardiac" not in decision.notification.lower()
