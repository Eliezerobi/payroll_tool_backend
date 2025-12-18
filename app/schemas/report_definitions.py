from pydantic import BaseModel
from datetime import datetime


class ReportDefinitionBase(BaseModel):
    code: str
    name: str
    frequency: str
    sql_file: str
    output_table: str
    enabled: bool


class ReportDefinitionCreate(ReportDefinitionBase):
    pass


class ReportDefinition(ReportDefinitionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
