---
name: interface-design
description: Build interfaces with intention, memory, and consistency. Follows a system-based approach for UI design.
---

# Interface Design

Build interfaces with intention. Remember decisions across sessions. Maintain systematic consistency.

## Core Principles

1.  **Craft**: Principle-based design that produces professional, polished interfaces.
2.  **Memory**: Save decisions to `.interface-design/system.md`.
3.  **Consistency**: Every component follows the same principles.

## How It Works

When building UI:

1.  **Check for System**: Look for `.interface-design/system.md`.
    -   If found: Read it and apply established patterns (Colors, Spacing, Depth).
    -   If not found: Establish a direction (Precision, Warmth, etc.) and create it.

2.  **Apply Principles**:
    -   **Spacing**: Use valid scales (e.g., 4px, 8px, 16px).
    -   **Depth**: Consistent strategy (borders-only vs shadows).
    -   **Surfaces**: Consistent elevation and background colors.

3.  **Save Decisions**: Update `system.md` with new patterns as they emerge.

## System File Structure (`.interface-design/system.md`)

```markdown
# Design System

## Direction
Personality: Precision & Density
Foundation: Cool (slate)
Depth: Borders-only

## Tokens
### Spacing
Base: 4px
Scale: 4, 8, 12, 16, 24, 32

### Colors
--bg-primary: #ffffff
--accent-primary: #8b5cf6

## Patterns
### Card
- Border: 1px solid #e5e7eb
- Radius: 12px
- Shadow: sm
```

## Usage

-   **Start**: When beginning a UI task, initialize or read the design system.
-   **Audit**: Check if current code matches the system.
-   **Extract**: Document new patterns into the system file.
