WITH yesterday AS (
    SELECT *
    FROM visits
    WHERE finalized_date = CURRENT_DATE - INTERVAL '1 day'
),

-- Find (patient_id, note_date) pairs where they appear more than once
dupe_groups AS (
    SELECT 
        patient_id,
        note_date
    FROM yesterday
    GROUP BY patient_id, note_date
    HAVING COUNT(*) > 1
),

-- Select ALL visits matching those groups
dupe_visits AS (
    SELECT 
        v.*
    FROM yesterday v
    JOIN dupe_groups g
      ON g.patient_id = v.patient_id
     AND g.note_date = v.note_date
)

INSERT INTO report_same_day_visits (
    visit_row_id,
    note_id,                -- ✅ Added here
    patient_id,
    first_name,
    last_name,
    note_date,
    case_id,
    case_description,
    note,
    visiting_therapist,
    cpt_code,
    primary_insurance
)
SELECT
    d.id AS visit_row_id,
    d.note_id,              -- ✅ Added here
    d.patient_id,
    d.first_name,
    d.last_name,
    d.note_date,
    d.case_id,
    d.case_description,
    d.note,
    d.visiting_therapist,
    d.cpt_code,
    d.primary_insurance
FROM dupe_visits d
WHERE NOT EXISTS (
    SELECT 1
    FROM report_same_day_visits r
    WHERE r.visit_row_id = d.id
);
