-- Cleanup partial ClawShield tables (run this first if migration failed)
-- Run in Supabase SQL Editor

-- Drop tables in correct order (respecting foreign keys)
DROP TABLE IF EXISTS public.malware_signatures CASCADE;
DROP TABLE IF EXISTS public.scan_credits CASCADE;
DROP TABLE IF EXISTS public.compliance_reports CASCADE;
DROP TABLE IF EXISTS public.monitored_skills CASCADE;
DROP TABLE IF EXISTS public.trust_scores CASCADE;
DROP TABLE IF EXISTS public.skill_findings CASCADE;
DROP TABLE IF EXISTS public.skill_scans CASCADE;
DROP TABLE IF EXISTS public.clawhub_skills CASCADE;

-- Drop enums
DROP TYPE IF EXISTS compliance_status CASCADE;
DROP TYPE IF EXISTS compliance_framework CASCADE;
DROP TYPE IF EXISTS monitor_status CASCADE;
DROP TYPE IF EXISTS finding_status CASCADE;
DROP TYPE IF EXISTS finding_type CASCADE;
DROP TYPE IF EXISTS finding_severity CASCADE;
DROP TYPE IF EXISTS scan_status CASCADE;
DROP TYPE IF EXISTS scan_profile CASCADE;
DROP TYPE IF EXISTS risk_level CASCADE;

SELECT 'Cleanup complete - now run the main ClawShield migration' as status;
