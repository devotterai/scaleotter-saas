import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
    Search,
    LayoutDashboard,
    Zap,
    Settings,
    Bell,
    ChevronDown,
    LogOut
} from 'lucide-react';
import { LoginModal } from './LoginModal';
import { useAuth } from '../context/AuthContext';

export function Sidebar() {
    const location = useLocation();
    const isActive = (path) => location.pathname === path;
    const [isLoginOpen, setIsLoginOpen] = useState(false);

    // Pull from Supabase
    const { user, profile, signOut } = useAuth();

    const navItems = [
        { icon: <Search size={18} />, label: 'Searches', path: '/' },
        { icon: <LayoutDashboard size={18} />, label: 'Campaigns', path: '/campaigns' },
        { icon: <Zap size={18} />, label: 'Sequences', path: '/sequences' },
        { icon: <Settings size={18} />, label: 'Settings', path: '/settings' },
    ];

    return (
        <aside style={{
            width: '260px',
            height: '100vh',
            background: 'var(--bg-primary)',
            borderRight: '1px solid var(--border-color)',
            display: 'flex',
            flexDirection: 'column',
            padding: '0',
            position: 'sticky',
            top: 0,
        }}>
            {/* Logo Area */}
            <div style={{
                padding: 'var(--spacing-xl) var(--spacing-xl)',
                borderBottom: '1px solid var(--border-color)',
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--spacing-md)',
            }}>
                <div style={{
                    width: 36,
                    height: 36,
                    borderRadius: 'var(--radius-md)',
                    background: 'linear-gradient(135deg, var(--accent-primary), #7c3aed)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 0 16px rgba(139, 92, 246, 0.3)',
                }}>
                    <span style={{ fontSize: '1.2rem' }}>🦦</span>
                </div>
                <div>
                    <h2 style={{ fontSize: '1.1rem', fontWeight: 700, letterSpacing: '-0.02em' }}>ScaleOtter</h2>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 500, letterSpacing: '0.05em' }}>AUTOMATION</span>
                </div>
            </div>

            {/* Navigation */}
            <nav style={{ flex: 1, padding: 'var(--spacing-lg) var(--spacing-md)', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <div style={{
                    fontSize: '0.68rem',
                    fontWeight: 600,
                    color: 'var(--text-muted)',
                    marginBottom: 'var(--spacing-sm)',
                    paddingLeft: 'var(--spacing-md)',
                    letterSpacing: '0.1em',
                    textTransform: 'uppercase',
                }}>
                    Navigation
                </div>

                {navItems.map((item) => (
                    <Link
                        key={item.path}
                        to={item.path}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                            padding: '0.6rem 0.75rem',
                            borderRadius: 'var(--radius-md)',
                            textDecoration: 'none',
                            color: isActive(item.path) ? 'var(--accent-text)' : 'var(--text-secondary)',
                            background: isActive(item.path) ? 'var(--accent-light)' : 'transparent',
                            fontWeight: isActive(item.path) ? 600 : 500,
                            fontSize: '0.875rem',
                            transition: 'all 0.2s ease',
                            position: 'relative',
                        }}
                    >
                        {isActive(item.path) && (
                            <div style={{
                                position: 'absolute',
                                left: '-12px',
                                top: '50%',
                                transform: 'translateY(-50%)',
                                width: '3px',
                                height: '20px',
                                borderRadius: '0 3px 3px 0',
                                background: 'var(--accent-primary)',
                            }} />
                        )}
                        {item.icon}
                        <span>{item.label}</span>
                    </Link>
                ))}
            </nav>

            {/* Bottom: User Profile */}
            <div style={{ borderTop: '1px solid var(--border-color)', padding: 'var(--spacing-md)' }}>
                <div
                    onClick={() => signOut()}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 'var(--spacing-md)',
                        padding: '0.6rem var(--spacing-md)',
                        borderRadius: 'var(--radius-md)',
                        cursor: 'pointer',
                        transition: 'background 0.2s ease',
                    }}
                    onMouseOver={e => e.currentTarget.style.background = 'var(--bg-secondary)'}
                    onMouseOut={e => e.currentTarget.style.background = 'transparent'}
                >
                    <div style={{ position: 'relative' }}>
                        <div style={{
                            width: 34,
                            height: 34,
                            borderRadius: '50%',
                            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '0.85rem',
                            fontWeight: 600,
                            color: 'white',
                        }}>
                            {profile?.full_name?.charAt(0) || user?.email?.charAt(0) || 'G'}
                        </div>
                    </div>
                    <div style={{ flex: 1, overflow: 'hidden', minWidth: 0 }}>
                        <div style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {profile?.full_name || user?.email}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                            {profile?.role ? profile.role.toUpperCase() : 'USER'}
                        </div>
                    </div>
                    <LogOut size={14} color="var(--text-muted)" />
                </div>
            </div>

            <LoginModal isOpen={isLoginOpen} onClose={() => setIsLoginOpen(false)} />
        </aside>
    );
}

export function MainLayout({ children }) {
    return (
        <div className="grid-dashboard">
            <Sidebar />
            <main style={{
                height: '100vh',
                overflowY: 'auto',
                background: 'linear-gradient(180deg, var(--bg-primary) 0%, rgba(30, 41, 59, 0.5) 100%)',
                padding: 'var(--spacing-2xl) var(--spacing-2xl)',
            }}>
                {children}
            </main>
        </div>
    );
}
