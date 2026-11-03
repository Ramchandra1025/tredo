# TRADO – Gamified Trading Learning Platform

A learning-focused Flask + SQLite + HTML/CSS/JavaScript application. It includes account registration/login, five seeded learning paths, lesson quizzes, XP, TRADO Cash, a first-lesson badge, a leaderboard, and a basic virtual trade ledger.

## Run locally (Windows PowerShell)

1. Open a terminal in the `TRADO` folder.
2. Create and activate a virtual environment:

   ```powershell
   py -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use `venv\Scripts\activate.bat` in Command Prompt, or run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in the current PowerShell window.

3. Install dependencies:

   ```powershell
   pip install -r backend/requirements.txt
   ```

4. Start Flask:

   ```powershell
   cd backend
   python app.py
   ```

5. Open http://127.0.0.1:5000

The SQLite database is created automatically at `backend/database/trado.db`.

## Notes

- This is an educational starter implementation, not a production financial application.
- The simulator records hypothetical paper trades at prices entered by the learner. It does not fetch live market prices, manage holdings, calculate portfolio P/L, or execute real trades.
- The virtual wallet is a simple ledger: BUY deducts the entered total and SELL adds it. It does not enforce ownership/quantity of assets.
- Set a strong `SECRET_KEY` environment variable before deployment; use HTTPS and add CSRF protection, rate limiting, email verification, password reset, and stronger validation before public launch.
- The sample lessons and quizzes are seed content. Expand and review educational material before publishing.
