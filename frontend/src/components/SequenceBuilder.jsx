
import { Zap, Clock, MessageSquare, Plus } from 'lucide-react';

const STEP_CONFIG = {
    connect: { icon: <Zap size={16} />, color: 'var(--accent-primary)', bg: 'rgba(139, 92, 246, 0.12)' },
    wait: { icon: <Clock size={16} />, color: 'var(--accent-warning)', bg: 'rgba(245, 158, 11, 0.12)' },
    message: { icon: <MessageSquare size={16} />, color: 'var(--accent-info)', bg: 'rgba(59, 130, 246, 0.12)' },
};

const DEFAULT_STEPS = [
    { type: 'connect', label: 'Send Connection', desc: 'AI personalized note' },
    { type: 'wait', label: 'Wait 3 Days', desc: 'Smart delay' },
    { type: 'message', label: 'Follow-up Message', desc: 'Custom template' },
    { type: 'wait', label: 'Wait 5 Days', desc: 'If no reply' },
    { type: 'message', label: 'Break-up Message', desc: 'Final touchpoint' },
];

export function SequenceBuilder() {
    return (
        <div style={{ maxWidth: '600px', margin: '0 auto', paddingTop: 'var(--spacing-3xl)' }} className="animate-fadeIn">
            <div style={{ marginBottom: 'var(--spacing-2xl)' }}>
                <h1 style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: 'var(--spacing-xs)' }}>Sequences</h1>
                <p>Build multi-step outreach automation flows</p>
            </div>

            <div className="glass-panel" style={{ padding: 'var(--spacing-xl)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-xl)' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Default Sequence</h3>
                    <span className="badge badge-accent">5 Steps</span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }} className="stagger-children">
                    {DEFAULT_STEPS.map((step, i) => {
                        const config = STEP_CONFIG[step.type];
                        return (
                            <div key={i}>
                                <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 'var(--spacing-lg)',
                                    padding: 'var(--spacing-md) 0',
                                }}>
                                    {/* Timeline Node */}
                                    <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                        <div style={{
                                            width: 36,
                                            height: 36,
                                            borderRadius: '50%',
                                            background: config.bg,
                                            border: `2px solid ${config.color}40`,
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            color: config.color,
                                            zIndex: 1,
                                        }}>
                                            {config.icon}
                                        </div>
                                    </div>

                                    {/* Step Info */}
                                    <div style={{ flex: 1 }}>
                                        <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>{step.label}</div>
                                        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{step.desc}</div>
                                    </div>

                                    {/* Step Number */}
                                    <span style={{
                                        fontSize: '0.7rem',
                                        color: 'var(--text-muted)',
                                        fontWeight: 500,
                                    }}>
                                        Step {i + 1}
                                    </span>
                                </div>

                                {/* Connecting Line */}
                                {i < DEFAULT_STEPS.length - 1 && (
                                    <div style={{
                                        width: 2,
                                        height: 24,
                                        background: 'linear-gradient(to bottom, var(--border-color), transparent)',
                                        marginLeft: 17,
                                    }} />
                                )}
                            </div>
                        );
                    })}
                </div>

                {/* Add Step */}
                <div style={{ marginTop: 'var(--spacing-xl)', paddingTop: 'var(--spacing-lg)', borderTop: '1px solid var(--border-color)' }}>
                    <button className="btn-secondary" style={{ width: '100%', justifyContent: 'center' }}>
                        <Plus size={16} />
                        Add Step
                    </button>
                </div>
            </div>
        </div>
    );
}
