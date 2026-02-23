
import { createContext, useContext, useReducer } from 'react';

// Initial State
const initialState = {
    candidates: [],
    jobs: [],
    campaigns: [], // New campaign state
    automationSequence: [],
    isSourcing: false,
    user: {
        name: "Alex Recruiter",
        agency: "Elite Talent",
        avatar: "https://i.pravatar.cc/150?img=11"
    },
    logs: []
};

// Actions
export const ACTIONS = {
    START_SOURCING: 'START_SOURCING',
    ADD_CANDIDATES: 'ADD_CANDIDATES',
    STOP_SOURCING: 'STOP_SOURCING',
    ADD_JOB: 'ADD_JOB',
    SET_CAMPAIGNS: 'SET_CAMPAIGNS',
    ADD_CAMPAIGN: 'ADD_CAMPAIGN',
    UPDATE_AUTOMATION: 'UPDATE_AUTOMATION',
    SET_USER: 'SET_USER',
    LOG: 'LOG',
    CLEAR_LOGS: 'CLEAR_LOGS'
};

// Reducer
function appReducer(state, action) {
    switch (action.type) {
        case ACTIONS.START_SOURCING:
            return { ...state, isSourcing: true };
        case ACTIONS.STOP_SOURCING:
            return { ...state, isSourcing: false };
        case ACTIONS.ADD_CANDIDATES: {
            // Deduplicate by id — new entries overwrite old ones
            const merged = new Map(
                state.candidates.map(c => [c.id, c])
            );
            action.payload.forEach(c => merged.set(c.id, c));
            return {
                ...state,
                candidates: Array.from(merged.values())
            };
        }
        case ACTIONS.ADD_JOB:
            return {
                ...state,
                jobs: [...state.jobs, action.payload]
            };
        case ACTIONS.SET_CAMPAIGNS:
            return {
                ...state,
                campaigns: action.payload
            };
        case ACTIONS.ADD_CAMPAIGN:
            return {
                ...state,
                campaigns: [action.payload, ...state.campaigns]
            };
        case ACTIONS.SET_USER:
            return {
                ...state,
                user: { ...state.user, ...action.payload }
            };
        case ACTIONS.LOG:
            return {
                ...state,
                logs: [...state.logs, { time: new Date().toLocaleTimeString(), message: action.payload }]
            };
        case ACTIONS.CLEAR_LOGS:
            return { ...state, logs: [] };
        default:
            return state;
    }
}

// Context
const AppContext = createContext();

// Provider Component
export function AppProvider({ children }) {
    const [state, dispatch] = useReducer(appReducer, initialState);

    return (
        <AppContext.Provider value={{ state, dispatch }}>
            {children}
        </AppContext.Provider>
    );
}

// Custom Hook to use Context
export function useAppContext() {
    const context = useContext(AppContext);
    if (!context) {
        throw new Error('useAppContext must be used within an AppProvider');
    }
    return context;
}
