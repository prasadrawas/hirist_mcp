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

## 🛠️ Unified 6-Tool Architecture

The Hirist MCP server has been engineered into a high-performance **6-Tool Architecture**, reducing prompt context token consumption by **~80%** (from ~5,200 tokens down to ~900 tokens) while eliminating Gemini Web's modal permission queuing.

| Tool | Action Options / Capabilities | Description |
| :--- | :--- | :--- |
| **`manage_profile`** | `action`: `"get"`, `"update"`, `"pulse"`, `"get_resume"`, `"upload_resume"` | Complete candidate profile lifecycle: view profile, update specific sections (personal details, skills, experience, education, bio, cover letter), bump recruiter search visibility pulse, and manage resumes. |
| **`search_jobs`** | `query`, `location`, `min_exp`, `max_exp`, `category_id`, `page`, `size` | Discover tech openings. If query and filters are omitted, automatically returns your personalized **Job Feed**. Otherwise, executes full parametric search. |
| **`get_job_details`** | `job_ids`: `Union[int, List[int]]`, `include_assessment`: `bool` | Comprehensive inspection for single or multiple jobs. Returns full JD, skills tags, recruiter info, and automatically embeds screening questionnaire questions if required. |
| **`manage_job_pipeline`** | `action`: `"apply"`, `"save"`, `"unsave"`, `"follow_up"`, `"metrics"` | Complete application pipeline: submit applications (single or batch with safe 200ms spacing), bookmark/save jobs, un-bookmark, send recruiter follow-ups, and fetch application statistics. |
| **`manage_account`** | `action`: `"get_settings"`, `"update_settings"`, `"list_blocked"`, `"block_company"`, `"unblock_company"`, `"suggest"` | Account settings, employer privacy (blocking competitor companies from seeing your profile), and company/institute autosuggest autocomplete. |
| **`manage_session`** | `action`: `"validate"`, `"refresh"` | Candidate authentication verification and on-demand JWT token renewal via Gladiator Auth. |

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
