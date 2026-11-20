# Hirist MCP Server

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP Specification](https://img.shields.io/badge/MCP-2024--11--05-brightgreen.svg)](https://modelcontextprotocol.io/)
[![FastMCP](https://img.shields.io/badge/FastMCP-Official%20SDK-orange.svg)](https://github.com/modelcontextprotocol/python-sdk)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-ready **Model Context Protocol (MCP)** server for **[Hirist.tech](https://www.hirist.tech)** (India's premier tech hiring platform, part of Info Edge / iimjobs). Enables AI assistants (Claude Web, Claude Desktop, Gemini, ChatGPT, Cursor, and custom agentic workflows) to seamlessly inspect candidate profiles, update key skills, search tech jobs, parse job descriptions, submit applications, nudge recruiters with follow-ups, and maintain active candidate search visibility.

---

## 🌟 Key Capabilities

- **Zero-Config Multi-Tenant Remote Deployment**: Securely connects to **Claude Web** (Custom Connectors) and **Gemini** without needing environment variables on the server. Simply pass your credentials directly in the connection URL (`?token=...`).
- **Complete Profile & Skills Management**: Fetch full candidate profiles, update key tech skills (`update_key_skills`), manage default cover letters (`update_cover_letter`), and inspect contact details.
- **Automated Recruiter Activity Pulse (`touch_profile_pulse`)**: Simulates candidate activity timestamps ("Active Today"), ranking candidate profiles higher in recruiter search results.
- **Smart Tech Job Search & Personalized Feed**:
  - `get_job_feed`: Fetch curated tech jobs tailored to your skills and preferences.
  - `search_jobs`: Full parametric job search by keywords, experience range, location, and tech category.
  - `get_job_details`: Full JD content, required tech stack tags, recruiter profiles, and application status.
- **Job Applications & Follow-Ups**:
  - `apply_to_job`: Apply directly to tech openings with custom cover letters.
  - `save_job` / `unsave_job`: Bookmark jobs for later analysis.
  - `do_follow_up`: Send follow-up nudges to recruiters for submitted applications.
- **Resume Extraction (`download_resume`)**: Parse and extract candidate resume text via PDF parsing (`pypdf`).
- **Employer Privacy & Settings**: Block competitor companies (`block_or_unblock_company`) and configure notification preferences.

---

## 🛠️ Complete Tools Catalog (23 Tools)

### 1. Profile & Skills Management
| Tool | Description |
| :--- | :--- |
| `validate_session` | Verify active Hirist session and retrieve candidate `seekerId`. |
| `get_profile` | Fetch complete candidate profile schema (experience, salary, institute, resume path). |
| `get_key_skills` | Fetch candidate key skills and tag identifiers. |
| `update_key_skills` | Update or replace candidate skills array (e.g. Python, Flutter, Docker). |
| `get_cover_letter` | Retrieve candidate default cover letter and application preferences. |
| `update_cover_letter` | Update default cover letter and auto-attachment preferences. |
| `touch_profile_pulse` | Touch activity timestamp to display "Active Today" in recruiter searches. |
| `download_resume` | Download and extract plain text from candidate's PDF resume. |

### 2. Job Search & Recommendations
| Tool | Description |
| :--- | :--- |
| `get_job_feed` | Retrieve candidate's personalized curated tech job feed. |
| `search_jobs` | Search jobs by keywords, experience, location, and category. |
| `get_job_details` | Fetch comprehensive JD, required tags, recruiter details, and status. |
| `get_applied_job_count` | Get total count of jobs applied to on Hirist. |
| `get_pending_jobs_count` | Get count of pending job assessments or actions. |

### 3. Applications & Recruiter Engagement
| Tool | Description |
| :--- | :--- |
| `apply_to_job` | Apply to a specific job opening with optional tailored cover letter. |
| `save_job` | Save/bookmark a job for later review. |
| `unsave_job` | Remove bookmark from a job. |
| `do_follow_up` | Send a recruiter follow-up nudge for an applied job. |

### 4. Settings, Privacy & Autosuggest
| Tool | Description |
| :--- | :--- |
| `get_user_settings` | Fetch email, push notification, and account preferences. |
| `update_user_settings` | Update notification and account settings. |
| `get_blocked_companies` | List companies blocked from viewing candidate profile. |
| `block_or_unblock_company` | Block or unblock a company from viewing candidate profile. |
| `suggest_companies` | Autosuggest company names matching query prefix. |
| `suggest_institutes` | Autosuggest college/university names matching query prefix. |

---

## 🚀 Quick Start & Connection Guide

### How to Retrieve Your `HIRIST_CK1` Cookie

1. Log in to your account on **[hirist.tech](https://www.hirist.tech)**.
2. Press `F12` (or `Cmd + Option + I` on macOS) to open Developer Tools.
3. Navigate to **Application** (Chrome) or **Storage** (Firefox) &rarr; **Cookies** &rarr; `https://www.hirist.tech`.
4. Copy the value of the `HIRIST_CK1` cookie (a JWT string starting with `eyJ...`).

---

### Connecting to Claude Web / Gemini Custom Connectors

In Claude Web or Gemini MCP connector setup, enter the HTTPS URL of your deployed server with your cookie appended:

```text
https://your-hirist-mcp.up.railway.app/sse?token=YOUR_HIRIST_CK1_COOKIE
```

#### Supported URL Query Parameters:
- `?token=<jwt>`: (Required) Your `HIRIST_CK1` cookie.
- `&phpsessid=<id>`: (Optional) Your `PHPSESSID` session cookie.
- `&resume=<url>`: (Optional) Direct HTTPS URL to your resume PDF for instant text extraction.

*(The server natively supports both **Streamable HTTP** `/mcp` and **Server-Sent Events** `/sse`, with dual-transport method routing to prevent HTTP 405 errors).*

---

### Connecting to Claude Desktop / Cursor

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hirist": {
      "command": "python",
      "args": ["-m", "hirist_mcp", "--transport", "stdio"],
      "env": {
        "HIRIST_CK1": "YOUR_HIRIST_CK1_COOKIE"
      }
    }
  }
}
```

---

## 🐳 Docker & Cloud Deployment

### Run with Docker

```bash
docker build -t hirist-mcp .
docker run -p 8000:8000 -e PORT=8000 hirist-mcp
```

### 1-Click Cloud Deployment (Railway / Render / Fly.io)

1. Push this repository to GitHub.
2. Link the repository to Railway or Render.
3. Set Start Command (optional, automatically inferred from `Dockerfile`):
   ```bash
   python -m hirist_mcp --transport sse --port ${PORT:-8000} --host 0.0.0.0
   ```
4. Access health probe at `https://<your-app>.up.railway.app/health`.

---

## 🧪 Running Automated Tests

```bash
python -m unittest discover hirist_mcp/tests
```

---

## 🔒 Security & Privacy

- **No Credential Storage**: Multi-tenant requests are held in transient memory context during the active SSE session and purged after inactivity.
- **Direct Microservice Communication**: All API calls communicate directly with `https://gladiator.hirist.tech` over TLS 1.3.

---

## 📄 License

MIT License. Designed and crafted for high-performance AI-assisted tech career growth.
