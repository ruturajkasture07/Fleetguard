# Design Document: FleetGuard Transport Management UI

## Overview

FleetGuard is a Flask-based Transport Management System serving three user roles — Admin, Driver, and Customer — across 20+ Jinja2 templates. The current UI uses Bootstrap 5 with inline `<style>` blocks scattered across every template and an empty `static/css/` directory.

This design delivers a production-quality UI overhaul: a single `static/css/main.css` design system that replaces all inline styles, a polished visual language built on dark-navy + gold + blue brand colours, glassmorphism-accented cards, smooth micro-animations, and role-specific UX optimisations. No backend routes, models, or Python logic are changed.

### Design Goals

- Single source of truth: all visual decisions live in CSS custom properties inside `main.css`
- Premium feel: depth layers, gradient accents, smooth transitions, Rajdhani + Inter typography
- Role clarity: Admin gets KPI grids; Driver gets large emergency action cards; Customer gets a shipment timeline
- Mobile-first: slide-in sidebar overlay, responsive grids, touch-friendly tap targets
- Accessibility: WCAG 2.1 AA contrast on all text, visible focus rings, text labels on all badges

---

## Architecture

### File Structure

```
static/
  css/
    main.css          <- single stylesheet (all custom styles)
templates/
  base.html           <- shared scaffold: sidebar + topbar + page-body
  login.html          <- standalone auth page (no base.html)
  register.html       <- standalone auth page
  forgot_password.html<- standalone auth page
  admin_dashboard.html
  driver_dashboard.html
  customer_dashboard.html
  trucks.html / truck_form.html
  drivers.html / driver_form.html
  shipments.html / shipment_form.html / customer_shipment_form.html
  users.html / profile.html
  admin_locations.html
  admin_fuel_requests.html / fuel_request.html
  admin_accidents.html / accident_report.html
  admin_breakdowns.html / breakdown_report.html
  admin_call_requests.html / call_request.html
  location_update.html
```

### Dependency Stack

- Bootstrap 5.3 CDN (grid, modals, utilities — no Bootstrap theme overrides)
- Font Awesome 6.4 CDN (icons)
- Google Fonts: Rajdhani (400,500,600,700) + Inter (300,400,500,600)
- Vanilla JS only (no jQuery, no Alpine, no React)
- Razorpay checkout.js (existing, unchanged)

### Layout Model

```
+-- .sidebar (fixed, 250px, z-index:1000) --------+
|   .sidebar-brand  (logo + brand name)           |
|   .sidebar-nav    (role-filtered links)          |
|   .sidebar-footer (avatar + logout)             |
+-------------------------------------------------+
+-- .main-content (margin-left: 250px) -----------+
|   .topbar (sticky, z-index:100)                 |
|   .page-body (padding: 1.75rem)                 |
|     -> {% block content %}                      |
+-------------------------------------------------+
```

Mobile: sidebar off-screen via `translateX(-100%)`, `.sidebar-overlay` covers content, hamburger in topbar.
Tablet (768–1199px): sidebar collapses to 64px icon-only strip, expands to 250px on hover.

---

## Components and Interfaces

### Component Inventory

| Class | Description | Used In |
|---|---|---|
| `.stat-card` | KPI metric widget | All dashboards |
| `.card-table` | White card wrapping a table | All list pages |
| `.form-card` | White card wrapping a form | All form pages |
| `.badge-status` | Pill status label | Tables, dashboards |
| `.driver-action-card` | Large icon action card | driver_dashboard |
| `.alert` | Flash message banner | base.html |
| `.empty-state` | No-data placeholder | Inside .card-table |
| `.auth-layout` | Split-panel auth wrapper | login, register, forgot |
| `.toast-container` | Toast notification stack | base.html (JS-driven) |

### Stat Card

```
+----------------------------------------------+
|  [icon 52x52]  42              <- .stat-value (Rajdhani 2rem 700)
|                TOTAL TRUCKS    <- .stat-label (Inter 0.75rem 500 uppercase)
+----------------------------------------------+
```

- `.stat-icon`: 52x52px, border-radius 12px, coloured background + icon
- Hover: `translateY(-3px)` + deeper shadow, 200ms ease
- Gradient variant `.stat-card--gradient`: linear-gradient background, white text

### Data Table

```
+-- .card-table ----------------------------------------+
|  .card-table-header: [Section Title]  [Action Btn]   |
|  thead: #f8f9fa bg, 0.78rem uppercase, 0.5px spacing |
|  tbody: hover tint #f0f4ff, 0.875rem                 |
|  .empty-state (when no rows)                         |
+-------------------------------------------------------+
```

- Sticky `thead` via `position: sticky; top: 0`
- Action buttons: `.btn-action` — small pill, semantic colour, icon + optional text
- Inline forms (status dropdowns) styled with `.form-select-sm`

### Driver Action Card

```
+-- .driver-action-card --------+
|       [icon 2.5rem]           |
|       Bold Label              |
|       short description       |
+-------------------------------+
```

- Hover: `translateY(-4px)` + shadow, 200ms ease
- Emergency cards (accident, breakdown): red accent top-border `4px solid var(--color-danger)`
- Grid: 2-col mobile -> 3-col tablet -> 4-col desktop

### Auth Layout

```
+-- .auth-layout ----------------------------------------+
|  .auth-left (flex:1, --color-primary bg)              |
|    animated CSS background pattern (floating circles) |
|    logo + tagline + feature list                      |
|  .auth-right (420px, white bg)                        |
|    form with icon-prefixed inputs                     |
+--------------------------------------------------------+
```

Mobile: `.auth-left` hidden, `.auth-right` full-width.

### Toast Notifications

Replace Flask `flash()` alert banners with slide-in toasts:
- `.toast-container`: fixed bottom-right, z-index 9999
- Auto-dismiss after 4s with fade-out
- Categories: success (green), danger (red), warning (amber), info (blue)
- JS reads `data-flash` attributes injected by Jinja into a hidden `<div id="flash-data">`

---

## Data Models

No new data models. The design system operates purely on existing Flask/SQLite data passed to templates. CSS classes map to existing Jinja template variables:

| Template Variable | CSS Class |
|---|---|
| `s.status == 'Pending'` | `.bs-pending` |
| `s.status == 'In Transit'` | `.bs-transit` |
| `s.status == 'Delivered'` | `.bs-delivered` |
| `t.status == 'Available'` | `.bs-available` |
| `t.status == 'On Route'` | `.bs-on-route` |
| `t.status == 'Maintenance'` | `.bs-maintenance` |
| `r.status == 'Approved'` | `.bs-approved` |
| `r.status == 'Rejected'` | `.bs-rejected` |
| `r.payment_status == 'Paid'` | `.bs-paid` |
| `r.payment_status == 'Unpaid'` | `.bs-unpaid` |
| `a.status == 'Reported'` | `.bs-reported` |
| `a.status == 'Resolved'` | `.bs-resolved` |
| `b.status == 'Open'` | `.bs-open` |

---

## Visual Design Language and Design Tokens

### Colour System

All colours are defined as CSS custom properties on `:root` in `main.css`.

#### Brand Colours

```css
--color-primary:   #0a2342;   /* dark navy — sidebar, primary buttons */
--color-primary-hover: #0d3060;
--color-accent:    #e8b04b;   /* gold — active nav border, accent buttons */
--color-accent-2:  #2196f3;   /* blue — focus rings, info badges, links */
```

#### Semantic Colour Tokens (with bg/text variants)

```css
--color-success:      #10b981;
--color-success-bg:   #d1fae5;
--color-success-text: #065f46;

--color-warning:      #f59e0b;
--color-warning-bg:   #fef3c7;
--color-warning-text: #92400e;

--color-danger:       #ef4444;
--color-danger-bg:    #fee2e2;
--color-danger-text:  #991b1b;

--color-info:         #2196f3;
--color-info-bg:      #dbeafe;
--color-info-text:    #1e40af;

--color-purple:       #8b5cf6;
--color-purple-bg:    #ede9fe;
--color-purple-text:  #5b21b6;
```

#### Surface and Text Colours

```css
--color-bg:           #f0f2f5;   /* page background */
--color-surface:      #ffffff;   /* card/panel background */
--color-border:       #e2e6ea;   /* dividers, input borders */
--color-border-light: #f0f0f0;   /* subtle dividers */

--color-text-primary:   #1a1a2e; /* headings, strong text — contrast 14.7:1 on white */
--color-text-secondary: #495057; /* labels, secondary text — contrast 7.0:1 on white */
--color-text-muted:     #6c757d; /* hints, timestamps — contrast 4.6:1 on white */
--color-text-inverse:   #ffffff; /* text on dark backgrounds */
```

#### Sidebar-Specific Tokens

```css
--sidebar-bg:           #0a2342;
--sidebar-w:            250px;
--sidebar-w-collapsed:  64px;
--sidebar-link:         rgba(255,255,255,0.75);
--sidebar-link-hover:   rgba(255,255,255,1);
--sidebar-link-active-bg: rgba(255,255,255,0.08);
--sidebar-section-title: rgba(255,255,255,0.4);
```

### Typography System

```css
--font-display: 'Rajdhani', sans-serif;  /* headings, stat values, brand */
--font-body:    'Inter', sans-serif;     /* body text, labels, nav links */

/* Font size scale */
--text-xs:   0.75rem;   /* 12px — badge labels, timestamps */
--text-sm:   0.875rem;  /* 14px — table cells, body text */
--text-base: 1rem;      /* 16px — default */
--text-lg:   1.25rem;   /* 20px — topbar title, card headings */
--text-xl:   1.5rem;    /* 24px — brand name, auth headings */
--text-2xl:  2rem;      /* 32px — stat values */

/* Line heights */
--leading-tight:  1.2;  /* display headings */
--leading-normal: 1.5;  /* body text */
```

### Spacing Scale

```css
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-5: 1.25rem;   /* 20px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-10: 2.5rem;   /* 40px */
--space-12: 3rem;     /* 48px */
```

### Border Radius Scale

```css
--radius-sm:   8px;   /* inputs, small buttons */
--radius-md:   12px;  /* cards, stat cards, tables */
--radius-lg:   14px;  /* driver action cards, modals */
--radius-xl:   20px;  /* badge pills */
--radius-full: 9999px;/* circular avatars */
```

### Shadow Scale

```css
--shadow-sm:  0 2px 8px rgba(0,0,0,0.05);
--shadow-md:  0 2px 12px rgba(0,0,0,0.06);
--shadow-lg:  0 8px 24px rgba(0,0,0,0.10);
--shadow-xl:  0 10px 28px rgba(0,0,0,0.12);
--shadow-2xl: 0 20px 48px rgba(0,0,0,0.18);
```

### Transition Tokens

```css
--transition-fast:   150ms ease;
--transition-base:   200ms ease;
--transition-slow:   300ms ease;
```

---

## Layout Architecture

### Sidebar

**Desktop (>=1200px)**
- `position: fixed; left: 0; top: 0; height: 100vh; width: var(--sidebar-w)`
- Full labels visible

**Tablet (768–1199px)**
- Width collapses to `var(--sidebar-w-collapsed)` (64px)
- Nav link text hidden via `opacity: 0; width: 0; overflow: hidden`
- On `:hover` sidebar expands to 250px with `transition: width var(--transition-slow)`
- Section titles hidden in collapsed state

**Mobile (<768px)**
- `transform: translateX(-100%)` by default
- `.sidebar.open` -> `transform: translateX(0)`
- `.sidebar-overlay` div inserted into DOM, `position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 999`
- Hamburger button `#sidebar-toggle` in topbar, `display: none` on desktop

### Topbar

- `position: sticky; top: 0; z-index: 100`
- `background: var(--color-surface); border-bottom: 1px solid var(--color-border)`
- `box-shadow: var(--shadow-sm)`
- Left: hamburger (mobile only) + page title in `--font-display` at `--text-lg`
- Right: role badge + username link

### Page Body

- `padding: var(--space-7)` (1.75rem)
- `background: var(--color-bg)`
- Flash messages rendered at top via toast system

---

## Responsive Behaviour

### Breakpoints

```css
/* Mobile first — base styles target mobile */
@media (min-width: 768px)  { /* tablet  */ }
@media (min-width: 1200px) { /* desktop */ }
```

### Grid Patterns by Page

| Page | Mobile | Tablet | Desktop |
|---|---|---|---|
| Admin dashboard stat cards | 2-col | 4-col | 4-col |
| Admin dashboard alert tables | 1-col | 2-col | 2-col |
| Driver action cards | 2-col | 3-col | 4-col |
| Customer stat cards | 1-col | 3-col | 3-col |
| Form pages | 1-col | 2-col | 2-col |
| Auth pages | 1-col (form only) | split | split |

---

## Animation and Transition Specs

### Hover Lifts

```css
/* Stat cards */
.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
  transition: transform var(--transition-base), box-shadow var(--transition-base);
}

/* Driver action cards */
.driver-action-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-xl);
  transition: transform var(--transition-base), box-shadow var(--transition-base);
}
```

### Sidebar Slide

```css
.sidebar {
  transition: transform var(--transition-slow), width var(--transition-slow);
}
```

### Page Fade-In

```css
.page-body {
  animation: fadeInUp 0.3s ease both;
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
```

### Shimmer Loading State

```css
.shimmer {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

### Toast Slide-In

```css
@keyframes toastSlideIn {
  from { transform: translateX(110%); opacity: 0; }
  to   { transform: translateX(0);    opacity: 1; }
}
```

### Auth Background Pattern

Animated floating circles on `.auth-left` using CSS `::before` / `::after` pseudo-elements with `@keyframes float` (vertical oscillation, 6s infinite alternate ease-in-out).

---

## CSS Architecture Plan for main.css

`main.css` is organised into clearly commented sections:

```
/* ============================================================
   1. DESIGN TOKENS
   ============================================================ */
/* Brand colours, semantic colours, surface colours, text colours */
/* Typography tokens, spacing scale, radius scale, shadow scale */
/* Transition tokens, sidebar tokens */

/* ============================================================
   2. RESET / BASE
   ============================================================ */
/* box-sizing, body font/bg/color, html lang, scrollbar styling */
/* link colours, code element styling */

/* ============================================================
   3. LAYOUT
   ============================================================ */
/* .sidebar, .main-content, .topbar, .page-body */
/* .sidebar-overlay */

/* ============================================================
   4. SIDEBAR
   ============================================================ */
/* .sidebar-brand, .brand-icon, .brand-name, .brand-sub */
/* .sidebar-nav, .nav-section-title */
/* .sidebar-nav a, .sidebar-nav a:hover, .sidebar-nav a.active */
/* .sidebar-footer, .avatar, .uname, .urole */

/* ============================================================
   5. TOPBAR
   ============================================================ */
/* .topbar, .topbar-title, .topbar-right */
/* #sidebar-toggle (hamburger) */

/* ============================================================
   6. COMPONENTS
   ============================================================ */
/* 6a. Stat Card */
/* 6b. Data Table (.card-table, .card-table-header, table styles) */
/* 6c. Form Card (.form-card, .form-label, input/select/textarea) */
/* 6d. Badge Status (.badge-status, .bs-* variants) */
/* 6e. Alert Banner (.alert variants) */
/* 6f. Empty State (.empty-state) */
/* 6g. Driver Action Card (.driver-action-card) */
/* 6h. Button variants (.btn-primary, .btn-accent, .btn-action) */
/* 6i. Toast Notifications (.toast-container, .toast-item) */

/* ============================================================
   7. AUTH PAGES
   ============================================================ */
/* .auth-layout, .auth-left, .auth-right */
/* .auth-brand, .auth-tagline, .feature-list */
/* .btn-auth-submit */

/* ============================================================
   8. PAGE-SPECIFIC
   ============================================================ */
/* 8a. Admin Dashboard — gradient stat card variants */
/* 8b. Driver Dashboard — emergency card accent borders */
/* 8c. Customer Dashboard — shipment timeline */
/* 8d. Location page — last-known location card */

/* ============================================================
   9. ANIMATIONS
   ============================================================ */
/* @keyframes fadeInUp, shimmer, toastSlideIn, float */

/* ============================================================
   10. RESPONSIVE
   ============================================================ */
/* @media (min-width: 768px) — tablet overrides */
/* @media (min-width: 1200px) — desktop overrides */
/* @media (max-width: 767px) — mobile-only rules */
```

---

## Template-by-Template Design Notes

### base.html

**Changes from current:**
- Remove entire `<style>` block; add `<link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">`
- Add `id="sidebar-toggle"` hamburger button in topbar (hidden on desktop via CSS)
- Add `<div class="sidebar-overlay" id="sidebar-overlay"></div>` before `.main-content`
- Replace flash message `<div class="alert ...">` blocks with `<div id="flash-data" data-messages="{{ get_flashed_messages(with_categories=true)|tojson|e }}"></div>` and a `<div class="toast-container" id="toast-container"></div>`
- Add vanilla JS at bottom: sidebar toggle, overlay click-to-close, toast renderer
- Add `lang="en"` to `<html>` tag

**Sidebar enhancements:**
- Add `aria-label="Main navigation"` to `<nav>`
- Wrap section titles in `<span class="nav-section-title">`
- Active link detection unchanged (Jinja logic preserved)

### login.html

**Changes from current:**
- Replace inline `<style>` block with `<link>` to `main.css`
- Wrap in `<div class="auth-layout">`
- `.auth-left`: add animated CSS background (two pseudo-element circles with `@keyframes float`)
- `.auth-right`: add `<div class="auth-right">` wrapper, keep existing form structure
- Add `lang="en"` to `<html>`
- Input group styling handled by `main.css` `.auth-layout .input-group` rules

### register.html

**Changes from current:**
- Currently a plain centered card — upgrade to full split-panel `.auth-layout`
- Left panel: same FleetGuard branding as login
- Right panel: registration form with icon-prefixed inputs (user icon for name/username, envelope for email, lock for password)
- Add `lang="en"` to `<html>`
- Link to `main.css`

### forgot_password.html

**Changes from current:**
- Currently bare Bootstrap with no branding — upgrade to `.auth-layout`
- Left panel: branding + "Secure account recovery" messaging
- Right panel: email + username + new password fields with icon prefixes
- Add `lang="en"` to `<html>`
- Link to `main.css`

### admin_dashboard.html

**Changes from current:**
- Stat cards: add `.stat-card--gradient` class to first row (trucks) for gradient backgrounds
- Row 1 (4 truck cards): gradient variants — blue, green, purple, amber
- Row 2 (6 alert cards): standard white cards with coloured icons
- Alert tables: existing `.card-table` structure preserved, CSS handles styling
- No structural changes needed beyond removing inline styles

**Gradient card colour assignments:**
- Total Trucks: `linear-gradient(135deg, #1e40af, #2196f3)` — white text
- Available: `linear-gradient(135deg, #065f46, #10b981)` — white text
- On Route: `linear-gradient(135deg, #5b21b6, #8b5cf6)` — white text
- Maintenance: `linear-gradient(135deg, #92400e, #f59e0b)` — white text

### driver_dashboard.html

**Changes from current:**
- Driver info stat cards: keep standard white style
- Quick action cards: upgrade `.driver-action-card` with larger icons (2.5rem), bolder labels
- Accident card: add `border-top: 4px solid var(--color-danger)` via `.driver-action-card--danger`
- Fuel + Breakdown cards: add `border-top: 4px solid var(--color-warning)` via `.driver-action-card--warning`
- Call Admin card: add `border-top: 4px solid var(--color-purple)` via `.driver-action-card--purple`
- Recent shipments table: standard `.card-table`
- Fuel requests sidebar: standard `.card-table`

### customer_dashboard.html

**Changes from current:**
- Stat cards: standard white with coloured icons (blue, amber, green)
- Shipment table: add a visual progress indicator column showing shipment stage
- Progress tracker: inline CSS-drawn step indicator (Pending -> In Transit -> Delivered) using flex + coloured dots
- Payment amount displayed more prominently below payment badge

### trucks.html

**Changes from current:**
- Table: standard `.card-table` with sticky header
- Truck number: replace `badge bg-dark` with `.truck-badge` (dark navy pill)
- Status modal: styled with `main.css` modal overrides (border-radius, shadow)
- Action buttons: `.btn-action` pill style

### truck_form.html

**Changes from current:**
- Wrap in `.form-card`
- All inputs styled via `main.css` form rules
- Submit button: `.btn-primary` with hover darkening

### drivers.html

**Changes from current:**
- Table: standard `.card-table`
- Driver name: bold via CSS (no inline `<strong>` needed)
- License number: `<code>` styled with `main.css` code rules
- Assigned truck: `.truck-badge` pill
- Action buttons: `.btn-action` edit (blue outline) + delete (red outline)

### driver_form.html

- `.form-card` wrapper
- All inputs via `main.css` form rules

### shipments.html

**Changes from current:**
- Table: standard `.card-table` with sticky header
- Inline status/payment/customer dropdowns: `.form-select-sm` styled
- Shipment ID `<code>`: styled with `main.css`
- All badge-status classes already present — CSS handles colours

### shipment_form.html / customer_shipment_form.html

- `.form-card` wrapper
- Standard form styling

### users.html

- Standard `.card-table`
- Role badges: use `.badge-status` with role-specific colour (admin=blue, driver=purple, customer=green)

### profile.html

- `.form-card` wrapper, centred with `col-md-8`
- Disabled fields styled with reduced opacity via `main.css`

### admin_locations.html

- `.card-table` for location list
- Last-updated timestamp styled with `--color-text-muted`
- Location string: `font-size: --text-sm`

### admin_fuel_requests.html

- `.card-table` with sticky header
- Pay button: `.btn-accent` (gold background, navy text)
- Approve/Reject: `.btn-action.btn-action--success` / `.btn-action.btn-action--danger`
- Razorpay JS unchanged

### fuel_request.html

- Left: `.form-card` with amber top-border accent (`border-top: 4px solid var(--color-warning)`)
- Right: `.card-table` history
- Submit button: `background: var(--color-warning); color: var(--color-primary)`

### admin_accidents.html / admin_breakdowns.html / admin_call_requests.html

- Standard `.card-table` with sticky header
- Resolve button: `.btn-action.btn-action--success`
- Status badges: existing `.bs-*` classes

### accident_report.html

- Left: `.form-card` with red top-border (`border-top: 4px solid var(--color-danger)`)
- Emergency alert banner: `.alert-danger` with triangle-exclamation icon
- Submit button: `background: var(--color-danger)`

### breakdown_report.html

- Left: `.form-card` with amber top-border
- Submit button: `background: var(--color-warning); color: var(--color-primary)`

### call_request.html

- Left: `.form-card` with purple top-border (`border-top: 4px solid var(--color-purple)`)
- Submit button: `background: var(--color-purple)`

### location_update.html

- Left: `.form-card` standard
- Right: `.form-card` with last-known location display
- Location string: large `font-size: 1.25rem` with pin emoji or FA icon
- Timestamp: `--color-text-muted`

---

## Error Handling

### Flash Message to Toast Migration

Current: Flask `flash()` messages render as Bootstrap `.alert` divs inside `.page-body`.

New approach:
1. `base.html` injects flash data into a hidden element: `<div id="flash-data" data-messages='{{ messages|tojson }}'></div>`
2. Vanilla JS reads this on `DOMContentLoaded`, creates `.toast-item` elements, appends to `.toast-container`
3. Each toast auto-dismisses after 4000ms with a CSS fade-out transition
4. Fallback: if JS is disabled, the hidden `#flash-data` element is replaced with standard `.alert` divs (progressive enhancement)

### Form Validation States

- Invalid fields: Bootstrap's `.is-invalid` class triggers red border via `main.css` override
- Valid fields: `.is-valid` triggers green border
- Focus ring: `box-shadow: 0 0 0 3px rgba(33,150,243,0.25)` on all focusable inputs

### Empty States

Every `.card-table` that may have zero rows renders `.empty-state` with:
- Centred FA icon (3rem, `--color-text-muted`)
- Descriptive message
- Optional CTA button (admin pages only)

---

## Testing Strategy

### Dual Testing Approach

Both unit tests and property-based tests are required. Unit tests verify specific examples and edge cases; property tests verify universal correctness across all inputs.

### Unit Tests (specific examples and integration points)

- Verify `main.css` exists and contains all required CSS custom property declarations (tokens 1.1–1.4)
- Verify `base.html` loads `main.css` via `url_for` and contains no inline `<style>` block
- Verify each auth page (`login.html`, `register.html`, `forgot_password.html`) contains `.auth-layout` and `.auth-left`/`.auth-right` structure
- Verify `admin_dashboard.html` contains at least 10 `.stat-card` elements
- Verify `driver_dashboard.html` contains at least 5 `.driver-action-card` elements
- Verify `customer_dashboard.html` contains 3 `.stat-card` elements
- Verify sidebar hamburger button `#sidebar-toggle` is present in `base.html`
- Verify `.sidebar-overlay` element is present in `base.html`
- Verify `<html lang="en">` on every standalone page
- Verify Razorpay JS is still present and unchanged in `admin_fuel_requests.html`

### Property-Based Tests (universal properties across all inputs)

Property-based testing library: **Hypothesis** (Python) for server-side rendering tests, **fast-check** (JS) for client-side CSS/DOM property tests.

Each property test runs a minimum of 100 iterations.

**Property 1: Design Token Propagation**
Tag: `Feature: transport-management-ui, Property 1: design token propagation`
For any CSS rule in `main.css` that sets a colour, border-radius, shadow, or transition value, that value should be expressed as a `var(--token)` reference rather than a hardcoded literal.
Implementation: Parse `main.css` with a CSS parser; for each declaration whose property is in `{color, background, background-color, border-color, border-radius, box-shadow, transition}`, assert the value string contains `var(--` rather than a raw hex/px/ms literal.

**Property 2: Stat Card Structure Completeness**
Tag: `Feature: transport-management-ui, Property 2: stat card structure completeness`
For any rendered stat card element in the DOM, it should contain exactly one `.stat-icon` child, one `.stat-value` child, and one `.stat-label` child, and the `.stat-value` element's computed `font-family` should resolve to Rajdhani.
Implementation: Use Hypothesis to generate random stat card data dicts, render the template fragment, parse with BeautifulSoup, assert child structure.

**Property 3: Badge Status Colour Mapping**
Tag: `Feature: transport-management-ui, Property 3: badge status colour mapping`
For any `.badge-status` element with a known status text value, the element's CSS class should be one of the defined `.bs-*` variants, and that variant's background-color and color should match the semantic colour pair.
Implementation: Generate random status strings from the known set; render a badge fragment; assert the correct `.bs-*` class is applied and the CSS variables resolve to the expected hex values.

**Property 4: Driver Action Card Semantic Colour Mapping**
Tag: `Feature: transport-management-ui, Property 4: driver action card semantic colour mapping`
For any driver action card type, the icon's CSS colour class should match the semantic assignment (blue for location, amber for fuel/breakdown, red for accident, purple for call admin, green for shipments).
Implementation: Parse `driver_dashboard.html` template; for each `.driver-action-card`, extract the icon colour style and assert it matches the expected semantic token.

**Property 5: Mobile Overlay Lifecycle**
Tag: `Feature: transport-management-ui, Property 5: mobile overlay lifecycle`
For any sidebar toggle event sequence, when the sidebar is opened the overlay should be visible, and when closed the overlay should not be visible — no orphaned overlays.
Implementation: Use fast-check to generate random sequences of open/close toggle events; simulate in jsdom; assert overlay visibility matches sidebar open state after each event.

**Property 6: Typography Token Consistency**
Tag: `Feature: transport-management-ui, Property 6: typography token consistency`
For any element with a display-class (`.topbar-title`, `.stat-value`, `.section-title`, `.brand-name`), the computed font-family should resolve to Rajdhani; for body-class elements (`.sidebar-nav a`, `table tbody td`, `.form-label`), it should resolve to Inter.
Implementation: Parse `main.css`; for each selector in the display/body sets, assert the `font-family` declaration references `var(--font-display)` or `var(--font-body)` respectively.

**Property 7: Body Text Contrast Ratio**
Tag: `Feature: transport-management-ui, Property 7: body text contrast ratio`
For any body text colour token (`--color-text-primary`, `--color-text-secondary`, `--color-text-muted`) rendered on white (`#ffffff`), the WCAG 2.1 relative luminance contrast ratio should be >= 4.5:1.
Implementation: Extract hex values of the three text tokens from `main.css`; compute relative luminance for each; assert contrast ratio against white >= 4.5. (Deterministic — no randomisation needed, but framed as a property over the token set.)
