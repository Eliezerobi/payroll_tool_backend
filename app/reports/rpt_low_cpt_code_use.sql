WITH yesterday AS (
    SELECT *
    FROM visits
    WHERE finalized_date = CURRENT_DATE - INTERVAL '1 day'
),

split_codes AS (
    SELECT
        v.*, 
        trim(code_part) AS raw_part
    FROM yesterday v,
         regexp_split_to_table(v.cpt_code, ',') AS code_part
),

-- Only exact matches
problematic_raw AS (
    SELECT
        s.*, 
        s.raw_part AS exact_match
    FROM split_codes s
    WHERE s.raw_part IN (
        '97116(2)', '97116(3)', '97116(4)',
        '97140(2)', '97140(3)', '97140(4)',
        '97110(2)', '97110(3)'
    )
),

parsed AS (
    SELECT
        p.id AS visit_row_id,
        p.note_id,
        p.case_id,
        p.patient_id,
        p.first_name,
        p.last_name,
        p.case_description,
        p.note_date,
        p.note,
        p.cpt_code,
        p.visiting_therapist,
        p.primary_insurance,
        split_part(p.exact_match, '(', 1)::INT AS problematic_cpt,
        split_part(split_part(p.exact_match, '(', 2), ')', 1)::INT AS problematic_amount
    FROM problematic_raw p
)

INSERT INTO report_low_cpt_code_use (
    visit_row_id,
    note_id,
    case_id,
    patient_id,
    first_name,
    last_name,
    case_description,
    note_date,
    note,
    cpt_code,
    problematic_cpt,
    problematic_amount,
    visiting_therapist,
    primary_insurance
)
SELECT
    pr.visit_row_id,
    pr.note_id,
    pr.case_id,
    pr.patient_id,
    pr.first_name,
    pr.last_name,
    pr.case_description,
    pr.note_date,
    pr.note,
    pr.cpt_code,
    pr.problematic_cpt,
    pr.problematic_amount,
    pr.visiting_therapist,
    pr.primary_insurance
FROM parsed pr
WHERE NOT EXISTS (
    SELECT 1
    FROM report_low_cpt_code_use r
    WHERE r.visit_row_id = pr.visit_row_id
      AND r.problematic_cpt = pr.problematic_cpt
      AND r.problematic_amount = pr.problematic_amount
);
