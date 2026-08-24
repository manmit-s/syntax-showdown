<div align="center">

# Syntax Showdown
### 1v1 Code Clash Arena

*A real-time competitive programming platform where two players race to solve the same AI-generated coding problem.*

*Capstone project — Mirai School of Technology*

<p align="center">
  <a href="https://syntax-showdown.streamlit.app" target="_blank">
    <img src="https://static.streamlit.io/badges/streamlit_badge_black_white.svg" alt="Open in Streamlit" />
  </a>
</p>

<p align="center">
  <a href="https://syntax-showdown.streamlit.app">
    <img src="https://img.shields.io/badge/LIVE_DEMO-🚀_Try_Now-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Live Demo" />
  </a>
  <br/>
  <sub><strong>https://syntax-showdown.streamlit.app</strong> &nbsp;•&nbsp; No login &nbsp;•&nbsp; Create a match in 10 seconds &nbsp;•&nbsp; Share the link with your opponent</sub>
</p>

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Firebase](https://img.shields.io/badge/Firestore-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)
![Gemini](https://img.shields.io/badge/Gemini_API-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white)
![Git](https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white)

</div>

---

## Overview

One player creates a match and picks a difficulty. Gemini generates a unique algorithmic problem on the spot, and a shareable URL is produced. The second player opens that link, both land in the same arena, and the clock starts.

Each player writes a Python solution directly in the browser. On submit, the code runs against three test cases locally, and Gemini reviews it for time complexity, space complexity, code quality, and correctness — plus a short roast of the code style, because feedback should sting a little. The final score is the test pass rate (up to 100 points) plus an AI bonus (0–10 points). Scores sync to Firestore in real time, and when both players have submitted, the results screen reveals the winner.

---

## Architecture

The application is split into four deliberately separate layers.

```
/
├── app.py                        Router — screens, query params, SDK init
├── requirements.txt
├── .gitignore
├── .env.example
│
├── .streamlit/
│   ├── secrets.toml              (not committed)
│   └── secrets.toml.example
│
├── core/                         Business logic — zero UI code
│   ├── ai_engine.py               Gemini communication
│   ├── db_client.py               Firestore communication
│   └── code_sandbox.py            Sandboxed code execution
│
├── components/                   Streamlit render functions
│   ├── layout.py
│   ├── editors.py
│   └── forms.py
│
└── utils/                        Cross-cutting helpers
    ├── config.py                  Single source of truth for constants
    └── state_manager.py           All st.session_state reads/writes
```

**`core/ai_engine.py`** owns all Gemini communication. It initializes a module-level client once per process, uses `gemini-3.5-flash` for both problem generation and code review, and retries failed calls up to three times with exponential back-off before surfacing an error.

**`core/db_client.py`** owns all Firestore communication — match creation, state reads, player updates, and the Player 2 join flow, which uses a Firestore transaction to prevent race conditions when both users try to claim the same slot.

**`core/code_sandbox.py`** executes submitted Python via `exec()`. Submissions are sanitized against a blocklist of dangerous substrings and regex patterns first. It also auto-detects the function to run, preferring one literally named `solve` and falling back to the first user-defined callable.

**`components/`** render functions accept data as arguments and return user input. They never read session state or call `core/` directly — that boundary is intentional.

**`utils/config.py`** is the single source of truth for every constant: model names, Firestore collection names, scoring limits, sandbox limits, status values, and blocked code patterns.

**`utils/state_manager.py`** is the only module that touches `st.session_state`.

**`app.py`** initializes the SDKs, reads the `match_id` query parameter, and routes to one of four screens: lobby, waiting room, arena, or results.

---

## Prerequisites

- Python 3.11+
- A Google AI Studio account with an API key (free tier works)
- A Firebase project with Firestore enabled in Native mode

---

## Local Setup

### 1. Clone and create a virtual environment

```bash
git clone <your-repo-url>
cd <project-folder>
python -m venv .venv
```

Activate it:

```powershell
# Windows
.venv\Scripts\Activate.ps1
```
```bash
# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure secrets

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Open `.streamlit/secrets.toml` and fill in two things:

**Gemini API key** — get one at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey):

```toml
GEMINI_API_KEY = "your-key-here"
```

**Firebase service account credentials** — from the [Firebase console](https://console.firebase.google.com): open your project → Project Settings → Service Accounts → Generate new private key. A JSON file downloads; copy its values into the `[firebase_credentials]` block. The `private_key` field must stay on a single line with literal `\n` characters exactly as they appear in the JSON — do not press Enter inside it.

> **Encoding warning:** `secrets.toml` must be saved as UTF-8 **without BOM**. In VS Code, check the status bar in the bottom-right. A BOM corrupts the first key name in Streamlit's TOML parser, which makes secrets appear missing even when they're present.

### 4. Set Firestore security rules

In the Firebase console → Firestore Database → Rules tab, replace the defaults with:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /matches/{matchId} {
      allow read, write: if true;
    }
  }
}
```

Click **Publish**. These rules are wide open — fine for development and demos, **not fine for production**. Add authentication before any real users touch this.

### 5. Run the app

Always use the virtual environment's own executable:

```powershell
.venv\Scripts\streamlit.exe run app.py
```

Streamlit opens `http://localhost:8501` automatically.

---

## Testing the Full Flow Locally

You don't need two computers — two browser tabs will do.

1. In tab one, go to `http://localhost:8501`, pick a difficulty, and click **Create Match**.
2. The URL becomes something like `http://localhost:8501/?match_id=clash_a3f9c1&player=p1`. Copy it.
3. Paste it into tab two. That tab is assigned Player 2 and the match goes active.
4. Both tabs show the same problem. Write a solution in each, then **Run and Evaluate**.
5. Once both submissions land, the results screen shows final scores and the winner.

---

## Scoring

| Component | Formula | Max |
|---|---|---|
| Test score | `floor(passed / total * 100)` | 100 |
| AI bonus | Gemini-judged: complexity + code quality | 10 |
| **Final score** | Test score + AI bonus | **110** |

---

## Firestore Data Model

All matches live in a top-level `matches` collection. Document IDs follow the format `clash_xxxxxx`, where the suffix is a random six-character hex string.

```
matches/
  clash_a3f9c1/
    created_at: "2026-08-15T10:00:00Z"
    status: "waiting" | "active" | "finished"
    problem_data:
      title: string
      description: string
      constraints: [string]
      starter_code: string
      test_cases: [{input: [...], expected_output: any}]
    players:
      p1:
        code: string
        score: integer
        status: "joined" | "submitted"
      p2:
        code: string
        score: integer
        status: "waiting" | "joined" | "submitted"
```

Player fields update atomically via dot-notation paths (`players.p1.score`) so one player's write never clobbers the other's data. Joining as Player 2 uses a Firestore transaction to prevent two users from claiming the same slot at once.

---

## Sandbox Security — Read This

The code sandbox runs submissions through Python's built-in `exec()`. This blocks the *obvious* abuse. It is **not** a secure execution environment, and it should not be treated as one.

The sanitizer rejects a fixed list of substrings (`import os`, `open(`, `__import__(`, and others), two regex patterns matching `eval`/`exec` at word boundaries, and any submission over 10,000 characters.

**This is a blocklist, not a sandbox.** Blocklists are bypassable by anyone who wants to bypass them — that's true of every substring/regex-based filter, not a flaw specific to this implementation. Treat this as adequate for controlled demos, internal tools, and contests among trusted participants, and nothing beyond that.

For any deployment with untrusted users, replace the runner with genuine isolation: a Docker container (or equivalent) with CPU and memory limits, no network access, and a read-only filesystem. Do not skip this step and assume the blocklist will hold.

---

## Deployment — Streamlit Community Cloud

1. Push the repo to GitHub. Confirm `.streamlit/secrets.toml` is in `.gitignore` and **not** committed.
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your GitHub account.
3. Select the repository, set the main file path to `app.py`, and deploy.
4. In the app's settings, open the **Secrets** section and paste the full contents of your local `secrets.toml`.
5. Save, let the app restart, and test the deployed URL in two separate browsers or devices.

---

## Configuration Reference

All constants live in `utils/config.py`.

| Constant | Default | Purpose |
|---|---|---|
| `GEMINI_PROBLEM_MODEL` | `gemini-3.5-flash` | Model used to generate problems |
| `GEMINI_REVIEW_MODEL` | `gemini-3.5-flash` | Model used to review code |
| `NUM_TEST_CASES` | `3` | Test cases Gemini generates per problem |
| `MAX_CODE_LENGTH` | `10000` | Max submission length (characters) |
| `MAX_TEST_SCORE` | `100` | Points for passing all test cases |
| `AI_BONUS_MAX` | `10` | Max AI bonus points |
| `POLL_INTERVAL_SECS` | `3` | Seconds between Firestore polls |
| `DEFAULT_DIFFICULTY` | `medium` | Pre-selected lobby difficulty |

---

## Known Limitations

- **Polling, not push.** The waiting room and arena poll Firestore on a timer rather than holding a persistent connection — up to a 3-second lag before one player's screen reflects the other's action.
- **No resource limits.** The sandbox enforces no CPU or memory ceiling. An infinite loop or a large allocation will hang or crash the Streamlit worker for the duration of the request.
- **Imperfect test-case matching.** AI-generated test cases occasionally mishandle edge cases in the sandbox comparison — most often with float outputs or string formatting with specific whitespace. If a test appears to fail incorrectly, check the Input and Expected columns in the results table before assuming your code is wrong.