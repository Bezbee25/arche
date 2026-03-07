# Spec: theme task dev

## Description

# Spec: Theme IHM Web

## Goal

Add a theme selector menu to the web UI header, allowing users to switch the interface color scheme in one click among several predefined themes.

## Context

- The web UI is a single-page vanilla JS application served from `web/static/` (HTML, CSS, JS).
- All colors are defined via CSS custom properties on `:root` in `style.css` (lines 4–22): `--bg`, `--bg2`, `--bg3`, `--border`, `--text`, `--text-dim`, `--text-muted`, `--green`, `--yellow`, `--red`, `--blue`, `--cyan`, `--purple`.
- Currently only a dark theme exists (hard-coded in `:root`). There is no theme switching mechanism.
- The header (`#header`) already contains a `.header-actions` group on the right side with buttons (New track, Archi, Memory, Refresh, Docs). The theme menu must be placed within this group.
- The xterm.js terminal has its own theme object in `app.js` (line 971, `TERM_OPTS.theme`), which must also update when the UI theme changes.
- Theme persistence must be scoped to the **working directory** (project), not global across all projects. The project is identified by its storage path or project name available from the `/api/project` endpoint.

## Requirements

1. **Define theme color palettes**
   - Define at least 6 complete CSS variable sets, one per theme:
     - **Dark** (current default — `--bg: #0d0d0d`, existing values)
     - **Light** (light backgrounds, dark text, appropriate accent colors)
     - **Pastel Grey/Orange** (soft grey backgrounds with orange accents)
     - **Pastel Violet** (soft violet-tinted backgrounds with purple accents)
     - **2 additional themes** of the developer's choice, with colors that are easy on the eyes and sit between light and dark intensity (e.g., a warm earth-tone theme, a blue-grey "nord"-style theme, a solarized variant, etc.)
   - Each theme must define all CSS variables currently in `:root` (`--bg`, `--bg2`, `--bg3`, `--border`, `--text`, `--text-dim`, `--text-muted`, `--green`, `--yellow`, `--red`, `--blue`, `--cyan`, `--purple`).
   - Each theme must also define a matching xterm.js theme object (`background`, `foreground`, `cursor`, `selection`).
   - **Acceptance criteria:** All 6+ themes render legibly; text contrast is sufficient (no light-on-light or dark-on-dark); accent colors remain visually distinct from each other within each theme.

2. **Add a "Theme" dropdown menu in the header**
   - Place a "Theme" button in `.header-actions` (top-right header bar), styled consistently with existing buttons (`btn-ghost btn-sm`).
   - Clicking the button opens a dropdown/popover listing all available theme names.
   - Clicking a theme name in the dropdown applies that theme immediately (no page reload, no confirmation dialog) and closes the dropdown.
   - Clicking outside the dropdown closes it without changing the theme.
   - **Acceptance criteria:** The menu appears aligned below/next to the Theme button; selecting a theme applies it instantly to the entire UI including terminal; the dropdown closes after selection or on outside click.

3. **Apply theme by updating CSS custom properties**
   - Theme switching must work by updating the CSS custom properties on `:root` (or `document.documentElement`), so that all existing CSS rules automatically pick up the new colors without any class changes on individual elements.
   - The xterm.js terminal theme (`TERM_OPTS.theme`) must also be updated, and all open terminal instances must have their theme refreshed in place.
   - **Acceptance criteria:** Switching theme updates every part of the UI (header, sidebar, panels, modals, console bar, scrollbars, terminal) without requiring a page reload.

4. **Persist theme choice per working directory**
   - Store the selected theme identifier in `localStorage` using a key scoped to the current project/working directory (e.g., `arche-theme-<projectName>` or `arche-theme-<projectPath>`).
   - On page load, read the persisted value and apply the corresponding theme before the UI becomes visible (to avoid a flash of the default theme).
   - If no persisted value exists, default to the **Dark** theme (current behavior).
   - **Acceptance criteria:** Reloading the page preserves the last-selected theme for that project; opening the UI for a different project uses that project's own stored preference (or the default).

5. **No functional changes**
   - The theme feature must not alter any existing functionality: tracks, tasks, modals, terminal, SSE streaming, polling, keyboard shortcuts, etc. must all work identically.
   - **Acceptance criteria:** All existing user workflows (create track, run task, edit task, open/close modals, use terminal, etc.) continue to work unchanged after the theme feature is added.

## Constraints

- Pure CSS + vanilla JS only — no build tools, no CSS-in-JS, no additional frameworks or libraries.
- All theme data (color definitions) must live client-side (in `style.css` and/or `app.js`). No server-side API changes.
- Theme colors must be non-aggressive and comfortable for extended use — avoid saturated neons, pure white backgrounds, or harsh contrast combinations.
- The dropdown menu CSS must not conflict with existing modal or popover styles.

## Out of Scope

- Custom/user-defined themes or a color picker.
- Server-side theme storage or any backend API changes.
- Per-user theme preferences (the scope is per working directory only, stored in the browser).
- Animated transitions between themes.
