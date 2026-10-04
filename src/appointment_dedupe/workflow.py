from typing import Any

from .models import AppointmentDecision, AppointmentRecord


class AppointmentWorkflow:
    def __init__(self, index: Any, collection: str = "appointments") -> None:
        self.index = index
        self.collection = collection

    def assess(self, record: AppointmentRecord) -> AppointmentDecision:
        text = self._search_text(record)
        embedding = self.index.embed(text)
        matches = self.index.query(self.collection, embedding, record.patient_id)

        candidate_texts = [
            str(match.get("metadata", {}).get("search_text", ""))
            for match in matches
            if str(match.get("id")) != record.appointment_id
            and isinstance(match.get("metadata"), dict)
        ]
        candidate_ids = [
            str(match.get("id"))
            for match in matches
            if str(match.get("id")) != record.appointment_id
            and isinstance(match.get("metadata"), dict)
        ]

        duplicate_of: str | None = None
        semantic_score: float | None = None
        if candidate_texts:
            ranked = self.index.rerank(text, candidate_texts)
            if ranked:
                best = ranked[0]
                candidate_index = int(best.get("index", 0))
                semantic_score = float(best.get("score", 0.0))
                if semantic_score >= 0.88:
                    duplicate_of = candidate_ids[candidate_index]

        status = "review_required" if duplicate_of else "accepted"
        notification = self._notification(record, status)
        return AppointmentDecision(
            appointment_id=record.appointment_id,
            status=status,
            duplicate_of=duplicate_of,
            semantic_score=semantic_score,
            notification=notification,
        )

    @staticmethod
    def _search_text(record: AppointmentRecord) -> str:
        return (
            f"clinic: {record.clinic}; starts: {record.starts_at}; "
            f"appointment reason: {record.reason}"
        )

    @staticmethod
    def _notification(record: AppointmentRecord, status: str) -> str:
        if status == "review_required":
            return (
                f"We are checking appointment {record.appointment_id} for a possible "
                "duplicate. No action is needed until the clinic contacts you."
            )
        return (
            f"Appointment {record.appointment_id} was received for {record.starts_at}. "
            "Contact the clinic if you need to make a change."
        )
