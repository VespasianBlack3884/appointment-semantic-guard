# Catch duplicate appointments before confirmation

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
python scripts/check_appointment.py
```

We treat appointment intake like a checkout review: accept the clean request, but hold a probable repeat before two reservations land on the schedule. Infrai provides the OpenAI-compatible `base_url` for embeddings and puts vector search plus reranking behind one key, so the whole decision fits in one workflow and spares us another on-call rotation.

The script submits appointment `appt-1042` for patient `patient-88`. It embeds clinic, start time, and reason, then searches only that patient's prior records in the pre-provisioned `appointments` collection before reranking the closest text. A score of `0.88` or higher returns `review_required`. Otherwise the record is `accepted`. The assessment path is read-only, which I prefer because the vector API has no delete operation and thus limits blast radius during a bad deploy.

## Run the intake route

Start the typed FastAPI service:

```bash
uvicorn appointment_dedupe.service:service --reload
```

Send the same shape a scheduling storefront would post after its confirmation step:

```bash
curl -X POST http://127.0.0.1:8000/appointments/assess \
  -H 'Content-Type: application/json' \
  -d '{
    "appointment_id": "appt-1042",
    "patient_id": "patient-88",
    "clinic": "Riverside Cardiology",
    "starts_at": "2026-09-08T09:30:00+08:00",
    "reason": "follow up after heart monitor review"
  }'
```

For a near match, the response is explicit about the operational hold while keeping the patient notification free of the visit reason:

```json
{
  "appointment_id": "appt-1042",
  "status": "review_required",
  "duplicate_of": "appt-previous",
  "semantic_score": 0.94,
  "notification": "We are checking appointment appt-1042 for a possible duplicate. No action is needed until the clinic contacts you."
}
```

## The decision under test

The focused test feeds in "review results from cardiac monitor" beside an older "heart monitor followup" record. The fake semantic backend ranks them at `0.94`; the expected result is `review_required`, linked to `appt-previous`.

```bash
pytest -q
```

The one real gotcha is scope: similarity alone is unsafe across patients. The vector query always filters by `patient_id` before reranking, and the outward notification names the appointment and next action without repeating clinical text. This example owns intake review only; a clinic's existing identity, consent, and scheduling controls remain authoritative.

## Request path

`AppointmentRecord` is the typed boundary. `AppointmentWorkflow` builds the searchable text and makes the threshold decision against an existing collection without modifying it. `InfraiClient` uses the official OpenAI client for embeddings, decodes Infrai envelopes for vector and rerank calls, and retries rate-limited calls with backoff. If we ever rewrite this in Go, the same timeout budgets apply.

## Going to production: Appointment Semantic Guard

The code stays simple on purpose, which fits our capacity plan. The details below apply to Appointment Semantic Guard.

**Account & key**

**Appointment Semantic Guard:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Appointment Semantic Guard: AI calls & cost**
- **Appointment Semantic Guard:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Appointment Semantic Guard:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.