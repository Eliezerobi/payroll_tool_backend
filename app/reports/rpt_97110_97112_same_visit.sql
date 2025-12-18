WITH yesterday AS (
    SELECT *
    FROM visits
    WHERE finalized_date = CURRENT_DATE - INTERVAL '1 day'
),

flagged AS (
    SELECT
        v.*
    FROM yesterday v
    WHERE 
        v.cpt_code ILIKE '%97110%' 
        AND v.cpt_code ILIKE '%97112%' 
)

INSERT INTO report_97110_97112_same_visit (
    visit_row_id,
    case_id,
    patient_id,
    first_name,
    last_name,
    case_description,
    note_date,
    note,
    cpt_code,
    visiting_therapist,
    primary_insurance
)
SELECT
    v.id,
    v.case_id,
    v.patient_id,
    v.first_name,
    v.last_name,
    v.case_description,
    v.note_date,
    v.note,
    v.cpt_code,
    v.visiting_therapist,
    v.primary_insurance
FROM flagged v
WHERE NOT EXISTS (
    SELECT 1
    FROM report_97110_97112_same_visit r
    WHERE r.visit_row_id = v.id
);
