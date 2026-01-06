from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class VisitDetailsOut(BaseModel):
    id: int
    visit_uid: Optional[str] = None
    note_id: Optional[int] = None
    patient_id: Optional[int] = None

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    note: Optional[str] = None
    note_number: int

    case_description: Optional[str] = None
    case_date: Optional[date] = None

    primary_ins_id: Optional[str] = None
    primary_insurance: Optional[str] = None
    secondary_ins_id: Optional[str] = None
    secondary_insurance: Optional[str] = None

    note_date: Optional[date] = None
    referring_provider: Optional[str] = None
    ref_provider_npi: Optional[str] = None
    diagnosis: Optional[str] = None
    finalized_date: Optional[date] = None

    pos: Optional[str] = None
    visit_type: Optional[str] = None
    attendance: Optional[str] = None
    comments: Optional[str] = None

    supervising_therapist: Optional[str] = None
    visiting_therapist: Optional[str] = None

    cpt_code: Optional[str] = None
    total_units: Optional[int] = None

    date_billed: Optional[date] = None
    billed_comment: Optional[str] = None

    date_of_birth: Optional[date] = None
    patient_street1: Optional[str] = None
    patient_street2: Optional[str] = None
    patient_city: Optional[str] = None
    patient_state: Optional[str] = None
    patient_zip: Optional[str] = None

    case_type: Optional[str] = None
    location: Optional[str] = None

    hold: bool
    billed: bool
    paid: bool

    auth_number: Optional[str] = None
    medical_record_no: Optional[str] = None
    medical_diagnosis: Optional[str] = None
    rendering_provider_npi: Optional[str] = None
    gender: Optional[str] = None

    created_at: datetime
    updated_at: datetime
    uploaded_by: Optional[int] = None
    uploaded_at: datetime

    review_needed: bool
    review_reason: Optional[str] = None

    case_id: Optional[int] = None
    time_in: Optional[datetime] = None
    time_out: Optional[datetime] = None

    review_by: Optional[int] = None

    note_group_id: Optional[int] = None
    note_version: Optional[int] = None

    model_config = {"from_attributes": True}
