import { useState, useEffect } from 'react';
import { X, Linkedin, Loader2, CheckCircle, AlertCircle, Shield, KeyRound } from 'lucide-react';
import { useAppContext, ACTIONS } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { supabase } from '../lib/supabase';

export function LoginModal({ isOpen, onClose }) {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [twoFactorCode, setTwoFactorCode] = useState('');

    // 'idle' | 'loading' | 'needs_2fa' | 'submitting_2fa' | 'success' | 'error'
    const [status, setStatus] = useState('idle');
    const [message, setMessage] = useState('');
    const [currentJobId, setCurrentJobId] = useState(null);
    const { profile } = useAuth();
    const { dispatch } = useAppContext();

    // Listen for Realtime Job Updates from the Ghost Laptop
    useEffect(() => {
        if (!currentJobId || !isOpen) return;

        const sub = supabase.channel(`job-${currentJobId}`)
            .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'job_runs', filter: `id=eq.${currentJobId}` }, (payload) => {
                const newStatus = payload.new.status;
                if (newStatus === 'waiting_for_2fa') {
                    setStatus('needs_2fa');
                    setMessage('LinkedIn requires a 2FA code. Please check your authenticator app or email.');
                } else if (newStatus === 'completed') {
                    setStatus('success');
                    setMessage('Connected! Browser session deployed on Ghost Laptop.');
                    dispatch({ type: ACTIONS.SET_USER, payload: { name: email.split('@')[0], isConnected: true } });
                    setTimeout(() => {
                        onClose();
                        setStatus('idle');
                        setTwoFactorCode('');
                    }, 2500);
                } else if (newStatus === 'failed') {
                    setStatus('error');
                    setMessage(payload.new.error_message || 'Login failed on the Ghost Laptop.');
                }
            })
            .subscribe();

        return () => supabase.removeChannel(sub);
    }, [currentJobId, isOpen, dispatch, email, onClose]);

    if (!isOpen) return null;

    const handleSubmit = async (e) => {
        e.preventDefault();
        setStatus('loading');
        setMessage('Queuing login job for the Ghost Laptop...');

        try {
            // Find an available ghost laptop for this org
            const { data: devices } = await supabase
                .from('devices')
                .select('id')
                .eq('organization_id', profile.organization_id)
                .limit(1);

            if (!devices || devices.length === 0) {
                throw new Error("No ghost laptops are assigned to your organization. Check Settings.");
            }

            const deviceId = devices[0].id;

            // Insert login job matching the ghost engine's expected workflow
            const { data: job, error } = await supabase.from('job_runs').insert({
                organization_id: profile.organization_id,
                device_id: deviceId,
                job_type: 'login',
                payload: { email, password },
                status: 'pending' // Ghost Engine will pick this up
            }).select().single();

            if (error) throw error;
            setCurrentJobId(job.id);

        } catch (error) {
            setStatus('error');
            setMessage(error.message || 'Could not queue login job.');
        }
    };

    const handle2FASubmit = async (e) => {
        e.preventDefault();
        setStatus('submitting_2fa');
        try {
            // Re-fetch existing payload to append the 2fa code
            const { data: currentJob } = await supabase.from('job_runs').select('payload').eq('id', currentJobId).single();
            const newPayload = { ...currentJob.payload, two_factor_code: twoFactorCode };

            await supabase.from('job_runs').update({
                payload: newPayload,
                status: 'pending' // Resume processing
            }).eq('id', currentJobId);

            setStatus('loading');
            setMessage('Verifying 2FA code on the Ghost Laptop...');

        } catch (error) {
            setStatus('error');
            setMessage('Failed to send 2FA code to the Ghost Laptop.');
        }
    };

    return (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="modal-content" style={{ width: '420px', padding: 'var(--spacing-2xl)', position: 'relative' }}>
                <button
                    onClick={onClose}
                    style={{
                        position: 'absolute',
                        top: 'var(--spacing-lg)',
                        right: 'var(--spacing-lg)',
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        color: 'var(--text-muted)',
                        transition: 'color 0.2s',
                    }}
                    onMouseOver={e => e.currentTarget.style.color = 'var(--text-primary)'}
                    onMouseOut={e => e.currentTarget.style.color = 'var(--text-muted)'}
                >
                    <X size={18} />
                </button>

                {/* Header */}
                <div style={{ textAlign: 'center', marginBottom: 'var(--spacing-xl)' }}>
                    <div style={{
                        width: 52,
                        height: 52,
                        borderRadius: 'var(--radius-lg)',
                        background: 'linear-gradient(135deg, #0077b5, #005f8d)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        margin: '0 auto var(--spacing-md)',
                        boxShadow: '0 4px 14px rgba(0, 119, 181, 0.3)',
                    }}>
                        <Linkedin size={24} color="white" />
                    </div>
                    <h2 style={{ fontSize: '1.2rem', marginBottom: 'var(--spacing-xs)' }}>Connect LinkedIn</h2>
                    <p style={{ fontSize: '0.85rem' }}>Authenticate your account on your assigned Ghost Laptop execution node.</p>
                </div>

                {/* Conditional Form Body depending on State */}
                {status === 'needs_2fa' || status === 'submitting_2fa' ? (
                    <form onSubmit={handle2FASubmit} className="animate-scaleIn" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)' }}>
                        <div style={{ textAlign: 'center', padding: 'var(--spacing-md)', background: 'rgba(245, 158, 11, 0.08)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
                            <KeyRound size={28} color="#f59e0b" style={{ margin: '0 auto 8px' }} />
                            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>Two-Factor Authentication</h3>
                            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{message}</p>
                        </div>

                        <div>
                            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 500, marginBottom: '6px', color: 'var(--text-secondary)', textAlign: 'center' }}>Enter 6-digit Code</label>
                            <input
                                type="text"
                                value={twoFactorCode}
                                onChange={(e) => setTwoFactorCode(e.target.value)}
                                required
                                className="input"
                                placeholder="123456"
                                style={{ textAlign: 'center', letterSpacing: '4px', fontSize: '1.2rem', padding: '0.75rem' }}
                                maxLength={8}
                                autoFocus
                            />
                        </div>

                        <button
                            type="submit"
                            className="btn-primary"
                            disabled={status === 'submitting_2fa' || twoFactorCode.length < 4}
                            style={{ width: '100%', justifyContent: 'center', padding: '0.75rem' }}
                        >
                            {status === 'submitting_2fa' ? <><Loader2 size={16} className="animate-spin" /> Verifying...</> : 'Submit Code'}
                        </button>
                    </form>
                ) : (
                    <form onSubmit={handleSubmit} className="animate-scaleIn" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-lg)' }}>
                        <div>
                            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 500, marginBottom: '6px', color: 'var(--text-secondary)' }}>Email</label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                className="input"
                                placeholder="name@company.com"
                                disabled={status === 'loading'}
                            />
                        </div>

                        <div>
                            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 500, marginBottom: '6px', color: 'var(--text-secondary)' }}>Password</label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                className="input"
                                placeholder="••••••••"
                                disabled={status === 'loading'}
                            />
                        </div>

                        {/* Status Messages */}
                        {status === 'error' && (
                            <div style={{
                                padding: '0.75rem', background: 'rgba(239, 68, 68, 0.1)', color: '#f87171',
                                borderRadius: 'var(--radius-md)', fontSize: '0.85rem', display: 'flex',
                                gap: '0.5rem', alignItems: 'center', border: '1px solid rgba(239, 68, 68, 0.2)',
                            }}>
                                <AlertCircle size={16} /> {message}
                            </div>
                        )}

                        {status === 'success' && (
                            <div style={{
                                padding: '0.75rem', background: 'rgba(16, 185, 129, 0.1)', color: '#34d399',
                                borderRadius: 'var(--radius-md)', fontSize: '0.85rem', display: 'flex',
                                gap: '0.5rem', alignItems: 'center', border: '1px solid rgba(16, 185, 129, 0.2)',
                            }}>
                                <CheckCircle size={16} /> {message}
                            </div>
                        )}

                        <button
                            type="submit"
                            className="btn-primary"
                            disabled={status === 'loading' || status === 'success'}
                            style={{
                                width: '100%', justifyContent: 'center', padding: '0.75rem',
                                opacity: (status === 'loading' || status === 'success') ? 0.7 : 1,
                            }}
                        >
                            {status === 'loading' ? (
                                <><Loader2 size={16} className="animate-spin" /> Connecting Router...</>
                            ) : status === 'success' ? (
                                <><CheckCircle size={16} /> Connected</>
                            ) : 'Connect Account'}
                        </button>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
                            <Shield size={12} color="var(--text-muted)" />
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textAlign: 'center' }}>
                                Credentials are sent securely directly to your assigned Ghost Node execution hardware.
                            </span>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
}
