import { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Key, Shield, Bell, Database, Users, Laptop, Loader2, Save, Plus } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { supabase } from '../lib/supabase';

export function Settings() {
    const { profile } = useAuth();
    const [organization, setOrganization] = useState(null);
    const [devices, setDevices] = useState([]);
    const [loading, setLoading] = useState(true);

    // Form state
    const [pdlKey, setPdlKey] = useState('');
    const [openAiKey, setOpenAiKey] = useState('');
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (profile?.organization_id) {
            fetchOrgData(profile.organization_id);
        }
    }, [profile]);

    const fetchOrgData = async (orgId) => {
        setLoading(true);
        try {
            // Fetch Org Info (for API keys)
            const { data: orgData } = await supabase
                .from('organizations')
                .select('*')
                .eq('id', orgId)
                .single();

            if (orgData) {
                setOrganization(orgData);
                setPdlKey(orgData.pdl_api_key || '');
                setOpenAiKey(orgData.openai_api_key || '');
            }

            // Fetch Devices
            const { data: devicesData } = await supabase
                .from('devices')
                .select('*')
                .eq('organization_id', orgId);

            if (devicesData) {
                setDevices(devicesData);
            }

        } catch (error) {
            console.error("Error fetching org data:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleSaveKeys = async () => {
        if (!organization?.id) return;
        setSaving(true);
        try {
            const { error } = await supabase
                .from('organizations')
                .update({ pdl_api_key: pdlKey, openai_api_key: openAiKey })
                .eq('id', organization.id);

            if (error) throw error;
            alert("API Keys saved successfully");
        } catch (error) {
            alert("Error saving API keys: " + error.message);
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--spacing-2xl)' }}><Loader2 className="animate-spin" /></div>;
    }

    const isParent = profile?.role === 'parent' || profile?.role === 'admin';

    return (
        <div style={{ maxWidth: '800px', margin: '0 auto', paddingTop: 'var(--spacing-2xl)' }} className="animate-fadeIn">
            <div style={{ marginBottom: 'var(--spacing-2xl)' }}>
                <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: 'var(--spacing-xs)' }}>
                    {organization?.name || 'Workspace'} Settings
                </h1>
                <p style={{ color: 'var(--text-secondary)' }}>
                    {isParent ? 'Manage your organization, team, and ghost laptops.' : 'View your profile and organization settings.'}
                </p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)' }} className="stagger-children">

                {isParent && (
                    <SettingsGroup icon={<Key size={18} />} title="API Keys" desc="Configure OpenAI and PDL API keys for your entire organization">
                        <SettingsField
                            label="OpenAI API Key"
                            placeholder="sk-..."
                            type="password"
                            value={openAiKey}
                            onChange={(e) => setOpenAiKey(e.target.value)}
                        />
                        <SettingsField
                            label="PDL API Key"
                            placeholder="Your PDL key..."
                            type="password"
                            value={pdlKey}
                            onChange={(e) => setPdlKey(e.target.value)}
                        />
                        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 'var(--spacing-md)' }}>
                            <button onClick={handleSaveKeys} className="btn-primary" disabled={saving}>
                                {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                                Save Keys
                            </button>
                        </div>
                    </SettingsGroup>
                )}

                {isParent && (
                    <SettingsGroup icon={<Laptop size={18} />} title="Ghost Laptops (Devices)" desc="Hardware execution nodes assigned to your organization">
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
                            {devices.length === 0 ? (
                                <div style={{ padding: 'var(--spacing-md)', background: 'var(--bg-primary)', borderRadius: 'var(--radius-md)', textAlign: 'center', border: '1px dashed var(--border-color)', color: 'var(--text-muted)' }}>
                                    No Ghost Laptops assigned to your organization yet. Contact support to have a device provisioned.
                                </div>
                            ) : (
                                devices.map(device => (
                                    <div key={device.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 'var(--spacing-md)', background: 'var(--bg-primary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)' }}>
                                            <Laptop size={16} color="var(--accent-primary)" />
                                            <div>
                                                <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{device.id}</div>
                                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Last Seen: {new Date(device.last_heartbeat).toLocaleString()}</div>
                                            </div>
                                        </div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                            <div style={{
                                                width: 8, height: 8, borderRadius: '50%',
                                                background: device.status === 'offline' ? '#ef4444' : device.status === 'running' ? '#f59e0b' : '#10b981'
                                            }} />
                                            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{device.status}</span>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </SettingsGroup>
                )}

                {isParent && (
                    <SettingsGroup icon={<Users size={18} />} title="Team Members" desc="Manage child users who can create and run campaigns">
                        <div style={{ padding: 'var(--spacing-lg)', background: 'var(--bg-primary)', borderRadius: 'var(--radius-md)', border: '1px dashed var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Child user invitations will be managed via the backend API.</span>
                            <button className="btn-secondary" style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }} disabled>
                                <Plus size={14} /> Invite User
                            </button>
                        </div>
                    </SettingsGroup>
                )}

            </div>
        </div>
    );
}

function SettingsGroup({ icon, title, desc, children }) {
    return (
        <div className="glass-panel" style={{ overflow: 'hidden' }}>
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--spacing-md)',
                padding: 'var(--spacing-lg) var(--spacing-xl)',
                borderBottom: '1px solid var(--border-color)',
            }}>
                <div style={{
                    width: 36,
                    height: 36,
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--accent-light)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--accent-primary)',
                    flexShrink: 0,
                }}>
                    {icon}
                </div>
                <div>
                    <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>{title}</h3>
                    <p style={{ fontSize: '0.78rem', marginTop: '2px', color: 'var(--text-secondary)' }}>{desc}</p>
                </div>
            </div>
            <div style={{ padding: 'var(--spacing-md) var(--spacing-xl)' }}>
                {children}
            </div>
        </div>
    );
}

function SettingsField({ label, placeholder, type = 'text', value, onChange }) {
    return (
        <div style={{ padding: 'var(--spacing-sm) 0', display: 'flex', alignItems: 'center', gap: 'var(--spacing-xl)' }}>
            <label style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-secondary)', minWidth: '180px' }}>{label}</label>
            <input
                type={type}
                placeholder={placeholder}
                value={value}
                onChange={onChange}
                className="input"
                style={{ flex: 1, maxWidth: '400px' }}
            />
        </div>
    );
}
