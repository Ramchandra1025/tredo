# TRADO upgrade checklist

## Audit (before changes)

- [x] Existing stack: Flask 3, SQLite, server static files, vanilla HTML/CSS/JavaScript.
- [x] Existing auth: Flask signed-cookie session and Werkzeug password hashes.
- [x] Existing data: `users`, `lessons`, `quizzes`, `user_progress`, `user_rewards`, `virtual_trades`.
- [x] Existing flows: registration/login, a single-question lesson quiz, basic XP/TRADO Cash, one badge, leaderboard, paper-trade ledger.
- [x] Existing curriculum: five categories, two lessons per category, one quiz per lesson.
- [x] Existing user database found at `backend/database/trado.db`; retain it and migrate additively.
- [x] Frontend/backend are connected through same-origin JSON APIs.
- [x] Main gaps: onboarding/preferences, multi-level roadmap, six-question mastery, saved attempts, server unlock enforcement, lives, active-time tracking, streaks, achievements, notifications, and mobile-first game UI.

## Upgrade plan and implementation status

- [x] Preserve current stack, routes where practical, records, and paper-trading feature.
- [ ] Add backward-compatible SQLite tables/indexes and seed structured learning content.
- [ ] Add secure auth improvements and first-run category/goal onboarding; returning accounts skip onboarding.
- [ ] Build category roadmaps with completed/current/locked states and server-side unlock checks.
- [ ] Implement six-question server-validated mastery, mistake explanations, retry, and resumable progress.
- [ ] Add idempotent XP/coin transactions, five regenerating lives, accuracy/stars, streaks, and achievements.
- [ ] Track active learning time by the user's date/timezone and expose goal progress.
- [ ] Add profile/settings and notification read/unread APIs.
- [ ] Upgrade the dashboard and lesson experience with responsive game-style navigation and reduced-motion support.
- [ ] Keep the paper simulator clearly labeled as hypothetical and simulated.
- [ ] Run focused API/database and frontend smoke checks for the implemented flows.

## Known scope limits from the provided prompt

- The attached prompt ends during Phase 4 (after “Explanation and retry”), so no later phase instructions were included.
- Password reset delivery needs an email service/configuration that this repository does not have; do not report a fake reset as complete.
- Notification storage/read state can be implemented locally; delivery channels are explicitly deferred in the prompt.
