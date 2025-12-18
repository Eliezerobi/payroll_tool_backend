import csv
from datetime import datetime
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ---------------------------------
# Make project root importable
# ---------------------------------
ROOT_DIR = Path(__file__).resolve().parents[3]
sys.path.append(str(ROOT_DIR))
print("ROOT_DIR =", ROOT_DIR)

# ---------------------------------
# Load DB settings from app.config
# ---------------------------------
from app.models.patient_coverages import PatientCoverage

try:
    # Typical pattern: get_settings() returns a Settings instance
    from app.config import get_settings
    settings = get_settings()
except ImportError:
    # If you actually have a `settings` object exported directly, fall back
    from app.config import settings  # type: ignore

# Try common attribute names for DB URL
db_url = None
for attr in ("DATABASE_URL", "SQLALCHEMY_DATABASE_URL", "DB_URL"):
    if hasattr(settings, attr):
        db_url = getattr(settings, attr)
        break

if not db_url:
    raise RuntimeError("Could not find a database URL in settings.")

# Convert async URL to sync URL if needed
if db_url.startswith("postgresql+asyncpg"):
    db_url = db_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
elif db_url.startswith("postgresql+psycopg"):
    # just in case you're using psycopg3-async style
    db_url = db_url.replace("postgresql+psycopg", "postgresql+psycopg2")

print("Using DB URL:", db_url)

engine = create_engine(db_url, future=True)
SessionLocal = sessionmaker(bind=engine)


def parse_date(value: str):
    if not value:
        return None
    value = value.strip()
    if not value:
        return None

    # Handles formats like 9/8/1953, 08/26/1939
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    # If everything fails, just return None
    return None


def import_patient_coverages(csv_path: str):
    session = SessionLocal()

    try:
        # Use cp1252 because the file came from Windows/Excel and has smart quotes
        with open(csv_path, newline="", encoding="cp1252") as f:
            raw_lines = f.readlines()

        # Find header row that starts with "Name"
        header_index = None
        for i, line in enumerate(raw_lines):
            cells = [c.strip() for c in line.split(",")]
            if cells and cells[0].lower() == "name":
                header_index = i
                break

        if header_index is None:
            raise ValueError("❌ Could not find header row starting with 'Name'.")

        print(f"🔎 Header found at line {header_index + 1}")

        clean_csv = raw_lines[header_index:]
        reader = csv.DictReader(clean_csv)

        for row in reader:
            name = row.get("Name")
            external_id = row.get("ID")
            file_number = row.get("File Number")
            medical_record_id = row.get("Medical Record ID")
            dob = parse_date(row.get("D.O.B.") or row.get("DOB"))
            gender = (row.get("Gender") or "").strip() or None

            coverage = PatientCoverage(
                name=name or None,
                external_patient_id=external_id or None,
                file_number=file_number or None,
                medical_record_id=medical_record_id or None,
                date_of_birth=dob,
                gender=gender,
                address1=row.get("Address1") or None,
                address2=row.get("Address2") or None,
                city=row.get("City") or None,
                state=row.get("State") or None,
                zip=row.get("Zip") or None,
                account_status=row.get("Account Status") or None,
                patient_type=row.get("Patient Type") or None,
                payer=row.get("Payer") or None,
                policy_type=row.get("Policy Type") or None,
                policy_number=row.get("Policy Number") or None,
            )

            session.add(coverage)

        session.commit()
        print("✅ Import complete")

    except Exception as e:
        session.rollback()
        print("❌ Import failed:", e)
        raise

    finally:
        session.close()


if __name__ == "__main__":
    csv_path = Path(__file__).resolve().parent / "InsurancePolicies12-10-2024.csv"
    import_patient_coverages(str(csv_path))
