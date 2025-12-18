WITH classified AS (
    SELECT
        pc.*,
        -- 👇 Replace these regex patterns with your real ones
        (policy_number ~ '^[A-HJ-NP-Z0-9][A-HJ-NP-Z].{9}$')       AS is_medicare,  -- example MBI-style
        (policy_number ~ '^[A-Z]{2}[0-9]{5}[A-Z]$')   AS is_medicaid   -- example Medicaid-style
    FROM patient_coverages pc
),

-- 1️⃣ Choose ONE Medicare row per medical_record_id
medicare_choice AS (
    SELECT DISTINCT ON (medical_record_id)
        medical_record_id,
        payer,
        policy_type,
        policy_number
    FROM classified
    WHERE is_medicare
    ORDER BY 
        medical_record_id,
        -- If there are multiple candidates, prefer payer NOT equal to 'Medicare'
        CASE WHEN payer ILIKE 'medicare' THEN 1 ELSE 0 END,
        id  -- tie-breaker if needed
),

-- 2️⃣ Choose ONE Medicaid row per medical_record_id
medicaid_choice AS (
    SELECT DISTINCT ON (medical_record_id)
        medical_record_id,
        payer,
        policy_type,
        policy_number
    FROM classified
    WHERE is_medicaid
    ORDER BY 
        medical_record_id,
        -- If there are multiple candidates, prefer payer NOT equal to 'Medicaid'
        CASE WHEN payer ILIKE 'medicaid' THEN 1 ELSE 0 END,
        id
)

INSERT INTO patient_coverages_flat (
    medical_record_id,
    medicare_payer,
    medicare_policy_type,
    medicare_policy_number,
    medicaid_payer,
    medicaid_policy_type,
    medicaid_policy_number
)
SELECT
    COALESCE(med.medical_record_id, medc.medical_record_id) AS medical_record_id,
    med.payer          AS medicare_payer,
    med.policy_type    AS medicare_policy_type,
    med.policy_number  AS medicare_policy_number,
    medc.payer         AS medicaid_payer,
    medc.policy_type   AS medicaid_policy_type,
    medc.policy_number AS medicaid_policy_number
FROM medicare_choice med
FULL OUTER JOIN medicaid_choice medc
  ON med.medical_record_id = medc.medical_record_id;
