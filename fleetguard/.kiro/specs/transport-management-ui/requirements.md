# Requirements Document

## Introduction

FleetGuard is an existing Flask-based Transport Management System with SQLite storage and three user roles: Admin, Driver, and Customer. The system currently uses Bootstrap 5 with inline styles scattered across templates and an empty CSS directory. This feature delivers a best-in-class, production-quality UI overhaul: a unified design system, polished visual language, full responsiveness across all device sizes, and role-specific UX optimisations — without altering any backend logic or routes.

## Glossary

- **UI_System**: The complete set of CSS custom properties, component classes, and layout primitives that govern the visual appearance of FleetGuard.
- **Design_Token**: A named CSS custom property (e.g. `--color-primary`) that encodes a single design decision and is referenced throughout the stylesheet.
- **Base_Template**: The Jinja2 template `base.html` that provides the shared sidebar, topbar, and page-body scaffold inherited by all authenticated pages.
- **Auth_Pages**: The standalone pages that do not extend `base.html`: login, register, and forgot-password.
- **Admin_Dashboard**: The page rendered for users with the `admin` role at `/dashboard`.
- **Driver_Dashboard**: The page rendered for users with the `driver` role at `/dashboard`.
- **Customer_Dashboard**: The page rendered for users with the `customer` role at `/dashboard`.
- **Sidebar**: The fixed left-hand navigation panel defined in `base.html`.
- **Topbar**: The sticky horizontal bar at the top of the main content area defined in `base.html`.
- **Stat_Card**: A summary metric widget displaying an icon, numeric value, and label.
- **Data_Table**: A styled HTML table used to list fleet entities (trucks, drivers, shipments, requests).
- **Form_Card**: A white card container wrapping form inputs used for create/edit operations.
- **Badge_Status**: A pill-shaped inline label conveying the status of an entity (e.g. Pending, In Transit, Delivered).
- **Alert_Banner**: A dismissible notification strip rendered from Flask `flash()` messages.
- **Empty_State**: A centred placeholder shown when a Data_Table has no rows.
- **Mobile_Breakpoint**: Viewport widths below 768 px.
- **Tablet_Breakpoint**: Viewport widths between 768 px and 1199 px.
- **Desktop_Breakpoint**: Viewport widths of 1200 px and above.
- **Razorpay_Widget**: The third-party payment checkout embedded in the fuel-requests admin page.

---

## Requirements

### Requirement 1: Unified Design Token System

**User Story:** As a developer, I want all visual values defined as CSS custom properties, so that the entire UI can be restyled by changing a single source of truth.

#### Acceptance Criteria

1. THE UI_System SHALL define Design_Tokens for colour palette, typography scale, spacing scale, border-radius scale, shadow scale, and transition durations in a single CSS file (`static/css/main.css`).
2. THE UI_System SHALL expose a `--color-primary` token set to `#0a2342`, a `--color-accent` token set to `#e8b04b`, and a `--color-accent-2` token set to `#2196f3` as the three brand colours.
3. THE UI_System SHALL define at least four semantic colour tokens: `--color-success`, `--color-warning`, `--color-danger`, and `--color-info`, each with a corresponding `-bg` and `-text` variant for use in Badge_Status components.
4. THE UI_System SHALL define a `--font-display` token referencing the Rajdhani typeface and a `--font-body` token referencing the Inter typeface.
5. WHEN a Design_Token value is changed in `main.css`, THE UI_System SHALL propagate that change to every component that references the token without requiring edits to individual template files.

---

### Requirement 2: Responsive Layout Foundation

**User Story:** As a user on any device, I want the application layout to adapt gracefully to my screen size, so that I can use FleetGuard comfortably on a phone, tablet, or desktop.

#### Acceptance Criteria

1. THE Base_Template SHALL render a full-height fixed Sidebar on Desktop_Breakpoint and Tablet_Breakpoint viewports.
2. WHEN the viewport is at Mobile_Breakpoint, THE Sidebar SHALL be hidden off-screen by default and SHALL slide into view when a hamburger toggle button is activated.
3. THE Base_Template SHALL render a hamburger toggle button in the Topbar that is visible only at Mobile_Breakpoint.
4. WHEN the Sidebar is open on Mobile_Breakpoint and the user taps outside the Sidebar area, THE Sidebar SHALL close.
5. THE Base_Template SHALL apply a CSS transition of 0.3 s or less to Sidebar open/close animations.
6. THE Base_Template SHALL render the main content area with `margin-left` equal to the Sidebar width on Desktop_Breakpoint and zero `margin-left` on Mobile_Breakpoint.
7. WHILE the viewport is at Tablet_Breakpoint, THE Sidebar SHALL collapse to show only icons (width ≤ 64 px) and SHALL expand to full width on hover.

---

### Requirement 3: Sidebar Navigation Polish

**User Story:** As a logged-in user, I want the sidebar to clearly communicate my current location and role, so that I can navigate the system confidently.

#### Acceptance Criteria

1. THE Sidebar SHALL highlight the active navigation link with a left-border accent in `--color-accent` and a background tint distinct from the inactive state.
2. THE Sidebar SHALL group navigation links under labelled sections (e.g. "Fleet", "Alerts", "My Work", "Emergency") with section titles styled in uppercase, reduced opacity, and small letter-spacing.
3. THE Sidebar SHALL display the authenticated user's avatar initial, full name, and role label in the footer area.
4. WHEN the user's role is `admin`, THE Sidebar SHALL render the Fleet and Alerts navigation sections.
5. WHEN the user's role is `driver`, THE Sidebar SHALL render the My Work and Emergency navigation sections.
6. WHEN the user's role is `customer`, THE Sidebar SHALL render the Customer navigation section.
7. THE Sidebar SHALL render a logout button in the footer that is visually distinct from navigation links.

---

### Requirement 4: Topbar and Page Header

**User Story:** As a user, I want a consistent page header that shows me where I am and who I am, so that I always have context while navigating.

#### Acceptance Criteria

1. THE Topbar SHALL display the current page title using the `--font-display` typeface at a minimum font size of 1.25 rem.
2. THE Topbar SHALL display the authenticated user's role as a colour-coded badge on the right side.
3. THE Topbar SHALL remain sticky at the top of the viewport while the user scrolls the page body.
4. THE Topbar SHALL cast a subtle box-shadow to visually separate it from the page body.
5. WHEN the viewport is at Mobile_Breakpoint, THE Topbar SHALL display the hamburger toggle button on the left side of the page title.

---

### Requirement 5: Stat Card Components

**User Story:** As an Admin or Driver or Customer, I want dashboard metric cards to be visually prominent and scannable, so that I can assess fleet status at a glance.

#### Acceptance Criteria

1. THE Stat_Card SHALL display a coloured icon container, a large numeric value in `--font-display`, and a small uppercase label.
2. WHEN a pointer device hovers over a Stat_Card, THE Stat_Card SHALL translate upward by 3 px and increase its box-shadow depth within 200 ms.
3. THE Stat_Card SHALL use a border-radius of at least 12 px.
4. THE Admin_Dashboard SHALL render at least ten Stat_Cards covering trucks (total, available, on-route, maintenance), drivers, shipments (in-transit, pending, delivered), and pending alerts (fuel, accidents, breakdowns, calls).
5. THE Driver_Dashboard SHALL render Stat_Cards for the driver's name, assigned truck, and license number.
6. THE Customer_Dashboard SHALL render Stat_Cards for total shipments, in-transit shipments, and paid shipments.

---

### Requirement 6: Data Table Styling

**User Story:** As an Admin, I want data tables to be easy to read and interact with, so that I can manage fleet entities efficiently.

#### Acceptance Criteria

1. THE Data_Table SHALL render inside a white card container with border-radius ≥ 12 px and a subtle box-shadow.
2. THE Data_Table SHALL render a card header containing a section title and, where applicable, an action button (e.g. "View All", "Add New").
3. THE Data_Table thead SHALL use a light background (`#f8f9fa`), uppercase column labels, reduced font size (≤ 0.8 rem), and letter-spacing ≥ 0.5 px.
4. THE Data_Table tbody rows SHALL apply a hover background tint to indicate interactivity.
5. WHEN a Data_Table has no rows, THE Empty_State SHALL be rendered inside the card with a centred icon and descriptive message.
6. THE Data_Table SHALL render action buttons (Edit, Delete, Approve, Reject, Resolve) as small pill-shaped buttons with appropriate semantic colours.

---

### Requirement 7: Badge Status System

**User Story:** As any user, I want entity statuses to be instantly recognisable through colour coding, so that I can assess state without reading text carefully.

#### Acceptance Criteria

1. THE Badge_Status SHALL use pill-shaped styling with border-radius ≥ 20 px, horizontal padding ≥ 0.6 rem, and font-size ≤ 0.75 rem.
2. THE Badge_Status SHALL apply the following colour mappings:
   - `Available` → green background / green text (`--color-success-bg` / `--color-success-text`)
   - `On Route` / `In Transit` → blue background / blue text (`--color-info-bg` / `--color-info-text`)
   - `Maintenance` / `Pending` / `Unpaid` → amber background / amber text (`--color-warning-bg` / `--color-warning-text`)
   - `Delivered` / `Resolved` / `Approved` / `Paid` → green background / green text
   - `Reported` / `Open` / `Rejected` → red background / red text (`--color-danger-bg` / `--color-danger-text`)
3. THE Badge_Status SHALL render with `font-weight: 600` for legibility.

---

### Requirement 8: Form and Input Styling

**User Story:** As any user submitting data, I want forms to be clean and easy to fill out, so that I can complete tasks without friction.

#### Acceptance Criteria

1. THE Form_Card SHALL render with a white background, border-radius ≥ 12 px, and a subtle box-shadow.
2. THE Form_Card SHALL render a section heading in `--font-display` with `font-weight: 700`.
3. THE UI_System SHALL style all `<input>`, `<select>`, and `<textarea>` elements with border-radius ≥ 8 px, a `1px solid` border in a neutral colour, and a focus ring using `--color-accent-2` with reduced opacity.
4. THE UI_System SHALL style form labels in uppercase, font-size ≤ 0.85 rem, `font-weight: 600`, and letter-spacing ≥ 0.4 px.
5. THE UI_System SHALL style the primary submit button with `--color-primary` background, white text, border-radius ≥ 8 px, and a hover state that darkens the background by at least 10 %.
6. WHEN a form field receives focus, THE UI_System SHALL apply a visible focus ring that meets WCAG 2.1 AA contrast requirements for focus indicators.

---

### Requirement 9: Alert Banner Styling

**User Story:** As any user, I want flash messages to be clearly visible and dismissible, so that I receive feedback on my actions without the message blocking my workflow.

#### Acceptance Criteria

1. THE Alert_Banner SHALL render with border-radius ≥ 10 px and no visible border.
2. THE Alert_Banner SHALL include a leading icon appropriate to the category (success, danger, info, warning).
3. THE Alert_Banner SHALL include a dismiss button that removes the banner from the DOM when clicked.
4. THE Alert_Banner SHALL be rendered at the top of the page body, above all other page content.

---

### Requirement 10: Authentication Page Design

**User Story:** As a new or returning user, I want the login, register, and forgot-password pages to look professional and trustworthy, so that I feel confident using FleetGuard.

#### Acceptance Criteria

1. THE Auth_Pages SHALL use a two-column split layout on Desktop_Breakpoint: a branded left panel and a form right panel.
2. THE Auth_Pages left panel SHALL display the FleetGuard logo, brand name, tagline, and a feature bullet list against the `--color-primary` background.
3. THE Auth_Pages right panel SHALL display the form on a white background with generous padding (≥ 2.5 rem).
4. WHEN the viewport is at Mobile_Breakpoint, THE Auth_Pages SHALL hide the left panel and render the form panel at full viewport width.
5. THE Auth_Pages SHALL render input fields with icon prefixes (user icon for username, lock icon for password, envelope icon for email).
6. THE Auth_Pages SHALL include navigation links between login, register, and forgot-password pages.

---

### Requirement 11: Driver Emergency Action Cards

**User Story:** As a Driver, I want my quick-action buttons to be large and visually distinct, so that I can trigger emergency reports quickly even under stress.

#### Acceptance Criteria

1. THE Driver_Dashboard SHALL render quick-action items as card components with a large centred icon (≥ 2 rem), a bold label, and a short description.
2. WHEN a pointer device hovers over a Driver action card, THE card SHALL translate upward by 4 px and increase box-shadow depth within 200 ms.
3. THE Driver_Dashboard action cards SHALL use semantically appropriate icon colours: blue for location, amber for fuel, red for accident, amber for breakdown, purple for call admin, green for shipments.
4. THE Driver_Dashboard action cards SHALL be arranged in a responsive grid: 2 columns on Mobile_Breakpoint, 3 columns on Tablet_Breakpoint, and 4 columns on Desktop_Breakpoint.

---

### Requirement 12: Mobile Navigation Overlay

**User Story:** As a mobile user, I want the navigation to be accessible without consuming screen space, so that I can navigate the app on a small screen without losing content area.

#### Acceptance Criteria

1. WHEN the Sidebar is open on Mobile_Breakpoint, THE UI_System SHALL render a semi-transparent dark overlay covering the main content area.
2. WHEN the user taps the overlay, THE Sidebar SHALL close and THE overlay SHALL be removed.
3. THE overlay SHALL have a z-index lower than the Sidebar and higher than the main content.
4. THE Sidebar open/close state SHALL be managed via a CSS class toggle on the Sidebar element, driven by a JavaScript event listener on the hamburger button.

---

### Requirement 13: Typography Hierarchy

**User Story:** As any user, I want a clear typographic hierarchy across all pages, so that I can quickly identify headings, labels, values, and body text.

#### Acceptance Criteria

1. THE UI_System SHALL apply `--font-display` (Rajdhani) to all page titles, section headings, stat values, brand names, and card headings.
2. THE UI_System SHALL apply `--font-body` (Inter) to all body text, table content, form labels, and navigation links.
3. THE UI_System SHALL define at least five font-size steps: 0.75 rem, 0.875 rem, 1 rem, 1.25 rem, and 2 rem, used consistently across components.
4. THE UI_System SHALL set `line-height` to at least 1.5 for body text and 1.2 for display headings.

---

### Requirement 14: Colour Contrast and Accessibility

**User Story:** As any user including those with visual impairments, I want the UI to meet minimum contrast standards, so that text and interactive elements are legible.

#### Acceptance Criteria

1. THE UI_System SHALL ensure all body text rendered on white backgrounds achieves a contrast ratio of at least 4.5:1 against the background colour.
2. THE UI_System SHALL ensure all interactive elements (buttons, links) have a visible focus indicator.
3. THE UI_System SHALL not rely solely on colour to convey status information; Badge_Status components SHALL include text labels alongside colour.
4. THE UI_System SHALL set `lang="en"` on the `<html>` element of every page.

---

### Requirement 15: CSS Architecture and Maintainability

**User Story:** As a developer, I want the CSS to be well-organised and free of inline styles, so that future UI changes can be made efficiently.

#### Acceptance Criteria

1. THE UI_System SHALL consolidate all custom styles into `static/css/main.css`, eliminating inline `<style>` blocks from `base.html` and all page templates.
2. THE UI_System SHALL organise `main.css` into clearly commented sections: Design Tokens, Reset/Base, Layout, Sidebar, Topbar, Components (Stat Card, Data Table, Form Card, Badge Status, Alert, Empty State, Driver Action Card), and Page-Specific overrides.
3. THE Base_Template SHALL load `main.css` via a `<link>` tag referencing `{{ url_for('static', filename='css/main.css') }}`.
4. THE UI_System SHALL not introduce any JavaScript framework dependencies; all interactivity SHALL be implemented in vanilla JavaScript or via Bootstrap 5's existing bundle.
5. WHEN a new page template is added to FleetGuard, THE developer SHALL be able to apply the full design system by extending `base.html` and using the documented component classes without writing additional CSS.
