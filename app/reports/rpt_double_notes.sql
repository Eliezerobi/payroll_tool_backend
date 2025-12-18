WITH target_visits AS (
    SELECT *
    FROM visits
    WHERE finalized_date = CURRENT_DATE - INTERVAL '1 day'
),

-- 🧩 Find duplicates by date
dups_by_date AS (
    SELECT
        v.patient_id,
        v.case_description,
        v.note_date,
        COUNT(*) AS cnt
    FROM visits v
    JOIN target_visits t
      ON v.patient_id = t.patient_id
     AND v.case_description = t.case_description
     AND v.note_date = t.note_date
    GROUP BY v.patient_id, v.case_description, v.note_date
    HAVING COUNT(*) > 1
),

-- 🧩 Find duplicates by note_number
dups_by_number AS (
    SELECT
        v.patient_id,
        v.case_description,
        v.note_number,
        COUNT(*) AS cnt
    FROM visits v
    JOIN target_visits t
      ON v.patient_id = t.patient_id
     AND v.case_description = t.case_description
     AND v.note_number = t.note_number
    GROUP BY v.patient_id, v.case_description, v.note_number
    HAVING COUNT(*) > 1
),

-- 🧩 Get all matching visits for these duplicate groups
matches_by_date AS (
    SELECT
        v.id AS visit_row_id,
        v.note_id,  -- ✅ Added
        v.case_id,
        v.patient_id,
        v.first_name,
        v.last_name,
        v.case_description,
        v.note,
        v.note_number,
        v.note_date,
        v.visiting_therapist,
        v.cpt_code,
        v.primary_insurance,
        'DATE-' || v.note_date || '-' || v.last_name AS dup_key
    FROM visits v
    JOIN dups_by_date d
      ON v.patient_id = d.patient_id
     AND v.case_description = d.case_description
     AND v.note_date = d.note_date
),

matches_by_number AS (
    SELECT
        v.id AS visit_row_id,
        v.note_id,  -- ✅ Added
        v.case_id,
        v.patient_id,
        v.first_name,
        v.last_name,
        v.case_description,
        v.note,
        v.note_number,
        v.note_date,
        v.visiting_therapist,
        v.cpt_code,
        v.primary_insurance,
        'NUMBER-' || v.note_number || '-' || v.last_name AS dup_key
    FROM visits v
    JOIN dups_by_number d
      ON v.patient_id = d.patient_id
     AND v.case_description = d.case_description
     AND v.note_number = d.note_number
),

all_matches AS (
    SELECT * FROM matches_by_date
    UNION ALL
    SELECT * FROM matches_by_number
)

INSERT INTO report_double_notes (
    visit_row_id,
    note_id,               -- ✅ Added
    case_id,
    patient_id,
    first_name,
    last_name,
    case_description,
    note,
    note_number,
    note_date,
    visiting_therapist,
    cpt_code,
    primary_insurance,
    duplicate_group
)
SELECT
    v.visit_row_id,
    v.note_id,             -- ✅ Added
    v.case_id,
    v.patient_id,
    v.first_name,
    v.last_name,
    v.case_description,
    v.note,
    v.note_number,
    v.note_date,
    v.visiting_therapist,
    v.cpt_code,
    v.primary_insurance,
    v.dup_key
FROM all_matches v
WHERE NOT EXISTS (
    SELECT 1
    FROM report_double_notes r
    WHERE r.visit_row_id = v.visit_row_id
);
