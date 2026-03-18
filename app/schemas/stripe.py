from pydantic import BaseModel


class ChargeClientVisitRequest(BaseModel):
    client_id: int
    visit_id: str
    visit_number: int | None = None
    amount_cents: int