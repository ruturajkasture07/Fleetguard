# Implementation Plan: FleetGuard Transport Management UI Overhaul

## Overview

Deliver a production-quality UI overhaul across all 20+ Jinja2 templates by building a single `static/css/main.css` design system, upgrading `base.html` with a premium sidebar/topbar/toast scaffold, converting all three auth pages to split-panel layouts, and updating every dashboard, list, and form page to use the new component classes. No backend Python logic is changed.

## Tasks

- [ ] 1. Create `static/css/main.css` — Design Token System and Base Styles
  - [ ] 1.1 Write Section 1 (Design Tokens): all CSS custom properties
    - Brand colours: `--color-primary`, `--color-accent`, `--color-accent-2`
    - Semantic colour tokens with `-bg` and `-text` variants: success, warning, danger, info, purple
    - Surface and text colour tokens: `--color-bg`, `--color-surface`, `--color-border`, `--color-text-primary/secondary/muted/inverse`
    - Sidebar-specific tokens: `--sidebar-bg`, `--sidebar-w` (250px), `--sidebar-w-collapsed` (64px), link/hover/active tokens
    - Typography tokens: `--font-display` (Rajdhani), `--font-body` (Inter), font-size scale (`--text-xs` through `--text-2xl`)
    - Spacing scale `--space-1` through `--space-12`, border-radius scale `--radius-sm` through `--radius-full`
    - Shadow scale `--shadow-sm` through `--shadow-2xl`, transition tokens `--transition-fast/base/slow`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ] 1.2 Write Section 2 (Reset/Base): box-sizing, body, html, scrollbar, links, code
    - Set `lang="en"` awareness note; apply `--font-body` to body, `--color-bg` as background, `--color-text-primary` as default colour
    - _Requirements: 13.1, 13.2, 13.4, 14.1, 14.4_

  - [ ]* 1.3 Write property test for design token propagation
    - **Property 1: Design Token Propagation**
    - **Validates: Requirements 1.1, 1.5, 15.1**
    - Parse `main.css` with a CSS parser; for each declaration whose property is in `{color, background, background-color, border-color, border-radius, box-shadow, transition}`, assert the value string contains `var(--` rather than a raw hex/px/ms literal
    - Use Python `tinycss2` or `cssutils`; run with `pytest`

- [ ] 2. Write Sections 3–5 of `main.css` — Layout, Sidebar, Topbar
  - [ ] 2.1 Write Section 3 (Layout): `.sidebar`, `.main-content`, `.page-body`, `.sidebar-overlay`
    - `.sidebar`: `position: fixed; left: 0; top: 0; height: 100vh; width: var(--sidebar-w); background: var(--sidebar-bg); z-index: 1000`
    - `.main-content`: `margin-left: var(--sidebar-w); min-height: 100vh`
    - `.page-body`: `padding: var(--space-7); background: var(--color-bg); animation: fadeInUp 0.3s ease both`
    - `.sidebar-overlay`: `position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 999; display: none`
    - _Requirements: 2.1, 2.6, 12.1, 12.3_

  - [ ] 2.2 Write Section 4 (Sidebar): brand, nav links, section titles, footer, avatar
    - `.sidebar-brand`, `.brand-icon`, `.brand-name` (Rajdhani), `.brand-sub`
    - `.sidebar-nav a`: flex, gap, padding, colour `var(--sidebar-link)`, `border-left: 3px solid transparent`, transition
    - `.sidebar-nav a:hover`, `.sidebar-nav a.active`: `border-left-color: var(--color-accent)`, `background: var(--sidebar-link-active-bg)`
    - `.nav-section-title`: uppercase, `color: var(--sidebar-section-title)`, small letter-spacing
    - `.sidebar-footer`, `.avatar` (circular, `--color-accent` bg), `.uname`, `.urole`
    - _Requirements: 3.1, 3.2, 3.3, 3.7_

  - [ ] 2.3 Write Section 5 (Topbar): sticky bar, title, role badge, hamburger button
    - `.topbar`: `position: sticky; top: 0; z-index: 100; background: var(--color-surface); border-bottom: 1px solid var(--color-border); box-shadow: var(--shadow-sm)`
    - `.topbar-title`: `font-family: var(--font-display); font-size: var(--text-lg)`
    - `#sidebar-toggle`: `display: none` (shown only at mobile via responsive section)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 2.4 Write property test for typography token consistency
    - **Property 6: Typography Token Consistency**
    - **Validates: Requirements 13.1, 13.2**
    - Parse `main.css`; for each selector in the display set (`.topbar-title`, `.stat-value`, `.section-title`, `.brand-name`), assert `font-family` declaration references `var(--font-display)`; for body set (`.sidebar-nav a`, `table tbody td`, `.form-label`), assert `var(--font-body)`

- [ ] 3. Write Section 6 of `main.css` — All Component Styles
  - [ ] 3.1 Write 6a Stat Card styles
    - `.stat-card`: white bg, `border-radius: var(--radius-md)`, `box-shadow: var(--shadow-md)`, flex, gap, padding
    - `.stat-card:hover`: `transform: translateY(-3px); box-shadow: var(--shadow-lg); transition: transform var(--transition-base), box-shadow var(--transition-base)`
    - `.stat-icon`: 52×52px, `border-radius: var(--radius-md)`
    - `.stat-value`: `font-family: var(--font-display); font-size: var(--text-2xl); font-weight: 700`
    - `.stat-label`: `font-size: var(--text-xs); text-transform: uppercase; letter-spacing: 0.5px; color: var(--color-text-muted)`
    - `.stat-card--gradient`: gradient background, white text (four colour variants for admin dashboard row 1)
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ]* 3.2 Write property test for stat card structure completeness
    - **Property 2: Stat Card Structure Completeness**
    - **Validates: Requirements 5.1, 5.4, 5.5, 5.6**
    - Use Hypothesis + BeautifulSoup: generate random stat card data dicts, render a minimal Jinja fragment, parse HTML, assert each `.stat-card` contains exactly one `.stat-icon`, one `.stat-value`, one `.stat-label`

  - [ ] 3.3 Write 6b Data Table styles
    - `.card-table`: white bg, `border-radius: var(--radius-md)`, `box-shadow: var(--shadow-md)`, `overflow: hidden`
    - `.card-table-header`: flex, space-between, padding, `border-bottom: 1px solid var(--color-border-light)`
    - `table thead th`: `background: #f8f9fa; font-size: var(--text-xs); text-transform: uppercase; letter-spacing: 0.5px; color: var(--color-text-muted); font-weight: 600`
    - `table thead`: `position: sticky; top: 0`
    - `table tbody tr:hover`: `background: #f0f4ff`
    - `.btn-action` pill variants: `border-radius: var(--radius-xl); font-size: var(--text-xs); padding: 0.28rem 0.65rem`
    - `.btn-action--success`, `.btn-action--danger`, `.btn-action--primary` colour variants
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.6_

  - [ ] 3.4 Write 6c Form Card styles
    - `.form-card`: white bg, `border-radius: var(--radius-md)`, `box-shadow: var(--shadow-md)`, `padding: var(--space-8)`
    - `.form-card h5`: `font-family: var(--font-display); font-weight: 700; color: var(--color-primary)`
    - `.form-label`: `font-size: var(--text-xs); font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; color: var(--color-text-secondary)`
    - `input, select, textarea`: `border-radius: var(--radius-sm); border: 1px solid var(--color-border); font-size: var(--text-sm)`
    - `:focus` ring: `border-color: var(--color-accent-2); box-shadow: 0 0 0 3px rgba(33,150,243,0.25)`
    - `.btn-primary`: `background: var(--color-primary); border-radius: var(--radius-sm)`; hover darkens 10%
    - `.btn-accent`: `background: var(--color-accent); color: var(--color-primary); font-weight: 600`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [ ] 3.5 Write 6d Badge Status styles
    - `.badge-status`: `border-radius: var(--radius-xl); padding: 0.3rem 0.7rem; font-size: var(--text-xs); font-weight: 600`
    - All `.bs-*` variants using semantic colour tokens: `.bs-available`, `.bs-on-route`, `.bs-maintenance`, `.bs-pending`, `.bs-transit`, `.bs-delivered`, `.bs-reported`, `.bs-resolved`, `.bs-open`, `.bs-approved`, `.bs-rejected`, `.bs-paid`, `.bs-unpaid`
    - _Requirements: 7.1, 7.2, 7.3_

  - [ ]* 3.6 Write property test for badge status colour mapping
    - **Property 3: Badge Status Colour Mapping**
    - **Validates: Requirements 7.1, 7.2, 7.3**
    - Generate random status strings from the known set; render a badge fragment; assert the correct `.bs-*` class is applied and the CSS variables resolve to the expected hex values

  - [ ] 3.7 Write 6e–6i remaining component styles
    - 6e `.alert` variants: `border-radius: var(--radius-md); border: none` + leading icon per category
    - 6f `.empty-state`: centred, icon 3rem `var(--color-text-muted)`, descriptive text
    - 6g `.driver-action-card`: `border-radius: var(--radius-lg); box-shadow: var(--shadow-md); text-align: center; padding: var(--space-6); transition: all var(--transition-base)`; hover `translateY(-4px)` + `var(--shadow-xl)`; `.driver-action-card--danger/warning/purple` top-border accent variants
    - 6h Button variants already covered in 3.4; add `.btn-outline-*` overrides
    - 6i `.toast-container`: `position: fixed; bottom: 1.5rem; right: 1.5rem; z-index: 9999; display: flex; flex-direction: column; gap: 0.5rem`; `.toast-item`: white card, shadow, `animation: toastSlideIn 0.3s ease`; category colour left-border
    - _Requirements: 9.1, 9.2, 9.3, 11.1, 11.2, 11.3_

  - [ ]* 3.8 Write property test for driver action card semantic colour mapping
    - **Property 4: Driver Action Card Semantic Colour Mapping**
    - **Validates: Requirements 11.3, 11.4**
    - Parse `driver_dashboard.html` template; for each `.driver-action-card`, extract the icon colour class/style and assert it matches the expected semantic token (blue=location, amber=fuel/breakdown, red=accident, purple=call, green=shipments)

- [ ] 4. Write Sections 7–10 of `main.css` — Auth, Page-Specific, Animations, Responsive
  - [ ] 4.1 Write Section 7 (Auth Pages): split-panel layout
    - `.auth-layout`: `display: flex; min-height: 100vh`
    - `.auth-left`: `flex: 1; background: var(--color-primary); display: flex; flex-direction: column; justify-content: center; padding: var(--space-10); position: relative; overflow: hidden`
    - `.auth-left::before` / `::after`: animated floating circles using `@keyframes float` (vertical oscillation, 6s infinite alternate ease-in-out)
    - `.auth-brand`, `.auth-tagline`, `.feature-list li` styles
    - `.auth-right`: `width: 420px; background: var(--color-surface); display: flex; flex-direction: column; justify-content: center; padding: var(--space-10) var(--space-8)`
    - `.auth-right h2`: `font-family: var(--font-display); font-size: var(--text-xl); font-weight: 700; color: var(--color-primary)`
    - `.input-group-text`: `background: #f8f9fa; border-color: var(--color-border)`
    - `.btn-auth-submit`: full-width, `background: var(--color-primary)`, hover lift + shadow
    - _Requirements: 10.1, 10.2, 10.3, 10.5, 10.6_

  - [ ] 4.2 Write Section 8 (Page-Specific): admin gradient cards, driver emergency borders, customer timeline, location card
    - 8a Admin gradient stat card colour assignments (4 variants: blue, green, purple, amber)
    - 8b Driver emergency card accent borders (`.driver-action-card--danger`, `--warning`, `--purple`)
    - 8c Customer shipment progress tracker: `.shipment-progress` flex step indicator with coloured dots
    - 8d Location page: `.location-display` large font, pin icon styling
    - _Requirements: 5.4, 11.3_

  - [ ] 4.3 Write Section 9 (Animations): all keyframes
    - `@keyframes fadeInUp`: `from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); }`
    - `@keyframes shimmer`: gradient sweep for `.shimmer` skeleton loader class
    - `@keyframes toastSlideIn`: `from { transform: translateX(110%); opacity: 0; } to { transform: translateX(0); opacity: 1; }`
    - `@keyframes float`: vertical oscillation for auth background circles
    - _Requirements: 2.5_

  - [ ] 4.4 Write Section 10 (Responsive): tablet and mobile breakpoints
    - `@media (min-width: 768px)`: tablet — sidebar collapses to 64px icon-only, nav link text hidden, section titles hidden; sidebar expands to 250px on `:hover`; auth layout shows split panel
    - `@media (min-width: 1200px)`: desktop — full sidebar always visible, driver action cards 4-col
    - `@media (max-width: 767px)`: mobile — sidebar `transform: translateX(-100%)`, `.sidebar.open` slides in, `#sidebar-toggle` visible, `.auth-left` hidden, `.auth-right` full-width, `margin-left: 0` on `.main-content`
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 2.6, 2.7, 10.4, 11.4, 12.1, 12.2_

  - [ ]* 4.5 Write property test for body text contrast ratio
    - **Property 7: Body Text Contrast Ratio**
    - **Validates: Requirements 14.1**
    - Extract hex values of `--color-text-primary`, `--color-text-secondary`, `--color-text-muted` from `main.css`; compute WCAG 2.1 relative luminance contrast ratio against white (`#ffffff`); assert each >= 4.5:1

- [ ] 5. Checkpoint — Verify `main.css` is complete before touching templates
  - Ensure all 10 sections are present in `main.css`, all CSS custom properties are defined, and no raw hex/px literals appear in component rules. Ask the user if questions arise.

- [ ] 6. Update `base.html` — Remove inline styles, add premium scaffold
  - [ ] 6.1 Replace `<style>` block with `<link>` to `main.css` and add Google Fonts + CDN links
    - Remove entire `<style>` block
    - Add `<link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">`
    - Ensure Google Fonts link includes Rajdhani (400,500,600,700) + Inter (300,400,500,600)
    - Add `lang="en"` to `<html>` tag
    - _Requirements: 15.1, 15.3, 14.4_

  - [ ] 6.2 Add hamburger toggle button to topbar and sidebar overlay div
    - Add `<button id="sidebar-toggle" aria-label="Toggle navigation">` with hamburger icon inside `.topbar`, before the page title
    - Add `<div class="sidebar-overlay" id="sidebar-overlay"></div>` immediately before `.main-content`
    - Add `aria-label="Main navigation"` to `<nav class="sidebar-nav">`
    - _Requirements: 2.2, 2.3, 12.1, 12.4_

  - [ ] 6.3 Replace flash message alert divs with toast data injection
    - Replace the `{% with messages %}` alert block with `<div id="flash-data" data-messages="{{ get_flashed_messages(with_categories=true)|tojson|e }}"></div>`
    - Add `<div class="toast-container" id="toast-container"></div>` at end of `<body>`
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [ ] 6.4 Add vanilla JS at bottom of `base.html`
    - Sidebar toggle: click `#sidebar-toggle` adds/removes `.open` class on `.sidebar`; also toggles `display` on `.sidebar-overlay`
    - Overlay click-to-close: click `#sidebar-overlay` removes `.open` from sidebar, hides overlay
    - Toast renderer: on `DOMContentLoaded`, read `#flash-data` `data-messages` JSON, create `.toast-item` elements with category colour class, append to `#toast-container`, auto-dismiss after 4000ms with CSS fade-out
    - _Requirements: 2.4, 12.2, 12.4, 9.3_

  - [ ]* 6.5 Write property test for mobile overlay lifecycle
    - **Property 5: Mobile Overlay Lifecycle**
    - **Validates: Requirements 2.4, 12.1, 12.2, 12.4**
    - Use fast-check (or Hypothesis + jsdom via subprocess) to generate random sequences of open/close toggle events; simulate against the JS in `base.html`; assert overlay visibility matches sidebar open state after each event with no orphaned overlays

- [ ] 7. Update Auth Pages — Split-panel layout for login, register, forgot_password
  - [ ] 7.1 Update `login.html` — migrate inline styles to `main.css` classes
    - Remove entire `<style>` block; add `<link>` to `main.css`
    - Wrap body content in `<div class="auth-layout">`
    - Move left panel content into `<div class="auth-left">` with `.auth-brand`, `.auth-tagline`, `.feature-list`
    - Move form into `<div class="auth-right">`; keep existing form fields and Jinja flash logic
    - Add `lang="en"` to `<html>`
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

  - [ ] 7.2 Update `register.html` — upgrade plain card to full split-panel auth layout
    - Remove inline `<style>` block; add `<link>` to `main.css`
    - Wrap in `<div class="auth-layout">`
    - Add `.auth-left` panel with FleetGuard branding (same structure as login)
    - Move registration form into `.auth-right`; add icon-prefixed input groups (user icon for name/username, envelope for email, lock for password)
    - Add `lang="en"` to `<html>`
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

  - [ ] 7.3 Update `forgot_password.html` — upgrade bare Bootstrap page to split-panel auth layout
    - Remove Bootstrap-only markup; add `<link>` to `main.css` and Font Awesome CDN
    - Wrap in `<div class="auth-layout">`
    - Add `.auth-left` panel with "Secure account recovery" messaging
    - Move form into `.auth-right`; add icon-prefixed inputs (envelope for email, user for username, lock for new password)
    - Add `lang="en"` to `<html>`
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

- [ ] 8. Update `admin_dashboard.html` — Gradient stat cards, charts, alert tables
  - [ ] 8.1 Upgrade truck stat cards (row 1) to gradient variants
    - Add `.stat-card--gradient` class to all four truck stat cards
    - Apply gradient colour assignments: Total Trucks = blue gradient, Available = green gradient, On Route = purple gradient, Maintenance = amber gradient
    - Ensure white text on gradient cards via CSS class (no inline styles)
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [ ] 8.2 Add Chart.js line chart for monthly trips and pie chart for truck status
    - Add `<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>` to `{% block scripts %}`
    - Add a new row below stat cards with two chart cards: `<canvas id="tripsChart">` (line) and `<canvas id="truckStatusChart">` (pie/doughnut)
    - Write inline JS in `{% block scripts %}` to initialise both charts using stats data passed from Flask (use `{{ stats|tojson }}` for truck status counts; trips chart uses placeholder monthly data)
    - Style chart containers as `.card-table` cards with `.card-table-header`
    - _Requirements: 5.4_

  - [ ] 8.3 Ensure all four alert tables use `.card-table` with `.card-table-header` and `.btn-action` buttons
    - Verify Pending Fuel Requests, Recent Accidents, Open Breakdowns, Call Requests tables all have `.card-table-header` with title + "View All" link
    - Replace any `btn btn-sm btn-outline-primary` "View All" links with `.btn-action.btn-action--primary`
    - Remove any remaining inline styles
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 15.1_

- [ ] 9. Update `driver_dashboard.html` — Welcome card, action cards, tables
  - [ ] 9.1 Upgrade driver info stat cards with proper token-based colours
    - Replace inline `style="background:#dbeafe;color:#1e40af;"` etc. with CSS utility classes or data attributes resolved by `main.css`
    - Ensure `.stat-icon` background/colour uses `var(--color-info-bg)` / `var(--color-info-text)` etc.
    - _Requirements: 5.5_

  - [ ] 9.2 Upgrade quick-action cards with semantic accent borders
    - Add `.driver-action-card--danger` to Accident Report card (red top border)
    - Add `.driver-action-card--warning` to Fuel Request and Breakdown Report cards (amber top border)
    - Add `.driver-action-card--purple` to Call Admin card (purple top border)
    - Remove all inline `style` attributes from `.driver-action-card` elements and `.dac-icon` spans; use CSS classes
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [ ]* 9.3 Write unit tests for driver dashboard structure
    - Verify `driver_dashboard.html` contains at least 5 `.driver-action-card` elements
    - Verify `.driver-action-card--danger` is present on the accident card
    - Verify `.driver-action-card--warning` is present on fuel and breakdown cards
    - _Requirements: 11.1, 11.3_

- [ ] 10. Update `customer_dashboard.html` — Stat cards and shipment progress tracker
  - [ ] 10.1 Remove inline styles from stat cards; use token-based colour classes
    - Replace `style="background:#dbeafe;color:#1e40af;"` etc. with CSS classes
    - _Requirements: 5.6_

  - [ ] 10.2 Add shipment progress tracker column to the shipment table
    - Add a "Progress" column to the `<thead>` and each `<tbody>` row
    - Render a `.shipment-progress` flex step indicator: three dots (Pending → In Transit → Delivered) with the current step highlighted using the appropriate semantic colour token
    - _Requirements: 5.6_

- [ ] 11. Checkpoint — Verify dashboards render correctly before updating list pages
  - Ensure all three dashboards extend `base.html`, contain no inline `<style>` blocks, and all stat cards use CSS classes. Ask the user if questions arise.

- [ ] 12. Update list/table pages — trucks, drivers, shipments, users, admin_locations
  - [ ] 12.1 Update `trucks.html`
    - Replace `<span class="badge bg-dark">` truck number badges with `.truck-badge` class (dark navy pill via `main.css`)
    - Replace `btn btn-sm btn-outline-primary/danger` action buttons with `.btn-action.btn-action--primary` / `.btn-action.btn-action--danger`
    - Ensure status modal uses `border-radius: var(--radius-md)` via `main.css` modal override (add `.modal-content` rule to Section 8 of `main.css`)
    - Remove any remaining inline styles
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.6, 15.1_

  - [ ] 12.2 Update `drivers.html`
    - Replace `<strong>` inline bold with CSS-driven bold via `main.css` `table tbody td:first-child` or a `.driver-name` class
    - Replace `badge bg-primary` assigned truck badge with `.truck-badge`
    - Replace action buttons with `.btn-action` variants
    - Remove inline styles
    - _Requirements: 6.1, 6.2, 6.6, 15.1_

  - [ ] 12.3 Update `shipments.html`
    - Ensure `.card-table-header` wraps the section title and action button
    - Replace inline `style="width:120px;"` on status/payment dropdowns with a CSS class `.select-sm-inline` in `main.css`
    - Remove inline styles
    - _Requirements: 6.1, 6.2, 6.3, 15.1_

  - [ ] 12.4 Update `users.html`
    - Replace `<span class="badge bg-secondary">` role badges with `.badge-status` + role-specific class: admin=`.bs-transit` (blue), driver=`.bs-purple` (add this variant), customer=`.bs-available` (green)
    - Add `.bs-purple` variant to `main.css` Section 6d
    - Replace delete button with `.btn-action.btn-action--danger`
    - _Requirements: 6.1, 6.6, 7.1, 7.2_

  - [ ] 12.5 Update `admin_locations.html`
    - Replace `<strong>` with CSS class; replace `badge bg-dark` with `.truck-badge`
    - Ensure timestamp uses `color: var(--color-text-muted)` via existing `.text-muted` override in `main.css`
    - _Requirements: 6.1, 6.3, 15.1_

- [ ] 13. Update alert list pages — admin_fuel_requests, admin_accidents, admin_breakdowns, admin_call_requests
  - [ ] 13.1 Update `admin_fuel_requests.html`
    - Replace `btn btn-sm btn-success/btn-danger` Approve/Reject buttons with `.btn-action.btn-action--success` / `.btn-action.btn-action--danger`
    - Replace `btn btn-sm btn-accent` Pay button with `.btn-accent` (already defined in `main.css`)
    - Ensure `.card-table-header` is present with section title
    - Razorpay JS block must remain completely unchanged
    - _Requirements: 6.1, 6.2, 6.6, 15.1_

  - [ ] 13.2 Update `admin_accidents.html`
    - Add `.card-table-header` with title "All Accident Reports" and optional "Export" placeholder
    - Replace `btn btn-sm btn-success` Resolve button with `.btn-action.btn-action--success`
    - Replace `<strong>` driver name with CSS class; replace `badge bg-dark` with `.truck-badge`
    - _Requirements: 6.1, 6.2, 6.6, 15.1_

  - [ ] 13.3 Update `admin_breakdowns.html`
    - Same pattern as `admin_accidents.html`: add `.card-table-header`, replace action buttons with `.btn-action`, replace badges
    - _Requirements: 6.1, 6.2, 6.6, 15.1_

  - [ ] 13.4 Update `admin_call_requests.html`
    - Add `.card-table-header` with title and count
    - Replace `btn btn-sm btn-success` Mark Done button with `.btn-action.btn-action--success`
    - Replace `badge bg-dark` with `.truck-badge`
    - _Requirements: 6.1, 6.2, 6.6, 15.1_

- [ ] 14. Update form pages — truck_form, driver_form, shipment_form, customer_shipment_form
  - [ ] 14.1 Update `truck_form.html`
    - Verify `.form-card` wrapper is present (already exists); remove any inline styles
    - Ensure submit button uses `.btn-primary` class (already present); cancel link uses `.btn-outline-secondary`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 15.1_

  - [ ] 14.2 Update `driver_form.html`
    - Verify `.form-card` wrapper is present; remove any inline styles
    - Ensure all inputs/selects use standard `form-control`/`form-select` classes styled by `main.css`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 15.1_

  - [ ] 14.3 Update `shipment_form.html`
    - Verify `.form-card` wrapper is present; remove any inline styles
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 15.1_

  - [ ] 14.4 Update `customer_shipment_form.html`
    - Verify `.form-card` wrapper is present; remove any inline styles
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 15.1_

- [ ] 15. Update driver report form pages — fuel_request, accident_report, breakdown_report, call_request, location_update
  - [ ] 15.1 Update `fuel_request.html`
    - Remove `style="border-top: 4px solid #f59e0b;"` inline style from `.form-card`; replace with CSS class `.form-card--warning` (add to `main.css` Section 8b)
    - Replace `btn btn-warning w-100 fw-bold` submit button with `.btn-submit-warning` class in `main.css` (`background: var(--color-warning); color: var(--color-primary)`)
    - _Requirements: 8.1, 8.5, 15.1_

  - [ ] 15.2 Update `accident_report.html`
    - Remove `style="border-top: 4px solid #ef4444;"` inline style; replace with `.form-card--danger` CSS class
    - Replace `btn btn-danger w-100 fw-bold` with `.btn-submit-danger` class (`background: var(--color-danger)`)
    - _Requirements: 8.1, 8.5, 15.1_

  - [ ] 15.3 Update `breakdown_report.html`
    - Remove `style="border-top: 4px solid #f59e0b;"` inline style; replace with `.form-card--warning`
    - Replace `btn btn-warning w-100 fw-bold text-dark` with `.btn-submit-warning`
    - _Requirements: 8.1, 8.5, 15.1_

  - [ ] 15.4 Update `call_request.html`
    - Remove `style="border-top: 4px solid #8b5cf6;"` inline style; replace with `.form-card--purple` CSS class (add to `main.css`)
    - Remove `style="background:#8b5cf6;color:#fff;"` from submit button; replace with `.btn-submit-purple` class
    - Remove `style="color:#8b5cf6;"` from icon; replace with `.text-purple` utility class in `main.css`
    - _Requirements: 8.1, 8.5, 15.1_

  - [ ] 15.5 Update `location_update.html`
    - Remove inline `class="fs-5"` and `class="fs-6"` Bootstrap utilities; replace with `main.css` classes `.location-display` and `.truck-badge`
    - Ensure last-known location card uses `.form-card` with no inline styles
    - _Requirements: 8.1, 15.1_

- [ ] 16. Update `profile.html` and remaining pages
  - [ ] 16.1 Update `profile.html`
    - Verify `.form-card` wrapper is present; remove any inline styles
    - Disabled fields: add `.form-control:disabled` rule to `main.css` Section 6c (`opacity: 0.65; background: #f8f9fa`)
    - _Requirements: 8.1, 8.3, 15.1_

- [ ] 17. Checkpoint — Full template audit: no inline styles remain
  - Grep all templates for `style="` attributes; fix any remaining occurrences. Ensure every template that extends `base.html` has no `<style>` block. Ask the user if questions arise.

- [ ] 18. Add `main.css` form-card accent variants and utility classes (from tasks 15–16)
  - Add `.form-card--warning`, `.form-card--danger`, `.form-card--purple` to `main.css` Section 8b
  - Add `.btn-submit-warning`, `.btn-submit-danger`, `.btn-submit-purple` to `main.css` Section 6h
  - Add `.text-purple` utility, `.truck-badge` pill, `.location-display` large text class, `.bs-purple` badge variant, `.select-sm-inline` dropdown width class
  - Add `.form-control:disabled` reduced-opacity rule
  - _Requirements: 7.2, 8.5, 15.1, 15.2_

- [ ]* 19. Write unit tests for template structure correctness
  - Verify `base.html` loads `main.css` via `url_for` and contains no inline `<style>` block
  - Verify each auth page contains `.auth-layout`, `.auth-left`, `.auth-right`
  - Verify `admin_dashboard.html` contains at least 10 `.stat-card` elements
  - Verify `driver_dashboard.html` contains at least 5 `.driver-action-card` elements
  - Verify `customer_dashboard.html` contains 3 `.stat-card` elements
  - Verify `#sidebar-toggle` and `.sidebar-overlay` are present in `base.html`
  - Verify `<html lang="en">` on every standalone page (login, register, forgot_password)
  - Verify Razorpay `checkout.js` script tag is still present and unchanged in `admin_fuel_requests.html`
  - Use `pytest` + `BeautifulSoup4`; parse raw HTML files without Flask context
  - _Requirements: 2.2, 2.3, 5.4, 5.5, 5.6, 10.1, 14.4, 15.1, 15.3_

- [ ] 20. Final checkpoint — End-to-end verification
  - Ensure all tests pass (run `pytest tests/` if test files exist)
  - Verify `static/css/main.css` exists and is non-empty
  - Verify no template file contains an inline `<style>` block
  - Ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Checkpoints at tasks 5, 11, 17, and 20 ensure incremental validation
- Property tests (Properties 1–7) validate universal correctness properties from the design document
- Unit tests (task 19) validate specific structural examples
- The Razorpay JS in `admin_fuel_requests.html` must never be modified
- No Python/Flask backend code is changed at any point
