-- ClawShield Security Scanning Extension
-- Migration for AgentCostControl

-- Enable necessary extensions
create extension if not exists "uuid-ossp";

-- ============================================
-- CLAWHUB SKILLS REGISTRY
-- ============================================

create table public.clawhub_skills (
    id uuid default uuid_generate_v4() primary key,
    skill_id text unique not null,  -- ClawHub skill identifier
    name text not null,
    author text,
    version text,
    description text,
    package_hash text,  -- SHA-256 of package
    manifest jsonb default '{}',  -- claw.json contents
    permissions text[] default '{}',
    tags text[] default '{}',
    clawhub_url text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create index idx_clawhub_skills_skill_id on public.clawhub_skills(skill_id);
create index idx_clawhub_skills_author on public.clawhub_skills(author);
create index idx_clawhub_skills_tags on public.clawhub_skills using gin(tags);

-- ============================================
-- SKILL SCANS
-- ============================================

create type scan_status as enum('pending', 'running', 'completed', 'failed');
create type scan_profile as enum('quick', 'standard', 'deep', 'comprehensive');
create type risk_level as enum('low', 'medium', 'high', 'critical');

create table public.skill_scans (
    id uuid default uuid_generate_v4() primary key,
    user_id uuid references public.users(id) on delete cascade not null,
    skill_id uuid references public.clawhub_skills(id) on delete cascade not null,

    -- Scan configuration
    profile scan_profile default 'standard',
    status scan_status default 'pending',

    -- Results
    trust_score int check (trust_score >= 0 and trust_score <= 100),
    risk_level risk_level,
    recommendation text check (recommendation in ('safe', 'caution', 'avoid')),

    -- Scan details
    scan_duration_ms int,
    files_scanned int default 0,
    patterns_checked int default 0,

    -- External API results
    virustotal_result jsonb,
    snyk_result jsonb,

    -- Metadata
    error_message text,
    metadata jsonb default '{}',

    created_at timestamptz default now(),
    completed_at timestamptz
);

create index idx_skill_scans_user on public.skill_scans(user_id, created_at desc);
create index idx_skill_scans_skill on public.skill_scans(skill_id);
create index idx_skill_scans_status on public.skill_scans(status);
create index idx_skill_scans_trust on public.skill_scans(trust_score);

-- ============================================
-- SKILL FINDINGS (Security Issues)
-- ============================================

create type finding_severity as enum('info', 'low', 'medium', 'high', 'critical');
create type finding_type as enum(
    'vulnerability',
    'malware',
    'secret',
    'misconfiguration',
    'suspicious_pattern',
    'permission_issue',
    'license_issue',
    'behavioral_anomaly'
);
create type finding_status as enum('open', 'confirmed', 'fixed', 'suppressed', 'false_positive');

create table public.skill_findings (
    id uuid default uuid_generate_v4() primary key,
    scan_id uuid references public.skill_scans(id) on delete cascade not null,
    skill_id uuid references public.clawhub_skills(id) on delete cascade not null,
    user_id uuid references public.users(id) on delete cascade not null,

    -- Finding details
    finding_type finding_type not null,
    severity finding_severity not null,
    title text not null,
    description text not null,

    -- Location
    file_path text,
    line_number int,
    code_snippet text,

    -- Classification
    cwe text,  -- CWE ID
    cve text,  -- CVE ID if applicable
    cvss_score decimal(3,1),

    -- Pattern matched
    pattern_matched text,
    rule_id text,

    -- Remediation
    remediation text,
    reference_urls text[] default '{}',

    -- Status
    status finding_status default 'open',
    suppressed_at timestamptz,
    suppressed_by uuid,
    suppress_reason text,

    detected_at timestamptz default now()
);

create index idx_skill_findings_scan on public.skill_findings(scan_id);
create index idx_skill_findings_severity on public.skill_findings(severity);
create index idx_skill_findings_type on public.skill_findings(finding_type);
create index idx_skill_findings_status on public.skill_findings(status);

-- ============================================
-- TRUST SCORES (Computed)
-- ============================================

create table public.trust_scores (
    id uuid default uuid_generate_v4() primary key,
    skill_id uuid references public.clawhub_skills(id) on delete cascade not null,

    -- Overall score
    overall_score int not null check (overall_score >= 0 and overall_score <= 100),
    risk_level risk_level not null,

    -- Component scores
    code_quality_score int check (code_quality_score >= 0 and code_quality_score <= 100),
    author_reputation_score int check (author_reputation_score >= 0 and author_reputation_score <= 100),
    community_validation_score int check (community_validation_score >= 0 and community_validation_score <= 100),
    security_posture_score int check (security_posture_score >= 0 and security_posture_score <= 100),
    behavior_profile_score int check (behavior_profile_score >= 0 and behavior_profile_score <= 100),

    -- Breakdown
    score_breakdown jsonb default '{}',

    -- Validity
    valid_from timestamptz default now(),
    valid_until timestamptz,

    -- Latest scan reference
    latest_scan_id uuid references public.skill_scans(id),

    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create index idx_trust_scores_skill on public.trust_scores(skill_id);
create index idx_trust_scores_overall on public.trust_scores(overall_score desc);

-- ============================================
-- MONITORED SKILLS (Real-time Monitoring)
-- ============================================

create type monitor_status as enum('active', 'paused', 'alerted', 'disabled');

create table public.monitored_skills (
    id uuid default uuid_generate_v4() primary key,
    user_id uuid references public.users(id) on delete cascade not null,
    skill_id uuid references public.clawhub_skills(id) on delete cascade not null,

    -- Monitoring configuration
    status monitor_status default 'active',
    check_interval_seconds int default 3600,  -- Check every hour
    last_check_at timestamptz,
    next_check_at timestamptz,

    -- Alert configuration
    alert_on_critical boolean default true,
    alert_on_high boolean default true,
    alert_on_new_findings boolean default true,
    alert_channels jsonb default '{"email": true}',

    -- Baseline
    baseline_trust_score int,
    baseline_finding_count int,

    -- Statistics
    total_checks int default 0,
    findings_detected int default 0,
    alerts_sent int default 0,

    created_at timestamptz default now(),
    updated_at timestamptz default now(),

    unique(user_id, skill_id)
);

create index idx_monitored_skills_user on public.monitored_skills(user_id);
create index idx_monitored_skills_next_check on public.monitored_skills(next_check_at)
    where status = 'active';

-- ============================================
-- COMPLIANCE REPORTS
-- ============================================

create type compliance_framework as enum('SOC2', 'ISO27001', 'HIPAA', 'PCI_DSS', 'GDPR', 'NIST_CSF', 'CUSTOM');
create type compliance_status as enum('compliant', 'partially_compliant', 'non_compliant', 'not_applicable');

create table public.compliance_reports (
    id uuid default uuid_generate_v4() primary key,
    user_id uuid references public.users(id) on delete cascade not null,

    -- Report details
    framework compliance_framework not null,
    framework_version text,
    report_name text,

    -- Scope
    skill_ids uuid[] default '{}',

    -- Results
    overall_status compliance_status,
    controls_evaluated int default 0,
    controls_passed int default 0,
    controls_failed int default 0,

    -- Detailed results
    control_results jsonb default '{}',
    recommendations jsonb default '{}',

    -- Evidence
    evidence_urls text[] default '{}',

    -- Report file
    report_url text,
    report_format text default 'pdf',

    -- Validity
    report_period_start timestamptz,
    report_period_end timestamptz,

    generated_at timestamptz default now(),
    expires_at timestamptz
);

create index idx_compliance_reports_user on public.compliance_reports(user_id, generated_at desc);
create index idx_compliance_reports_framework on public.compliance_reports(framework);

-- ============================================
-- SCAN CREDITS & USAGE
-- ============================================

create table public.scan_credits (
    id uuid default uuid_generate_v4() primary key,
    user_id uuid references public.users(id) on delete cascade not null,

    -- Credit allocation
    total_credits int not null default 0,
    used_credits int not null default 0,
    remaining_credits int generated always as (total_credits - used_credits) stored,

    -- Credit types (different scan profiles cost different amounts)
    quick_scan_cost int default 1,
    standard_scan_cost int default 2,
    deep_scan_cost int default 5,
    comprehensive_scan_cost int default 10,

    -- Period
    period_start timestamptz not null,
    period_end timestamptz not null,

    -- Rollover
    rollover_credits int default 0,

    created_at timestamptz default now(),
    updated_at timestamptz default now(),

    unique(user_id, period_start)
);

create index idx_scan_credits_user on public.scan_credits(user_id, period_end);

-- ============================================
-- MALWARE SIGNATURES DATABASE
-- ============================================

create table public.malware_signatures (
    id uuid default uuid_generate_v4() primary key,
    signature_hash text unique not null,
    signature_name text not null,
    signature_type text not null,  -- pattern, hash, behavior
    pattern text,
    severity finding_severity not null,
    description text,
    remediation text,
    reference_urls text[] default '{}',
    is_active boolean default true,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create index idx_malware_signatures_hash on public.malware_signatures(signature_hash);
create index idx_malware_signatures_type on public.malware_signatures(signature_type);

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

alter table public.clawhub_skills enable row level security;
alter table public.skill_scans enable row level security;
alter table public.skill_findings enable row level security;
alter table public.trust_scores enable row level security;
alter table public.monitored_skills enable row level security;
alter table public.compliance_reports enable row level security;
alter table public.scan_credits enable row level security;

-- RLS Policies for skill_scans
create policy "Users can view own scans"
    on public.skill_scans for select
    using (auth.uid() = user_id);

create policy "Users can insert own scans"
    on public.skill_scans for insert
    with check (auth.uid() = user_id);

create policy "Service role can manage scans"
    on public.skill_scans for all
    using (auth.jwt()->>'role' = 'service_role');

-- RLS Policies for skill_findings
create policy "Users can view own findings"
    on public.skill_findings for select
    using (auth.uid() = user_id);

create policy "Service role can manage findings"
    on public.skill_findings for all
    using (auth.jwt()->>'role' = 'service_role');

-- RLS Policies for monitored_skills
create policy "Users can manage own monitored skills"
    on public.monitored_skills for all
    using (auth.uid() = user_id);

-- RLS Policies for compliance_reports
create policy "Users can view own compliance reports"
    on public.compliance_reports for select
    using (auth.uid() = user_id);

create policy "Users can create own compliance reports"
    on public.compliance_reports for insert
    with check (auth.uid() = user_id);

-- RLS Policies for scan_credits
create policy "Users can view own credits"
    on public.scan_credits for select
    using (auth.uid() = user_id);

create policy "Service role can manage credits"
    on public.scan_credits for all
    using (auth.jwt()->>'role' = 'service_role');

-- RLS Policies for trust_scores (public read for verified skills)
create policy "Trust scores are publicly readable"
    on public.trust_scores for select
    using (true);

create policy "Service role can manage trust scores"
    on public.trust_scores for all
    using (auth.jwt()->>'role' = 'service_role');

-- RLS for clawhub_skills (public read)
create policy "ClawHub skills are publicly readable"
    on public.clawhub_skills for select
    using (true);

create policy "Service role can manage skills"
    on public.clawhub_skills for all
    using (auth.jwt()->>'role' = 'service_role');

-- ============================================
-- FUNCTIONS
-- ============================================

-- Function to check if user has enough credits
create or replace function check_scan_credits(
    p_user_id uuid,
    p_profile scan_profile
) returns boolean as $$
declare
    v_remaining int;
    v_cost int;
begin
    -- Get cost based on profile
    v_cost := case p_profile
        when 'quick' then 1
        when 'standard' then 2
        when 'deep' then 5
        when 'comprehensive' then 10
    end;

    -- Check remaining credits
    select (total_credits - used_credits) into v_remaining
    from scan_credits
    where user_id = p_user_id
    and period_start <= now()
    and period_end >= now()
    limit 1;

    return v_remaining >= v_cost;
end;
$$ language plpgsql security definer;

-- Function to consume credits
create or replace function consume_scan_credits(
    p_user_id uuid,
    p_profile scan_profile,
    p_scan_id uuid
) returns boolean as $$
declare
    v_cost int;
    v_updated int;
begin
    -- Get cost based on profile
    v_cost := case p_profile
        when 'quick' then 1
        when 'standard' then 2
        when 'deep' then 5
        when 'comprehensive' then 10
    end;

    -- Consume credits
    update scan_credits
    set used_credits = used_credits + v_cost,
        updated_at = now()
    where user_id = p_user_id
    and period_start <= now()
    and period_end >= now()
    and (total_credits - used_credits) >= v_cost;

    return found;
end;
$$ language plpgsql security definer;

-- Function to calculate trust score
create or replace function calculate_trust_score(
    p_scan_id uuid
) returns int as $$
declare
    v_score int := 100;
    v_finding record;
begin
    -- Deduct points based on findings
    for v_finding in
        select severity, count(*) as cnt
        from skill_findings
        where scan_id = p_scan_id
        and status != 'false_positive'
        group by severity
    loop
        case v_finding.severity
            when 'critical' then v_score := v_score - (30 * v_finding.cnt);
            when 'high' then v_score := v_score - (15 * v_finding.cnt);
            when 'medium' then v_score := v_score - (5 * v_finding.cnt);
            when 'low' then v_score := v_score - (2 * v_finding.cnt);
            when 'info' then v_score := v_score - (1 * v_finding.cnt);
        end case;
    end loop;

    -- Clamp between 0 and 100
    return greatest(0, least(100, v_score));
end;
$$ language plpgsql security definer;

-- Function to get scan statistics
create or replace function get_scan_stats(
    p_user_id uuid default auth.uid(),
    p_days int default 30
) returns table(
    total_scans bigint,
    completed_scans bigint,
    failed_scans bigint,
    avg_trust_score decimal,
    skills_with_issues bigint,
    critical_findings bigint,
    high_findings bigint
) as $$
begin
    return query
    select
        count(*) as total_scans,
        count(*) filter (where status = 'completed') as completed_scans,
        count(*) filter (where status = 'failed') as failed_scans,
        avg(trust_score) as avg_trust_score,
        count(distinct skill_id) filter (where exists (
            select 1 from skill_findings sf
            where sf.scan_id = skill_scans.id
            and sf.severity in ('critical', 'high')
        )) as skills_with_issues,
        coalesce(sum(critical_cnt), 0) as critical_findings,
        coalesce(sum(high_cnt), 0) as high_findings
    from skill_scans
    left join (
        select scan_id,
            count(*) filter (where severity = 'critical') as critical_cnt,
            count(*) filter (where severity = 'high') as high_cnt
        from skill_findings
        group by scan_id
    ) findings on findings.scan_id = skill_scans.id
    where user_id = p_user_id
    and created_at >= now() - interval '1 day' * p_days;
end;
$$ language plpgsql security definer;

-- ============================================
-- INITIAL DATA
-- ============================================

-- Insert default malware signatures
insert into public.malware_signatures (signature_hash, signature_name, signature_type, pattern, severity, description) values
('SIG001', 'AWS Access Key Pattern', 'pattern', '(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}', 'critical', 'Detects AWS access key IDs'),
('SIG002', 'GitHub Token Pattern', 'pattern', 'ghp_[A-Za-z0-9]{36}', 'high', 'Detects GitHub personal access tokens'),
('SIG003', 'Private Key Pattern', 'pattern', '-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----', 'critical', 'Detects private key files'),
('SIG004', 'Eval Execution', 'pattern', 'eval\s*\(', 'high', 'Dynamic code execution via eval'),
('SIG005', 'Child Process Spawn', 'pattern', 'child_process|spawn|exec\s*\(', 'high', 'Process spawning detected'),
('SIG006', 'Credential File Access', 'pattern', '\.ssh|\.aws|credentials|\.env', 'critical', 'Access to credential files'),
('SIG007', 'Base64 Obfuscation', 'pattern', 'base64|atob|btoa|Buffer\.from.*base64', 'medium', 'Potential obfuscation via base64'),
('SIG008', 'Data Exfiltration Pattern', 'pattern', 'fetch\s*\([^)]*(?:password|token|secret|key)[^)]*\)', 'critical', 'Potential credential exfiltration'),
('SIG009', 'Environment Variable Access', 'pattern', 'process\.env', 'medium', 'Access to environment variables'),
('SIG010', 'Database Connection String', 'pattern', '(?:postgres|mysql|mongodb|redis):\/\/[^:]+:[^@]+@', 'critical', 'Database credentials in connection string');

-- ============================================
-- UPDATED AT TRIGGERS
-- ============================================

create trigger update_clawhub_skills_updated_at
    before update on public.clawhub_skills
    for each row
    execute function update_updated_at();

create trigger update_trust_scores_updated_at
    before update on public.trust_scores
    for each row
    execute function update_updated_at();

create trigger update_monitored_skills_updated_at
    before update on public.monitored_skills
    for each row
    execute function update_updated_at();

create trigger update_scan_credits_updated_at
    before update on public.scan_credits
    for each row
    execute function update_updated_at();

-- ============================================
-- GRANTS
-- ============================================

grant select on public.clawhub_skills to authenticated;
grant select on public.trust_scores to authenticated;
grant all on public.skill_scans to authenticated;
grant all on public.skill_findings to authenticated;
grant all on public.monitored_skills to authenticated;
grant all on public.compliance_reports to authenticated;
grant select on public.scan_credits to authenticated;
