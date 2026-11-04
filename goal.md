# TRADO — Product Goal and Requirements

## Purpose

Build TRADO into a clear, trustworthy trading-literacy platform where a beginner can learn how markets and trading tools work, practise decisions safely, and understand the risks behind each choice. The product should feel like a guided learning game while rewarding knowledge, reflection, and consistency rather than simulated profits or risk-taking.

This document records the current project baseline and a proposed product and engineering direction. Proposed requirements below are goals; they are not claims that those features already exist.

## Product promise

TRADO teaches concepts and decision-making habits. It does not tell users what to buy or sell, promise returns, or execute real trades. Every practice price and trade is clearly identified as simulated or user-entered. XP, coins, lives, badges, and paper-trading cash have no cash value.

The distinctive product loop should be:

1. **Understand** a short, reviewed concept.
2. **Apply** it to a concrete market scenario.
3. **Explain** the decision and its uncertainty or downside.
4. **Reflect** on mistakes and revisit the concept later.

This risk-aware practice loop is TRADO's main point of difference. The product should not become a generic XP leaderboard or a simulated-profit contest.

## Current project baseline

### Stack and structure

- Flask serves the HTML pages and same-origin JSON APIs; SQLite stores accounts and progress.
- The frontend uses plain HTML, one shared CSS file, and vanilla JavaScript.
- `backend/app.py` defines the application, authentication, learning rules, and API routes. `backend/database.py` creates/migrates the SQLite schema and seeds learning content. `backend/config.py` holds environment-backed settings.
- `frontend/` contains the landing page, login, registration, onboarding, dashboard, learning catalogue, lesson, profile, simulator, leaderboard, and terms pages.
- The working implementation uses generated SVG avatars. The four JPEGs remain in `frontend/static/images`, but are no longer embedded in the pages.

### Features present in the source

- Account registration and login with Werkzeug password hashes, signed-cookie sessions, a remember option, and a process-local failed-login limit.
- First-run category and daily-goal onboarding; profile editing for name, trader type, avatar, and goal.
- Five seeded learning paths—Stock, Forex, Cryptocurrency, Options, and Intraday—with five levels per path.
- Six server-validated questions per level, explanations, persisted attempts, a first-pass/review flow for the first level, server-side unlock checks, and resumable progress.
- Five lives, a four-hour life recovery interval, question and level rewards, hints costing three coins, stars, streaks, achievements, daily activity, and in-app notifications.
- A dashboard with category selection, a level roadmap, field notes, progress, daily goals, and achievement summaries.
- A leaderboard sorted by XP.
- A paper-trade ledger with a starting virtual cash balance. Users enter their own prices; the simulator does not fetch market prices, enforce holdings on sells, calculate portfolio performance, or execute real trades.
- Terms that describe the educational and simulated nature of the application.

### Data model

The original account, lesson, quiz, completion, badge, and virtual-trade tables coexist with learning tables for categories, preferences, worlds, level metadata, questions, question state and attempts, lives, a separate coin wallet, reward transactions, streaks, daily activity, achievements, and notifications. Preserve existing account and progress data when evolving this schema.

### Existing user flow

1. A new learner registers and accepts the terms.
2. They choose at least one learning path, a daily goal, and their timezone.
3. The dashboard opens the next available level for each selected path.
4. The learner reads the lesson, answers questions, receives feedback, and can spend coins on hints.
5. Mastery awards progress and rewards; mistakes in the first level return during review.
6. Activity, streaks, notifications, profile preferences, and paper trades are saved to the account.

## Product requirements

### Learning quality and differentiation

- Every level must teach one bounded learning objective and use plain language appropriate for a beginner.
- A complete lesson should explain the concept, show a scenario, name a material risk or limitation, and end with a practical takeaway.
- Questions must test understanding and application, not just repeat the same fact. Distractors should represent plausible misconceptions, not obviously absurd answers.
- A wrong answer should explain the reasoning, identify the misconception where practical, and give the learner a useful retry or review path.
- Add a **Decision Lab** to selected lessons: a short scenario with a choice, the reasoning behind the choice, and a “what could go wrong?” reflection. Scenarios must make uncertainty explicit and must not imply a recommended real-world trade.
- Add a **Mistake Review** queue that revisits missed concepts over time. Reward recovered understanding and explanation quality, not speed or trading returns.
- Have trading and financial subject matter reviewed before publishing curriculum. Record a review date and source notes for claims that could change; keep stable principles separate from time-sensitive rules.
- Keep the five current paths coherent, then expand only when the existing path has reviewed lessons, questions, and risk explanations end to end.

### Progress, rewards, and fairness

- The server remains authoritative for answer correctness, level unlocks, mastery, rewards, and saved progress.
- Repeated requests must not duplicate XP, coins, completion records, or achievements.
- Define the separate meanings of **coins** (learning rewards/hints) and **TRADO Cash** (simulated trade balance) wherever they appear.
- Make lives and hint costs understandable before a learner spends or loses them. Never block access to educational explanations because a learner has no coins or lives.
- Keep progress useful without making a missed answer feel punitive. Allow review of completed lessons.
- Change competitive ranking to emphasize learning outcomes—mastery, consistency, or completed learning goals. Do not rank users by simulated profit or encourage higher-risk behavior.
- Explain what each streak, star, and achievement measures. Rewards must never be presented as money or as evidence of trading ability.

### Accounts, preferences, and privacy

- Registration, login, logout, onboarding, and profile updates must give clear, recoverable errors and preserve valid user state.
- Users can change paths and goals without losing prior completions. Removing a path from view must not silently delete its data.
- Provide a clear account-data explanation and, before public release, a supported account deletion and data export process.
- Get appropriate consent for any public display of a learner's name or progress. Let users opt out of public rankings or use a display name.
- Password reset and email verification remain incomplete until an actual delivery provider and end-to-end flow exist. Never display a fake success state.

### Paper-trading simulator

- Keep every simulator screen labelled as hypothetical, with user-entered prices distinguished from live prices.
- Show the arithmetic for each trade and the effect on virtual cash before confirmation.
- Reject malformed symbols, non-finite or non-positive quantity/price values, and purchases that exceed the available virtual balance.
- Before describing the simulator as a portfolio, add holdings/quantity checks, a clear sell rule, transaction history, and a reproducible balance calculation. Until then, keep the current ledger limitations visible.
- Any future live data integration is a separate, explicitly scoped product decision; it must not silently replace simulated values.

### Interface and accessibility

- Keep the mobile-first dashboard and lesson flow fast to scan, with a clear next action and clear locked/completed states.
- All actions must work with keyboard navigation, have visible focus, use meaningful labels, and announce important feedback to assistive technology.
- Respect reduced-motion preferences, maintain readable contrast and text sizing, and avoid relying on color or animation alone to explain status.
- Provide useful loading, empty, offline, and error states for every page that depends on an API.
- Keep account forms and lesson controls usable on narrow screens and at browser zoom.
- Use text, CSS, and the existing SVG avatars where they improve the experience; decorative artwork must not be required to understand a feature.

### Security, reliability, and operations

- Use a stable, secret deployment key; fail safely when production configuration is missing. Define and document one reliable local `.env` loading contract without exposing secrets.
- Protect state-changing routes against cross-site request forgery and use robust rate limits for authentication and other abuse-sensitive routes.
- Set secure cookies and HTTPS behavior explicitly for deployment. Keep error responses useful to users and avoid returning internal exception details.
- Move schema initialization and seeding into a deliberate startup/migration path rather than relying on application import side effects.
- Choose one source of truth for database and frontend paths; the current configuration declares paths while other modules also define them.
- Keep migrations additive and test them against both a new database and a copy of the existing database before release.
- Add automated coverage for authentication, onboarding, unlock enforcement, answer review, reward idempotency, life recovery, timezones, notifications, and simulator accounting.
- Add browser checks for the complete first-run and returning-user journeys at desktop and mobile sizes. Syntax checks and API smoke checks are useful, but do not replace browser or regression coverage.

## Current gaps and documentation notes

1. The existing `IMPLEMENTATION_CHECKLIST.md` describes several features as unfinished even though the current source contains them. Reconcile it with the actual application before using it as a delivery tracker.
2. The README understates the current lesson depth and should describe the present five-path, five-level structure and current simulator limitations accurately.
3. No automated test suite is checked in. A temporary-database smoke run and Python/JavaScript syntax checks have passed, but they do not establish production readiness or complete frontend behavior.
4. CSRF protection and production-grade authentication throttling are not present. The failed-login counter is in memory and will not be shared across workers or survive a restart.
5. `python-dotenv` is listed as a dependency, but the Python entry path does not explicitly load `.env`; document or implement the expected configuration behavior before relying on it.
6. Password reset delivery, email verification, account deletion/export, and public leaderboard privacy controls are not implemented.
7. Curriculum and quiz content are hard-coded seed data. A content review and change workflow is needed before broad release.
8. The simulator is intentionally a ledger rather than a portfolio simulator; its cash and sell behavior should remain explicit in product copy.

## Recommended delivery sequence

### Phase 1 — Establish a trustworthy baseline

- Update README and implementation tracking to reflect current source behavior.
- Add automated tests around existing flows and database migration from the current schema.
- Make configuration, secrets, database paths, startup behavior, and production cookie settings explicit.
- Add CSRF protection and durable rate limiting before exposing account routes publicly.
- Review curriculum and verify all user-visible rewards, coins, cash, and leaderboard labels are clear.

### Phase 2 — Deliver the distinctive learning loop

- Pilot Decision Labs in a small number of lessons.
- Improve distractors and misconception-specific explanations.
- Add a Mistake Review queue with saved, spaced review state.
- Show progress by concept mastery and consistency, with XP as a supporting signal.
- Validate the experience with beginner learners and revise content based on observed confusion.

### Phase 3 — Make practice coherent and fair

- Improve simulator confirmations and balance transparency.
- Decide whether to keep the ledger intentionally small or build a holdings-aware virtual portfolio; do not blur the two models.
- Add leaderboard privacy/display-name controls and rank learning behavior rather than paper returns.
- Add export and deletion flows, along with clear retention behavior.

### Phase 4 — Polish and release readiness

- Test keyboard, screen-reader feedback, reduced motion, zoom, and responsive layouts.
- Test error, empty, loading, and network-interruption states across all pages.
- Add migration/backup/restore instructions and a repeatable deployment checklist.
- Run a release review for educational claims, privacy copy, simulator disclosure, and reward language.

## Release acceptance criteria

A public release is ready only when:

- A new learner can register, complete onboarding, finish a level, leave, return, and resume without losing or duplicating progress.
- The server rejects locked-level access and invalid answers, and repeated completion requests never pay rewards twice.
- Migrations preserve existing accounts, completions, and paper trades; migration tests use a disposable database copy.
- The simulator is consistently described as simulated, and its displayed balance matches the documented ledger rules.
- Every published lesson has reviewed content, meaningful questions, a risk explanation, and a clear source/review record where appropriate.
- State-changing routes, secrets, session cookies, login throttling, and error handling meet the deployment security requirements above.
- Core journeys work with keyboard-only input and at mobile size, with reduced motion enabled.
- Users understand what TRADO stores, how leaderboard visibility works, and how to leave the service and retrieve or delete their data.
- Documentation matches the behavior shipped in the application.

## Product guardrails and non-goals

- No brokerage connection, real-money trading, trade execution, or personalized investment recommendations.
- No live market feed in the current scope. Any future feed must show provenance, timestamp, delays, and simulation boundaries.
- No reward or competition mechanic based on risk-taking, leverage, short-term returns, or simulated profit.
- No claims that completing lessons makes a learner profitable or qualified to trade.
- Preserve the current Flask, SQLite, HTML, CSS, and vanilla JavaScript architecture unless a measured product or reliability need justifies a change.
- Preserve existing user data and behavior through explicit, reviewed migrations; do not replace the database as a shortcut.

## Success measures

Track learning outcomes alongside usage:

- New-user onboarding completion and first-level completion.
- Correctness on first attempt and later mastery after a mistake.
- Return rate to review items and retention of concepts after a delay.
- Completion of user-selected learning goals and voluntary return to lessons.
- Simulator comprehension: learners can explain that prices are hypothetical and calculate the effect on virtual cash.
- Accessibility and reliability findings from browser testing, reported by severity and resolved before release.

Set numeric targets only after establishing a baseline with real beginner users. Higher session time, more trades, or more risk-taking are not success measures by themselves.
