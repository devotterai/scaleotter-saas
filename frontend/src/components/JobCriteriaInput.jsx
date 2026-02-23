
import { useState } from 'react';
import { Search, Sparkles, Loader2 } from 'lucide-react';

export function JobCriteriaInput({ onAnalyze, isLoading }) {
    const [query, setQuery] = useState('');

    const suggestions = [
        "Sales Managers in NYC with 10+ years",
        "Python Devs in SF with startup experience",
        "Marketing Directors in London",
        "Full Stack Engineers with AWS skills",
    ];

    const handleSubmit = (e) => {
        e.preventDefault();
        if (query.trim()) {
            onAnalyze(query);
        }
    };

    return (
        <div className="animate-fadeIn" style={{ maxWidth: '720px', margin: '0 auto', paddingTop: 'var(--spacing-4xl)' }}>
            {/* Hero */}
            <div style={{ textAlign: 'center', marginBottom: 'var(--spacing-3xl)' }}>
                <div style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 14px',
                    borderRadius: 'var(--radius-full)',
                    background: 'var(--accent-light)',
                    border: '1px solid rgba(139, 92, 246, 0.2)',
                    color: 'var(--accent-text)',
                    fontSize: '0.78rem',
                    fontWeight: 500,
                    marginBottom: 'var(--spacing-lg)',
                }}>
                    <Sparkles size={12} />
                    AI-Powered Talent Sourcing
                </div>

                <h1 className="gradient-text" style={{
                    fontSize: '2.5rem',
                    fontWeight: 800,
                    letterSpacing: '-0.03em',
                    lineHeight: 1.15,
                    marginBottom: 'var(--spacing-md)',
                }}>
                    Find Your Next<br />Perfect Hire
                </h1>

                <p style={{ fontSize: '1rem', color: 'var(--text-secondary)', maxWidth: '480px', margin: '0 auto', lineHeight: 1.6 }}>
                    Describe who you're looking for in plain English. We'll search millions of profiles and score them for you.
                </p>
            </div>

            {/* Search Box */}
            <form onSubmit={handleSubmit}>
                <div className="glass-panel" style={{
                    padding: 'var(--spacing-md)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--spacing-sm)',
                }}>
                    <Search size={18} color="var(--text-muted)" style={{ marginLeft: 'var(--spacing-sm)', flexShrink: 0 }} />
                    <textarea
                        className="search-input"
                        placeholder="e.g. Sales Managers in NYC with 10+ years of SaaS experience..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSubmit(e))}
                        rows={2}
                        style={{
                            flex: 1,
                            resize: 'none',
                            background: 'transparent',
                            border: 'none',
                            boxShadow: 'none',
                        }}
                    />
                    <button
                        type="submit"
                        className="btn-primary"
                        disabled={isLoading || !query.trim()}
                        style={{
                            padding: '10px 20px',
                            opacity: (isLoading || !query.trim()) ? 0.6 : 1,
                            flexShrink: 0,
                        }}
                    >
                        {isLoading ? (
                            <>
                                <Loader2 size={16} className="animate-spin" />
                                Sourcing...
                            </>
                        ) : 'Source'}
                    </button>
                </div>
            </form>

            {/* Suggestions */}
            <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: 'var(--spacing-sm)',
                justifyContent: 'center',
                marginTop: 'var(--spacing-xl)',
            }}>
                {suggestions.map((s, i) => (
                    <button
                        key={i}
                        className="btn-pill"
                        onClick={() => setQuery(s)}
                    >
                        {s}
                    </button>
                ))}
            </div>
        </div>
    );
}
