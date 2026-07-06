# Accessibility

**Target standard:** WCAG 2.2 AA

## A11Y-001 — Every interactive control is fully keyboard operable.

**Acceptance criteria:**
- **Given** a user navigates with the keyboard only **When** they tab through any flow **Then** every interactive control is reachable, operable and follows a logical focus order

## A11Y-002 — Focus is always visible.

**Acceptance criteria:**
- **Given** an element receives keyboard focus **When** the user is navigating **Then** a visible focus indicator is shown and meets the non-text contrast minimum

## A11Y-003 — Colour contrast meets the target standard.

**Acceptance criteria:**
- **Given** any text or essential UI element **When** it is rendered in any supported theme **Then** contrast meets the target (≥ 4.5:1 for body text, ≥ 3:1 for large text and UI)

## A11Y-004 — Every control and image exposes an accessible name.

**Acceptance criteria:**
- **Given** a form control, icon-only button or meaningful image **When** it is read by assistive technology **Then** it exposes a programmatic label/name and images carry meaningful alt text (decorative images are hidden)

## A11Y-005 — Structure and async changes are conveyed semantically.

**Acceptance criteria:**
- **Given** a screen is parsed by a screen reader **When** the user explores it **Then** headings, landmarks and roles convey the structure and live regions announce asynchronous changes

## A11Y-006 — Reduced motion and zoom are respected.

**Acceptance criteria:**
- **Given** a user prefers reduced motion or zooms to 200% **When** they use the product **Then** non-essential motion is reduced or disabled and content reflows without loss of content or function
