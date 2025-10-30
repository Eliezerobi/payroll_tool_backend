from sqlalchemy import Column, String, BigInteger, Date, DateTime, Text, func
from app.database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(BigInteger, primary_key=True, index=True)  # "Patient Id" from Excel
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date)
    gender = Column(String(20))
    address = Column(String(255))
    city = Column(String(100))
    state = Column(String(10))
    zip = Column(String(20))
    phone = Column(String(50))
    work_phone = Column(String(50))
    mobile_phone = Column(String(50))
    primary_insurance = Column(String(150))
    primary_ins_id = Column(String(50))
    secondary_insurance = Column(String(150))
    secondary_ins_id = Column(String(50))
    medical_record_no = Column(String(50))
    email = Column(String(150))
    status = Column(String(100))
    comment = Column(Text)
    primary_care_physician = Column(String(150))
    date_added = Column(Date)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
