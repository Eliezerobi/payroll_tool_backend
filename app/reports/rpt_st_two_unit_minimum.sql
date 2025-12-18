WITH yesterday AS (
    SELECT *
    FROM visits
    WHERE finalized_date = CURRENT_DATE - INTERVAL '1 day'
),

filtered AS (
    SELECT 
        v.*
    FROM yesterday v
    WHERE 
        (
            v.case_description ILIKE 'ST%' OR
            v.case_description ILIKE 'SLP%' OR
            v.case_description ILIKE 'Speech%'
        )
        AND LOWER(v.primary_insurance) NOT IN (
            'americare', 'royal care', 'extendedcare', 'able health'
        )
)

INSERT INTO report_st_two_unit_minimum (
    visit_row_id,
    note_id,                    -- ✅ added here
    case_id,
    patient_id,
    first_name,
    last_name,
    case_description,
    note_date,
    note,
    cpt_code,
    total_units,                -- ✅ report column
    visiting_therapist,
    primary_insurance
)
SELECT
    f.id AS visit_row_id,
    f.note_id,                  -- ✅ added here
    f.case_id,
    f.patient_id,
    f.first_name,
    f.last_name,
    f.case_description,
    f.note_date,
    f.note,
    f.cpt_code,
    f.total_units,
    f.visiting_therapist,
    f.primary_insurance
FROM filtered f
WHERE f.total_units = 1         -- ✅ keep same criteria
  AND NOT EXISTS (
        SELECT 1 
        FROM report_st_two_unit_minimum r
        WHERE r.visit_row_id = f.id
  );
