import { useState, useEffect } from 'react';
import { useAppContext, ACTIONS } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../components/Toast';
import { supabase } from '../lib/supabase';
import { Plus, Users, Send, CheckCircle, MessageSquare, Zap, AlertTriangle, Sparkles, X, Loader2, Edit3, Mail, Briefcase, MapPin, DollarSign, UsersRound, FileText, Ban, Trash2 } from 'lucide-react';

export function Campaigns() {
    const { profile } = useAuth();
    const { state, dispatch } = useAppContext();
    const toast = useToast();
    const [selectedCampaign, setSelectedCampaign] = useState(null);
    const [campaignDetails, setCampaignDetails] = useState([]);
    const [isCreating, setIsCreating] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);
    const [isStarting, setIsStarting] = useState(false);
    const [activeTab, setActiveTab] = useState('pipeline');

    // Create form state
    const [newCampaignName, setNewCampaignName] = useState('');
    const [newSendNotes, setNewSendNotes] = useState(false);
    const [jobContext, setJobContext] = useState({
        job_title: '', company: '', pitch: '', why_exciting: '', comp_range: '',
        work_model: '', must_have_skills: '', team_context: '', tone: 'professional', dont_mention: '',
    });

    // Messages state
    const [messages, setMessages] = useState([]);
    const [isGenerating, setIsGenerating] = useState(false);
    const [isSending, setIsSending] = useState(false);
    const [editingId, setEditingId] = useState(null);
    const [editText, setEditText] = useState('');

    // Load initial campaigns
    useEffect(() => {
        if (!profile?.organization_id) return;

        const loadCampaigns = async () => {
            const { data } = await supabase
                .from('campaigns')
                .select('*')
                .eq('organization_id', profile.organization_id)
                .order('created_at', { ascending: false });

            if (data) {
                dispatch({ type: ACTIONS.SET_CAMPAIGNS, payload: data });
                if (data.length > 0 && !selectedCampaign) setSelectedCampaign(data[0]);
            }
        };

        loadCampaigns();

        // Subscribe to campaigns
        const sub = supabase.channel('campaigns-channel')
            .on('postgres_changes', { event: '*', schema: 'public', table: 'campaigns', filter: `organization_id=eq.${profile.organization_id}` }, () => {
                loadCampaigns();
            })
            .subscribe();

        return () => supabase.removeChannel(sub);
    }, [profile?.organization_id]);

    // Load candidates for selected campaign
    useEffect(() => {
        if (!selectedCampaign || !profile?.organization_id) return;

        const loadCandidates = async () => {
            const { data } = await supabase
                .from('candidates')
                .select('*')
                .eq('campaign_id', selectedCampaign.id);
            if (data) {
                setCampaignDetails(data);
                // The messages tab uses candidates that have 'connection_sent'
                setMessages(data.filter(c => c.campaign_status === 'connection_sent'));
            }
        };

        loadCandidates();

        // Realtime Subscription for candidates matching this campaign
        const sub = supabase.channel(`candidates-${selectedCampaign.id}`)
            .on('postgres_changes', { event: '*', schema: 'public', table: 'candidates', filter: `campaign_id=eq.${selectedCampaign.id}` }, () => {
                loadCandidates();
            })
            .subscribe();

        return () => supabase.removeChannel(sub);
    }, [selectedCampaign, profile?.organization_id]);


    const updateJobField = (field, value) => {
        setJobContext(prev => ({ ...prev, [field]: value }));
    };

    const handleCreateCampaign = async () => {
        if (!newCampaignName.trim() || !profile?.organization_id) return;
        try {
            const { data, error } = await supabase.from('campaigns').insert({
                organization_id: profile.organization_id,
                name: newCampaignName,
                send_notes: newSendNotes,
                job_context: jobContext
            }).select().single();

            if (error) throw error;

            setNewCampaignName('');
            setNewSendNotes(false);
            setJobContext({
                job_title: '', company: '', pitch: '', why_exciting: '', comp_range: '',
                work_model: '', must_have_skills: '', team_context: '', tone: 'professional', dont_mention: '',
            });
            setIsCreating(false);
            setSelectedCampaign(data);
            toast.success(`Campaign created!`);
        } catch (err) {
            toast.error("Failed to create campaign.");
        }
    };

    const handleAddManualCandidate = async (name, url) => {
        if (!selectedCampaign || !name.trim() || !url.trim() || !profile?.organization_id) return;
        try {
            const { error } = await supabase.from('candidates').insert({
                id: crypto.randomUUID(),
                organization_id: profile.organization_id,
                campaign_id: selectedCampaign.id,
                name: name,
                linkedin_url: url,
                campaign_status: 'pending'
            });
            if (error) throw error;
            toast.success("Added candidate");
        } catch (err) {
            toast.error("Error adding candidate");
        }
    };

    const handleDeleteCandidate = async (candidateId) => {
        if (!confirm("Are you sure?")) return;
        try {
            await supabase.from('candidates').delete().eq('id', candidateId);
            toast.success("Removed");
        } catch (err) {
            toast.error("Failed to remove");
        }
    };

    const handleEditNote = async (candidateId, note) => {
        try {
            await supabase.from('candidates').update({ connection_note: note }).eq('id', candidateId);
            toast.success('Note updated');
        } catch (err) {
            toast.error('Failed to update note');
        }
    };

    const handleGenerateNotes = async () => {
        // Needs backend LLM processing
        if (!selectedCampaign) return;
        toast.error("AI operations migrating to queued worker system - Please use manual notes for now.");
    };

    const handleGenerateMessages = async () => {
        // Needs backend LLM processing
        if (!selectedCampaign) return;
        toast.error("AI operations migrating to queued worker system - Please use manual messages for now.");
    };

    const handleEditMessage = async (candidateId) => {
        try {
            await supabase.from('candidates').update({ initial_message: editText, message_status: 'draft' }).eq('id', candidateId);
            setEditingId(null);
            toast.success("Message updated.");
        } catch (err) {
            toast.error("Failed to update message.");
        }
    };

    const handleApproveMessage = async (candidateId, message) => {
        try {
            await supabase.from('candidates').update({ initial_message: message, message_status: 'approved' }).eq('id', candidateId);
        } catch (err) {
            toast.error("Failed to approve.");
        }
    };

    // --- Starting Automations via Ghost Laptop Queue ---

    const queueJobForGhostLaptop = async (jobType) => {
        if (!selectedCampaign || !profile?.organization_id) return;
        try {
            // Find an available ghost laptop for this org
            const { data: devices } = await supabase
                .from('devices')
                .select('id')
                .eq('organization_id', profile.organization_id)
                .in('status', ['idle', 'offline', 'waiting_for_2fa']) // Could be offline but we'll queue it anyway
                .limit(1);

            if (!devices || devices.length === 0) {
                toast.error("No ghost laptops are assigned to your organization. Go to Settings to add one.");
                return false;
            }

            const deviceId = devices[0].id;

            // Insert into job queue
            const { error } = await supabase.from('job_runs').insert({
                organization_id: profile.organization_id,
                device_id: deviceId,
                campaign_id: selectedCampaign.id,
                job_type: jobType,
                status: 'pending'
            });

            if (error) throw error;
            toast.success(`Job queued for ghost device: ${deviceId}`);
            return true;

        } catch (err) {
            toast.error(`Error queuing job: ${err.message}`);
            return false;
        }
    };

    const handleStartAutomation = async () => {
        setIsStarting(true);
        await queueJobForGhostLaptop('connect');
        setIsStarting(false);
        setShowConfirm(false);
    };

    const handleSendMessages = async () => {
        setIsSending(true);
        await queueJobForGhostLaptop('message');
        setIsSending(false);
    };


    // Stats
    const pending = campaignDetails.filter(c => c.campaign_status === 'pending');
    const sent = campaignDetails.filter(c => c.campaign_status === 'connection_sent');
    const messageSent = campaignDetails.filter(c => c.campaign_status === 'message_sent');
    const accepted = campaignDetails.filter(c => c.campaign_status === 'accepted');
    const replied = campaignDetails.filter(c => c.campaign_status === 'replied');

    const campaignHasNotes = selectedCampaign?.send_notes;

    // View Components (AddManualModal, tabs, etc. rendering)
    const [showAddManualModal, setShowAddManualModal] = useState(false);
    const [manualCandidateName, setManualCandidateName] = useState('');
    const [manualCandidateUrl, setManualCandidateUrl] = useState('');

    return (
        <div style={{ maxWidth: '1200px', margin: '0 auto' }} className="animate-fadeIn">
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-2xl)' }}>
                <div>
                    <h1 style={{ fontSize: '1.75rem', fontWeight: 700 }}>Campaigns</h1>
                    <p style={{ marginTop: '4px' }}>Manage your outreach pipelines</p>
                </div>
                <button onClick={() => setIsCreating(true)} className="btn-primary">
                    <Plus size={16} /> New Campaign
                </button>
            </div>

            {/* Create Campaign Panel */}
            {isCreating && (
                <div className="glass-panel animate-slideDown" style={{ padding: 'var(--spacing-xl)', marginBottom: 'var(--spacing-xl)' }}>
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 'var(--spacing-xl)' }}>Create New Campaign</h3>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)' }}>
                        <input
                            type="text"
                            placeholder="Campaign Name (e.g. Senior SWE — Series B Fintech)"
                            className="input"
                            value={newCampaignName}
                            onChange={(e) => setNewCampaignName(e.target.value)}
                            autoFocus
                        />

                        {/* Job Questionnaire */}
                        <div style={{
                            background: 'var(--bg-primary)',
                            borderRadius: 'var(--radius-lg)',
                            padding: 'var(--spacing-xl)',
                            border: '1px solid var(--border-color)',
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', marginBottom: 'var(--spacing-lg)' }}>
                                <Briefcase size={16} color="var(--accent-primary)" />
                                <span style={{ fontSize: '0.95rem', fontWeight: 600 }}>Job Details</span>
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)' }}>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                    <label style={labelStyle}>Job Title *</label>
                                    <input className="input" value={jobContext.job_title} onChange={e => updateJobField('job_title', e.target.value)} />
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                    <label style={labelStyle}>Company *</label>
                                    <input className="input" value={jobContext.company} onChange={e => updateJobField('company', e.target.value)} />
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', gridColumn: 'span 2' }}>
                                    <label style={labelStyle}>Why is this role exciting? *</label>
                                    <textarea className="input" value={jobContext.why_exciting} onChange={e => updateJobField('why_exciting', e.target.value)} rows={2} />
                                </div>
                            </div>
                        </div>

                        <div style={{ display: 'flex', gap: 'var(--spacing-md)', justifyContent: 'flex-end' }}>
                            <button className="btn-secondary" onClick={() => { setIsCreating(false); setNewSendNotes(false); }}>Cancel</button>
                            <button className="btn-primary" onClick={handleCreateCampaign} disabled={!newCampaignName.trim()}>
                                <Plus size={16} /> Create Campaign
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: 'var(--spacing-xl)' }}>
                {/* Sidebar List */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }} className="stagger-children">
                    {state.campaigns.map(camp => (
                        <div
                            key={camp.id}
                            onClick={() => { setSelectedCampaign(camp); setActiveTab('pipeline'); }}
                            style={{
                                padding: 'var(--spacing-md) var(--spacing-lg)',
                                borderRadius: 'var(--radius-md)',
                                background: selectedCampaign?.id === camp.id ? 'var(--accent-light)' : 'transparent',
                                border: '1px solid ' + (selectedCampaign?.id === camp.id ? 'rgba(139, 92, 246, 0.2)' : 'transparent'),
                                cursor: 'pointer', transition: 'all 0.2s ease',
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span style={{ fontWeight: 600, fontSize: '0.9rem', color: selectedCampaign?.id === camp.id ? 'var(--accent-text)' : 'var(--text-primary)' }}>{camp.name}</span>
                            </div>
                        </div>
                    ))}
                    {state.campaigns.length === 0 && (
                        <div style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '0.85rem', padding: 'var(--spacing-lg)' }}>No campaigns yet.</div>
                    )}
                </div>

                {/* Main View */}
                {selectedCampaign ? (
                    <div className="animate-fadeIn">
                        {/* Stats Bar */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-xl)' }}>
                            <StatCard icon={<Users size={20} />} label="Pending" value={pending.length} color="var(--text-secondary)" bg="rgba(148, 163, 184, 0.1)" />
                            <StatCard icon={<Send size={20} />} label="Conn. Sent" value={sent.length} color="var(--accent-info)" bg="rgba(59, 130, 246, 0.1)" />
                            <StatCard icon={<CheckCircle size={20} />} label="Accepted" value={accepted.length} color="var(--accent-success)" bg="rgba(16, 185, 129, 0.1)" />
                            <StatCard icon={<Mail size={20} />} label="Msg Sent" value={messageSent.length} color="#8b5cf6" bg="rgba(139, 92, 246, 0.1)" />
                            <StatCard icon={<MessageSquare size={20} />} label="Replied" value={replied.length} color="#f59e0b" bg="rgba(245, 158, 11, 0.1)" />
                        </div>

                        {/* Tabs */}
                        <div style={{ display: 'flex', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-lg)' }}>
                            <TabButton active={activeTab === 'pipeline'} onClick={() => setActiveTab('pipeline')} icon={<Zap size={14} />} label="Pipeline" />
                            <TabButton active={activeTab === 'messages'} onClick={() => setActiveTab('messages')} icon={<Mail size={14} />} label="Follow-Up Messages" count={messages.filter(m => m.initial_message).length} />
                        </div>

                        {/* Campaign Panel */}
                        <div className="glass-panel" style={{ padding: 'var(--spacing-xl)' }}>
                            {activeTab === 'pipeline' ? (
                                <>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-xl)' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)' }}>
                                            <h3 style={{ fontSize: '1.15rem', fontWeight: 600 }}>{selectedCampaign.name}</h3>
                                        </div>
                                        <button className="btn-primary" onClick={() => setShowConfirm(true)} disabled={pending.length === 0} style={{ opacity: pending.length === 0 ? 0.5 : 1 }}>
                                            <Zap size={16} /> Start Automation
                                        </button>
                                        <button className="btn-ghost" onClick={() => setShowAddManualModal(true)} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem' }}>
                                            <Plus size={14} /> Add Candidate
                                        </button>
                                    </div>

                                    {/* Kanban Board */}
                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--spacing-md)' }}>
                                        <KanbanColumn
                                            title="Pending" icon={<Users size={16} />} candidates={pending} color="var(--status-pending)"
                                            showNotes={true} campaignId={selectedCampaign?.id} onNoteEdit={handleEditNote} onDelete={handleDeleteCandidate}
                                        />
                                        <KanbanColumn
                                            title="Connection Sent" icon={<Send size={16} />} candidates={sent} color="var(--status-contacted)"
                                            showNotes={true} campaignId={selectedCampaign?.id} onDelete={handleDeleteCandidate}
                                        />
                                        <KanbanColumn
                                            title="Accepted" icon={<CheckCircle size={16} />} candidates={accepted} color="var(--status-replied)" onDelete={handleDeleteCandidate}
                                        />
                                        <KanbanColumn
                                            title="Msg Sent" icon={<Mail size={16} />} candidates={messageSent} color="#8b5cf6" onDelete={handleDeleteCandidate}
                                        />
                                    </div>
                                </>
                            ) : (
                                <MessagesTab
                                    messages={messages} editingId={editingId} editText={editText} setEditingId={setEditingId} setEditText={setEditText}
                                    onEdit={handleEditMessage} onApprove={handleApproveMessage} onGenerate={handleGenerateMessages} onSend={handleSendMessages}
                                    isGenerating={isGenerating} isSending={isSending} sent={sent}
                                />
                            )}
                        </div>
                    </div>
                ) : (
                    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '400px', gap: 'var(--spacing-md)' }}>
                        <Users size={40} color="var(--text-muted)" style={{ opacity: 0.5 }} />
                        <p style={{ color: 'var(--text-muted)' }}>Select or create a campaign to get started</p>
                    </div>
                )}
            </div>

            {/* Manual Candidate Modal */}
            {showAddManualModal && (
                <div className="modal-overlay">
                    <div className="modal-content animate-scaleIn" style={{ width: '400px' }}>
                        <h3 style={{ marginBottom: 'var(--spacing-lg)', fontSize: '1.1rem' }}>Add Test Candidate</h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            <input type="text" className="input-field" value={manualCandidateName} onChange={e => setManualCandidateName(e.target.value)} placeholder="e.g. John Doe" />
                            <input type="text" className="input-field" value={manualCandidateUrl} onChange={e => setManualCandidateUrl(e.target.value)} placeholder="https://www.linkedin.com/in/..." />
                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--spacing-md)', marginTop: 'var(--spacing-lg)' }}>
                                <button className="btn-ghost" onClick={() => setShowAddManualModal(false)}>Cancel</button>
                                <button className="btn-primary" onClick={() => { handleAddManualCandidate(manualCandidateName, manualCandidateUrl); setShowAddManualModal(false); }}>Add Candidate</button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Confirmation Modal */}
            {showConfirm && (
                <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowConfirm(false)}>
                    <div className="modal-content confirm-dialog">
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-xl)' }}>
                            <div style={{ width: 40, height: 40, borderRadius: 'var(--radius-md)', background: 'rgba(139, 92, 246, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                <Zap size={20} color="var(--accent-primary)" />
                            </div>
                            <div>
                                <h3 style={{ fontSize: '1.1rem' }}>Queue Automation Job</h3>
                                <p style={{ fontSize: '0.85rem', marginTop: '2px' }}>This will be sent to your assigned ghost laptop.</p>
                            </div>
                        </div>

                        <div style={{ display: 'flex', gap: 'var(--spacing-md)', justifyContent: 'flex-end' }}>
                            <button className="btn-secondary" onClick={() => setShowConfirm(false)}>Cancel</button>
                            <button className="btn-primary" onClick={handleStartAutomation} disabled={isStarting}>
                                {isStarting ? <><Loader2 size={16} className="animate-spin" /> Queuing...</> : <><Zap size={16} /> Confirm & Queue</>}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

// --- Sub-Components ---
const labelStyle = { fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.03em' };

function TabButton({ active, onClick, icon, label, count }) {
    return (
        <button
            onClick={onClick}
            style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                padding: 'var(--spacing-sm) var(--spacing-lg)',
                borderRadius: 'var(--radius-md)',
                background: active ? 'var(--accent-light)' : 'transparent',
                border: `1px solid ${active ? 'rgba(139, 92, 246, 0.2)' : 'var(--border-color)'}`,
                color: active ? 'var(--accent-text)' : 'var(--text-secondary)',
                fontWeight: 600, fontSize: '0.85rem',
                cursor: 'pointer', transition: 'all 0.2s ease',
            }}
        >
            {icon} {label}
            {count !== undefined && count > 0 && <span style={{ background: active ? 'rgba(139, 92, 246, 0.2)' : 'var(--bg-tertiary)', padding: '1px 6px', borderRadius: 'var(--radius-full)', fontSize: '0.7rem' }}>{count}</span>}
        </button>
    );
}

function MessagesTab({ messages, editingId, editText, setEditingId, setEditText, onEdit, onApprove, onGenerate, onSend, isGenerating, isSending, sent }) {
    const safeMessages = Array.isArray(messages) ? messages : [];
    const connectionSent = safeMessages.filter(m => m.campaign_status === 'connection_sent');
    const withMessages = connectionSent.filter(m => m.initial_message);
    const approved = connectionSent.filter(m => m.message_status === 'approved');

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-xl)' }}>
                <div>
                    <h3 style={{ fontSize: '1.15rem', fontWeight: 600 }}>Follow-Up Messages</h3>
                </div>
                <div style={{ display: 'flex', gap: 'var(--spacing-md)' }}>
                    <button className="btn-secondary" onClick={onGenerate} disabled={isGenerating}>
                        {isGenerating ? <><Loader2 size={14} className="animate-spin" /> Generating...</> : <><Sparkles size={14} /> Generate Messages</>}
                    </button>
                    <button className="btn-primary" onClick={onSend} disabled={isSending || withMessages.length === 0}>
                        {isSending ? <><Loader2 size={14} className="animate-spin" /> Queuing Job...</> : <><Send size={14} /> Queue Send Job</>}
                    </button>
                </div>
            </div>

            {connectionSent.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 'var(--spacing-2xl)', color: 'var(--text-muted)' }}>
                    <Mail size={32} style={{ opacity: 0.3, marginBottom: 'var(--spacing-md)' }} />
                    <p>No candidates with Connection Sent.</p>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
                    {connectionSent.map(c => (
                        <div key={c.id} style={{ background: 'var(--bg-primary)', padding: 'var(--spacing-lg)', borderRadius: 'var(--radius-md)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <strong>{c.name}</strong>
                            </div>
                            {c.initial_message ? (
                                <div style={{ marginTop: '8px', fontSize: '0.85rem' }}>{c.initial_message}</div>
                            ) : (
                                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No message generated.</div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function StatCard({ icon, label, value, color, bg }) {
    return (
        <div className="stat-card">
            <div className="stat-icon" style={{ background: bg, color }}>{icon}</div>
            <div>
                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)' }}>{value}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 500 }}>{label}</div>
            </div>
        </div>
    );
}

function KanbanColumn({ title, icon, candidates, color, showNotes, campaignId, onNoteEdit, onDelete }) {
    return (
        <div style={{ flex: 1, background: 'var(--bg-secondary)', borderRadius: '12px', padding: '16px', border: '1px solid var(--border-color)', minWidth: '280px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', color: color, fontWeight: 600 }}>
                {icon} <span>{title}</span> <span style={{ marginLeft: 'auto', background: 'var(--bg-primary)', padding: '2px 8px', borderRadius: '12px', fontSize: '0.8rem' }}>{candidates.length}</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto' }}>
                {candidates.map(c => (
                    <div key={c.id} style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                        <div style={{ fontWeight: 600 }}>{c.name}</div>
                        {c.connection_note && <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '8px', fontStyle: 'italic' }}>"{c.connection_note}"</div>}
                    </div>
                ))}
            </div>
        </div>
    );
}
