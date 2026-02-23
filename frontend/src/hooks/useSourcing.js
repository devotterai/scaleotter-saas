
import { useState, useCallback } from 'react';
import { ACTIONS, useAppContext } from '../context/AppContext';

export function useSourcing() {
    const { dispatch } = useAppContext();
    const [sourcingStats, setSourcingStats] = useState({ scanned: 0, matched: 0 });

    const startSourcing = useCallback(async (criteria) => {
        dispatch({ type: ACTIONS.START_SOURCING });
        dispatch({ type: ACTIONS.CLEAR_LOGS });
        dispatch({ type: ACTIONS.LOG, payload: `Starting search for: "${criteria.query}"` });
        setSourcingStats({ scanned: 0, matched: 0 });

        try {
            dispatch({ type: ACTIONS.LOG, payload: "Sending request to backend (PDL + AI)..." });
            const response = await fetch('http://localhost:8000/api/source', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: criteria.query }),
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Sourcing failed');
            }

            dispatch({ type: ACTIONS.LOG, payload: "Response received. Processing candidates..." });
            const data = await response.json();

            // Helper to capitalize
            const capitalize = (str) => str ? str.split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ') : '';

            // Map Backend Data -> Frontend UI
            const mappedCandidates = (data.candidates || []).map(c => ({
                id: c.id,
                name: capitalize(c.full_name),
                role: capitalize(c.headline),
                company: capitalize(c.work_history[0]?.company || 'Unknown'), // Get most recent
                location: capitalize(c.location || 'Unknown'),
                matchScore: c.ai_score || 0,
                avatar: `https://ui-avatars.com/api/?name=${encodeURIComponent(c.full_name)}&background=random`,
                experience: c.years_experience,
                relevant_experience: c.relevant_experience,
                experience_breakdown: c.experience_breakdown,
                summary: c.summary,
                education: c.education,
                skills: c.skills,
                linkedin_url: c.linkedin_url,
                work_email: c.work_email,
                reasoning: c.ai_reasoning
            }));

            dispatch({ type: ACTIONS.LOG, payload: `Found ${mappedCandidates.length} candidates. (Total Matches: ${data.total_matches})` });
            dispatch({ type: ACTIONS.ADD_CANDIDATES, payload: mappedCandidates });
            setSourcingStats({
                scanned: data.total_matches || mappedCandidates.length,
                matched: mappedCandidates.length
            });
            dispatch({ type: ACTIONS.LOG, payload: "Sourcing complete." });

        } catch (error) {
            console.error("Sourcing Error:", error);
            dispatch({ type: ACTIONS.LOG, payload: `ERROR: ${error.message}` });
        } finally {
            dispatch({ type: ACTIONS.STOP_SOURCING });
        }
    }, [dispatch]);

    const fetchHistory = useCallback(async () => {
        try {
            dispatch({ type: ACTIONS.LOG, payload: "Loading candidate history..." });
            const response = await fetch('http://localhost:8000/api/candidates');
            if (!response.ok) throw new Error("Failed to load history");

            const candidates = await response.json();
            // Helper to capitalize
            const capitalize = (str) => str ? str.split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ') : '';

            const mapped = candidates.map(c => ({
                id: c.id,
                name: capitalize(c.full_name),
                role: capitalize(c.headline),
                company: capitalize(c.company || 'Unknown'),
                location: capitalize(c.location || 'Unknown'),
                matchScore: c.ai_score || 0,
                avatar: `https://ui-avatars.com/api/?name=${encodeURIComponent(c.full_name)}&background=random`,
                experience: c.years_experience,
                relevant_experience: c.relevant_experience,
                experience_breakdown: c.experience_breakdown,
                summary: c.summary,
                education: c.education,
                skills: c.skills,
                linkedin_url: c.linkedin_url,
                work_email: c.work_email,
                reasoning: c.ai_reasoning
            }));

            dispatch({ type: ACTIONS.ADD_CANDIDATES, payload: mapped });
            dispatch({ type: ACTIONS.LOG, payload: `Loaded ${mapped.length} candidates from history.` });
        } catch (error) {
            console.error("History Error:", error);
            dispatch({ type: ACTIONS.LOG, payload: "Error loading history." });
        }
    }, [dispatch]);

    return { startSourcing, sourcingStats, fetchHistory };
}
