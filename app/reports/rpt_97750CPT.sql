-- Insert new rows only

INSERT INTO report_97750CPT (
    visit_row_id,
    note_id,
    case_id,
    note,
    patient_id,
    first_name,
    last_name,
    case_description,
    primary_insurance,
    note_date,
    cpt_code,
    visiting_therapist
)
SELECT
    v.id AS visit_row_id,
    v.note_id,
    v.case_id,
    v.note,
    v.patient_id,
    v.first_name,
    v.last_name,
    v.case_description,
    v.primary_insurance,
    v.note_date,
    v.cpt_code,
    v.visiting_therapist
FROM visits v
WHERE 
    v.finalized_date = CURRENT_DATE - INTERVAL '1 day'  AND 
    v.cpt_code ILIKE '%97750%'
  AND NOT EXISTS (
        SELECT 1
        FROM report_97750CPT r
        WHERE r.visit_row_id = v.id
    );
