# Design System

## Direction
Personality: Clarity & Warmth (Juicebox Style)
Foundation: White / Gray / Purple
Depth: Soft Shadows + Borders

## Tokens
### Spacing
Base: 4px
Scale: 4, 8, 12, 16, 24, 32, 48, 64

### Colors
--bg-primary: #ffffff
--bg-secondary: #f9fafb
--text-primary: #111827
--text-secondary: #4b5563
--accent-primary: #8b5cf6
--accent-light: #f3e8ff
--border-color: #e5e7eb

### Typography
Font: Inter, sans-serif
Weights: 400 (Regular), 500 (Medium), 600 (SemiBold)

## Patterns
### Surfaces
- **Panel**: White background, `1px solid var(--border-color)`, `radius-lg` (12px), `shadow-sm`.
- **Card**: White background, `1px solid var(--border-color)`, `radius-md` (8px), hover `shadow-md` & `border-accent`.

### Interactive
- **Button Primary**: `bg-accent`, `text-white`, `radius-full` (for pills) or `radius-md`.
- **Input**: `bg-white`, `border-transparent` (hero) or `border-gray-200`, `radius-xl` (24px).

### Layout
- **Sidebar**: Fixed width (240px), clean white, minimal icons, active state `accent-light` + `accent-text`.
- **Dashboard**: Centralized "Hero" search input, max-width container.
