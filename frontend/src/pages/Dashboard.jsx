
import { useState, useEffect } from 'react';
import { JobCriteriaInput } from '../components/JobCriteriaInput';
import { CandidatesList } from '../components/CandidatesList';
import { useSourcing } from '../hooks/useSourcing';
import { useAppContext } from '../context/AppContext';

export function Dashboard() {
    const { state } = useAppContext();
    const { startSourcing, sourcingStats, fetchHistory } = useSourcing();

    // Load old searches on mount
    useEffect(() => {
        fetchHistory();
    }, [fetchHistory]);

    const handleAnalyze = (queryText) => {
        startSourcing({ query: queryText });
    };

    return (
        <div className="animate-fadeIn">
            <JobCriteriaInput
                onAnalyze={handleAnalyze}
                isLoading={state.isSourcing}
            />

            {/* Stats */}
            {(sourcingStats.scanned > 0 || sourcingStats.matched > 0) && (
                <div style={{
                    display: 'flex',
                    gap: 'var(--spacing-lg)',
                    justifyContent: 'center',
                    marginTop: 'var(--spacing-2xl)',
                    fontSize: '0.85rem',
                    color: 'var(--text-secondary)',
                }}>
                    <span>Scanned: <strong style={{ color: 'var(--text-primary)' }}>{sourcingStats.scanned}</strong></span>
                    <span>Matched: <strong style={{ color: 'var(--accent-success)' }}>{sourcingStats.matched}</strong></span>
                </div>
            )}

            <CandidatesList candidates={state.candidates} />
        </div>
    );
}
