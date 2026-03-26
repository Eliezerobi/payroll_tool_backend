WITH yesterday AS (
    SELECT *
    FROM visits
    WHERE finalized_date = CURRENT_DATE - INTERVAL '1 day'
      AND COALESCE(hold, false) = false
),

overlap_rows AS (
    SELECT
        a.id AS visit_row_id,
        a.note_id,
        a.patient_id,
        a.first_name,
        a.last_name,
        a.case_id,
        a.case_description,
        a.note,
        a.note_date,
        a.visiting_therapist,
        a.cpt_code,
        a.primary_insurance,
        a.time_in,
        a.time_out,
        b.id AS overlap_visit_row_id,
        b.note AS overlap_note,
        b.patient_id AS overlap_patient_id,
        b.first_name AS overlap_first_name,
        b.last_name AS overlap_last_name,
        b.time_in AS overlap_time_in,
        b.time_out AS overlap_time_out,
        concat(
            coalesce(a.first_name, ''), ' ', coalesce(a.last_name, ''), ', ',
            'Note: ', coalesce(a.note, ''), ', ',
            'Visit period was ', coalesce(a.time_in::text, ''), ' - ', coalesce(a.time_out::text, ''),
            ' overlaps with: ',
            coalesce(b.first_name, ''), ' ', coalesce(b.last_name, ''), ', ',
            'Note: ', coalesce(b.note, ''), ', ',
            'Visit period was ', coalesce(b.time_in::text, ''), ' - ', coalesce(b.time_out::text, '')
        ) AS explanation
    FROM yesterday a
    JOIN visits b
      ON trim(coalesce(a.visiting_therapist, '')) = trim(coalesce(b.visiting_therapist, ''))
     AND a.id < b.id
     AND COALESCE(b.hold, false) = false
     AND a.time_in IS NOT NULL
     AND a.time_out IS NOT NULL
     AND b.time_in IS NOT NULL
     AND b.time_out IS NOT NULL
     AND a.time_in < b.time_out
     AND b.time_in < a.time_out
)

INSERT INTO overlapping_visits_by_therapist (
    visit_row_id,
    note_id,
    patient_id,
    first_name,
    last_name,
    case_id,
    case_description,
    note,
    note_date,
    visiting_therapist,
    cpt_code,
    primary_insurance,
    time_in,
    time_out,
    overlap_visit_row_id,
    overlap_note,
    overlap_patient_id,
    overlap_first_name,
    overlap_last_name,
    overlap_time_in,
    overlap_time_out,
    explanation
)
SELECT
    o.visit_row_id,
    o.note_id,
    o.patient_id,
    o.first_name,
    o.last_name,
    o.case_id,
    o.case_description,
    o.note,
    o.note_date,
    o.visiting_therapist,
    o.cpt_code,
    o.primary_insurance,
    o.time_in,
    o.time_out,
    o.overlap_visit_row_id,
    o.overlap_note,
    o.overlap_patient_id,
    o.overlap_first_name,
    o.overlap_last_name,
    o.overlap_time_in,
    o.overlap_time_out,
    o.explanation
FROM overlap_rows o
WHERE NOT EXISTS (
    SELECT 1
    FROM overlapping_visits_by_therapist r
    WHERE r.visit_row_id = o.visit_row_id
      AND r.overlap_visit_row_id = o.overlap_visit_row_id
);
