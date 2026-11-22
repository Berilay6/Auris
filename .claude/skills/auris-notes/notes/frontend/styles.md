# frontend/src/styles

Code: `frontend/src/styles/global.css`

## Rules

- Shared colors are CSS variables in the `:root` block of `global.css`. Use them
  with `var(--color-...)`.
- Success / OK state (green): `--color-success` (text), `--color-success-bg`,
  `--color-success-border`.
- Error / danger state (red): `--color-danger` (text), `--color-danger-bg`,
  `--color-danger-border`.
- Do not add new color codes for success or error states. Use these variables.
- When a new color is needed in more than one place, add it to `:root` first.

## Decision log

| Date | Task | Decision | Who |
|---|---|---|---|
| 2026-11-22 | SCRUM-20 | Standard success (green) and danger (red) colors live in `:root` | Kaan |
