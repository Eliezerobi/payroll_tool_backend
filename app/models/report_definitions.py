from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB


from app.database import Base


class ReportDefinition(Base):
    __tablename__ = "report_definitions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    frequency = Column(String(50), nullable=False, default="daily")
    sql_file = Column(String(255), nullable=False)
    output_table = Column(String(255), nullable=False)
    exclude_chha = Column(Boolean, nullable=False, default=True)

    # NEW FIELD
    output_columns = Column(JSONB, nullable=False)

    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
