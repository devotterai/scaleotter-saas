-- ScaleOtter SaaS Supabase Schema

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Organizations Table
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    pdl_api_key TEXT,
    openai_api_key TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Profiles Table (extends auth.users)
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'parent', 'child')),
    full_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Devices Table (Ghost Laptops)
CREATE TABLE devices (
    id TEXT PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'unassigned' CHECK (status IN ('unassigned', 'idle', 'running', 'waiting_for_2fa', 'offline')),
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Campaigns Table
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID REFERENCES profiles(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'draft',
    send_notes BOOLEAN DEFAULT false,
    job_context JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Candidates Table
CREATE TABLE candidates (
    id TEXT PRIMARY KEY,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    linkedin_url TEXT,
    campaign_status TEXT DEFAULT 'pending',
    connection_note TEXT,
    initial_message TEXT,
    message_status TEXT DEFAULT 'draft',
    data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Job Runs Table (Queue for Ghost Laptops)
CREATE TABLE job_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    device_id TEXT REFERENCES devices(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    job_type TEXT NOT NULL, -- 'login', 'connect', 'message'
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'waiting_for_2fa')),
    error_message TEXT,
    payload JSONB,
    result JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- --- ROW LEVEL SECURITY (RLS) ---

-- Enable RLS on all tables
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_runs ENABLE ROW LEVEL SECURITY;

-- 1. Profiles Policies
-- Users can view profiles in their own organization
CREATE POLICY "Users can view profiles in same org" ON profiles
    FOR SELECT USING (
        organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid())
        OR role = 'admin'
    );
-- Users can update their own profile
CREATE POLICY "Users can update own profile" ON profiles
    FOR UPDATE USING (id = auth.uid());

-- 2. Organizations Policies
-- Users can view their own organization
CREATE POLICY "Users can view own organization" ON organizations
    FOR SELECT USING (
        id = (SELECT organization_id FROM profiles WHERE id = auth.uid())
        OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'admin'
    );
-- Only parents and admins can update the organization
CREATE POLICY "Parents and admins can update organization" ON organizations
    FOR UPDATE USING (
        (id = (SELECT organization_id FROM profiles WHERE id = auth.uid()) AND (SELECT role FROM profiles WHERE id = auth.uid()) = 'parent')
        OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'admin'
    );

-- 3. Devices Policies
-- Users can view devices assigned to their organization
CREATE POLICY "Users can view org devices" ON devices
    FOR SELECT USING (
        organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid())
        OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'admin'
    );
-- Only parents and admins can update devices
CREATE POLICY "Parents can update org devices" ON devices
    FOR ALL USING (
        (organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid()) AND (SELECT role FROM profiles WHERE id = auth.uid()) = 'parent')
        OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'admin'
    );

-- 4. Campaigns Policies
-- Read access for everyone in the org
CREATE POLICY "Users can view org campaigns" ON campaigns
    FOR SELECT USING (
        organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid())
        OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'admin'
    );
-- Write access
CREATE POLICY "Users can insert org campaigns" ON campaigns
    FOR INSERT WITH CHECK (
        organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid())
    );
CREATE POLICY "Users can update org campaigns" ON campaigns
    FOR UPDATE USING (
        organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid())
    );

-- 5. Candidates Policies
CREATE POLICY "Users can view org candidates" ON candidates
    FOR SELECT USING (
        organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid())
        OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'admin'
    );
CREATE POLICY "Users can insert org candidates" ON candidates
    FOR INSERT WITH CHECK (
        organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid())
    );
CREATE POLICY "Users can update org candidates" ON candidates
    FOR UPDATE USING (
        organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid())
    );

-- 6. Job Runs Policies
CREATE POLICY "Users can view org job runs" ON job_runs
    FOR SELECT USING (
        organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid())
        OR (SELECT role FROM profiles WHERE id = auth.uid()) = 'admin'
    );
CREATE POLICY "Users can insert org job runs" ON job_runs
    FOR INSERT WITH CHECK (
        organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid())
    );
CREATE POLICY "Users can update org job runs" ON job_runs
    FOR UPDATE USING (
        organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid())
    );

-- Set up Realtime for `job_runs` and `devices` and `campaigns`
alter publication supabase_realtime add table job_runs;
alter publication supabase_realtime add table devices;
alter publication supabase_realtime add table campaigns;
