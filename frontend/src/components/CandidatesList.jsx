
import { useState } from 'react';
import { MapPin, Building, Linkedin, Mail, Plus, ChevronDown, ExternalLink } from 'lucide-react';
import { useAppContext, ACTIONS } from '../context/AppContext';
import { useToast } from './Toast';

function CandidateCard({ candidate }) {
    const { state } = useAppContext();
    const toast = useToast();
    const [showCampaignMenu, setShowCampaignMenu] = useState(false);
    const [isAdding, setIsAdding] = useState(false);

    const handleAddToCampaign = async (campaignId, campaignName) => {
        setIsAdding(true);
        try {
            const res = await fetch(`http://localhost:8000/api/campaigns/${campaignId}/add`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ candidate_id: candidate.id })
            });
            if (res.ok) {
                toast.success(`Added ${candidate.name} to ${campaignName}`);
                setShowCampaignMenu(false);
            }
        } catch (err) {
            toast.error("Failed to add candidate");
        } finally {
            setIsAdding(false);
        }
    };

    const scoreColor = candidate.matchScore > 90 ? '#10b981' : candidate.matchScore > 80 ? '#3b82f6' : '#f59e0b';

    return (
        <div className="glass-card" style={{
            display: 'flex',
            gap: 'var(--spacing-lg)',
            alignItems: 'flex-start',
            position: 'relative',
        }}>
            {/* Avatar + Score */}
            <div style={{ position: 'relative', flexShrink: 0 }}>
                <div style={{
                    width: 48,
                    height: 48,
                    borderRadius: '50%',
                    background: `linear-gradient(135deg, ${scoreColor}30, ${scoreColor}10)`,
                    border: `2px solid ${scoreColor}40`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1.1rem',
                    fontWeight: 600,
                    color: scoreColor,
                }}>
                    {candidate.matchScore}
                </div>
            </div>

            {/* Content */}
            <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', marginBottom: '4px' }}>
                    <h4 style={{ fontSize: '0.95rem', fontWeight: 600 }}>{candidate.name}</h4>
                </div>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                    {candidate.role}
                </p>
                <div style={{ display: 'flex', gap: 'var(--spacing-lg)', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '10px', flexWrap: 'wrap' }}>
                    {candidate.company && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Building size={12} /> {candidate.company}</span>
                    )}
                    {candidate.location && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><MapPin size={12} /> {candidate.location}</span>
                    )}
                </div>

                {/* Experience Breakdown */}
                {candidate.experience_breakdown && candidate.experience_breakdown.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '10px' }}>
                        {candidate.experience_breakdown.map((item, i) => (
                            <span key={i} className="badge badge-info">
                                <strong>{item.years}y</strong>&nbsp;{item.role}
                            </span>
                        ))}
                    </div>
                )}

                {/* Summary */}
                {candidate.summary && (
                    <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '10px', lineHeight: '1.5' }}>
                        {candidate.summary.length > 180 ? candidate.summary.substring(0, 180) + '...' : candidate.summary}
                    </p>
                )}

                {/* Skills */}
                {candidate.skills && candidate.skills.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '10px' }}>
                        {candidate.skills.slice(0, 5).map((skill, i) => (
                            <span key={i} style={{
                                background: 'var(--bg-tertiary)',
                                padding: '2px 8px',
                                borderRadius: 'var(--radius-full)',
                                fontSize: '0.72rem',
                                color: 'var(--text-secondary)',
                            }}>
                                {skill}
                            </span>
                        ))}
                        {candidate.skills.length > 5 && (
                            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', alignSelf: 'center' }}>+{candidate.skills.length - 5}</span>
                        )}
                    </div>
                )}

                {/* AI Reasoning */}
                {candidate.reasoning && (
                    <div style={{
                        fontSize: '0.8rem',
                        color: 'var(--text-secondary)',
                        background: 'var(--accent-light)',
                        padding: '10px 12px',
                        borderRadius: 'var(--radius-md)',
                        borderLeft: '3px solid var(--accent-primary)',
                        lineHeight: 1.4,
                    }}>
                        <strong style={{ color: 'var(--accent-text)' }}>AI:</strong> {candidate.reasoning}
                    </div>
                )}
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: '6px', flexShrink: 0, alignItems: 'flex-start' }}>
                {candidate.linkedin_url && (
                    <a
                        href={candidate.linkedin_url?.startsWith('http') ? candidate.linkedin_url : `https://${candidate.linkedin_url}`}
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        <ActionBtn icon={<Linkedin size={14} />} title="LinkedIn" />
                    </a>
                )}
                {candidate.work_email && (
                    <a href={`mailto:${candidate.work_email}`}>
                        <ActionBtn icon={<Mail size={14} />} title="Email" />
                    </a>
                )}

                <div style={{ position: 'relative' }}>
                    <button
                        className="btn-primary"
                        onClick={() => setShowCampaignMenu(!showCampaignMenu)}
                        style={{ padding: '6px 8px', fontSize: '0.8rem' }}
                        title="Add to Campaign"
                    >
                        <Plus size={14} />
                    </button>

                    {showCampaignMenu && (
                        <>
                            {/* Click-away layer */}
                            <div
                                style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 9 }}
                                onClick={() => setShowCampaignMenu(false)}
                            />
                            <div style={{
                                position: 'absolute',
                                right: 0,
                                top: '100%',
                                marginTop: '6px',
                                background: 'var(--bg-secondary)',
                                border: '1px solid var(--border-color)',
                                borderRadius: 'var(--radius-md)',
                                boxShadow: 'var(--shadow-lg)',
                                zIndex: 10,
                                minWidth: '200px',
                                padding: '6px',
                            }} className="animate-slideDown">
                                <div style={{ fontSize: '0.68rem', fontWeight: 600, color: 'var(--text-muted)', padding: '6px 10px', letterSpacing: '0.05em' }}>
                                    SELECT CAMPAIGN
                                </div>
                                {state.campaigns && state.campaigns.length > 0 ? (
                                    state.campaigns.map(camp => (
                                        <div
                                            key={camp.id}
                                            onClick={() => handleAddToCampaign(camp.id, camp.name)}
                                            style={{
                                                padding: '8px 10px',
                                                fontSize: '0.85rem',
                                                cursor: 'pointer',
                                                borderRadius: 'var(--radius-sm)',
                                                color: 'var(--text-primary)',
                                                transition: 'background 0.15s',
                                            }}
                                            onMouseOver={e => e.currentTarget.style.background = 'var(--bg-hover)'}
                                            onMouseOut={e => e.currentTarget.style.background = 'transparent'}
                                        >
                                            {camp.name}
                                        </div>
                                    ))
                                ) : (
                                    <div style={{ padding: '8px 10px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                        No campaigns yet
                                    </div>
                                )}
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}

function ActionBtn({ icon, title }) {
    return (
        <button
            className="btn-ghost"
            title={title}
            style={{
                width: 32,
                height: 32,
                padding: 0,
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px solid var(--border-color)',
                color: 'var(--text-secondary)',
            }}
        >
            {icon}
        </button>
    );
}

export function CandidatesList({ candidates }) {
    if (!candidates || candidates.length === 0) {
        return null;
    }

    return (
        <div style={{ marginTop: 'var(--spacing-2xl)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-lg)' }}>
                <h3 style={{ fontSize: '1rem', color: 'var(--text-secondary)' }}>Top Matches ({candidates.length})</h3>
            </div>
            <div style={{ display: 'grid', gap: 'var(--spacing-md)' }} className="stagger-children">
                {candidates.map(candidate => (
                    <CandidateCard key={candidate.id} candidate={candidate} />
                ))}
            </div>
        </div>
    );
}
