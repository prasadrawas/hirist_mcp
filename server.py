"""
Hirist MCP Server implementation using official FastMCP / MCPServer SDK.
Provides Tools, Resources, and Prompts for Hirist.tech.
"""
import os
import re
import time
import urllib.parse
from typing import Dict, Any, List, Optional, Union, Literal

from starlette.requests import Request
from starlette.responses import Response, JSONResponse, HTMLResponse

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except Exception:
    from mcp.server.fastmcp import FastMCP  # type: ignore

from hirist_mcp import client, auth
from hirist_mcp.auth import (
    SESSION_STORE,
    clean_stale_sessions,
    current_session_id,
    current_session_token,
    current_session_phpsessid,
    current_session_resume_url,
)

# Initialize the FastMCP server with unified 6-tool architecture instructions
mcp = FastMCP(
    "hirist-mcp",
    instructions=(
        "Hirist MCP Server (Unified 6-Tool Architecture): Production MCP server for Hirist.tech candidate profile "
        "management, smart tech job discovery, applications, recruiter follow-ups, and employer privacy.\n\n"
        "CORE TOOLS (Total 6 Tools):\n"
        "1. `manage_profile`: Candidate profile reads, section updates (skills, bio, experience, education), resume management, and recruiter activity pulse.\n"
        "2. `search_jobs`: Search tech jobs by keywords/location or retrieve your personalized Job Feed (when no query is given).\n"
        "3. `get_job_details`: Inspect single or multiple job descriptions, tech stack tags, recruiter profiles, and screening questions.\n"
        "4. `manage_job_pipeline`: Apply to jobs (single or batch), bookmark/un-bookmark jobs, follow up with recruiters, and fetch application statistics.\n"
        "5. `manage_account`: Employer privacy (blocking competitor companies), notification settings, and company/institute autosuggest.\n"
        "6. `manage_session`: Verify active session authentication or renew session token."
    )
)


# ---------------------------------------------------------------------------
# CUSTOM HTTP ROUTES (Health, Landing Page)
# ---------------------------------------------------------------------------

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> Response:
    """Public health check endpoint for monitoring and cloud container platforms."""
    return JSONResponse({
        "status": "healthy",
        "service": "hirist-mcp",
        "version": "1.0.0"
    })


@mcp.custom_route("/", methods=["GET", "POST", "OPTIONS", "HEAD"])
async def index_route(request: Request) -> Response:
    """Root info page or transparent redirect to /sse when called with token or SSE headers."""
    if request.method == "OPTIONS":
        return Response(status_code=200)

    # If request contains token query parameter or requests SSE stream, redirect to /sse
    if (
        "token" in request.query_params
        or "ck" in request.query_params
        or "hirist_ck1" in request.query_params
        or "text/event-stream" in request.headers.get("accept", "")
    ):
        from starlette.responses import RedirectResponse
        target_url = "/sse"
        if request.scope.get("query_string"):
            target_url += "?" + request.scope["query_string"].decode("utf-8")
        return RedirectResponse(url=target_url, status_code=307)

    host = request.headers.get("host", "localhost:8000")
    scheme = "https" if request.headers.get("x-forwarded-proto") == "https" else "http"
    base_url = f"{scheme}://{host}"
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Hirist MCP Server</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 820px; margin: 40px auto; padding: 20px; line-height: 1.6; color: #2d3748; }}
        h1 {{ color: #1a202c; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; margin-top: 10px; }}
        code {{ background: #edf2f7; padding: 3px 6px; border-radius: 4px; font-family: monospace; font-size: 0.9em; color: #d53f8c; }}
        pre {{ background: #1a202c; color: #f7fafc; padding: 16px; border-radius: 8px; overflow-x: auto; }}
        pre code {{ background: none; color: inherit; padding: 0; }}
        .badge {{ display: inline-block; background: #38a169; color: white; padding: 4px 12px; border-radius: 12px; font-weight: bold; font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.5px; }}
        .card {{ background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 22px; margin-top: 24px; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 8px; }}
        a {{ color: #3182ce; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <span class="badge">Running</span>
    <h1>Hirist MCP Server</h1>
    <p>Production Model Context Protocol (MCP) server providing automated tools for Hirist.tech candidate profile management, recruiter visibility optimization, and smart tech job applications.</p>
    
    <div class="card">
        <h3>Connect to Claude Web / Claude Desktop / Gemini / Cursor</h3>
        <p>Add this server to your MCP configuration with your personalized SSE or Streamable HTTP URL:</p>
        <pre><code>{{
  "mcpServers": {{
    "hirist": {{
      "url": "{base_url}/sse?token=YOUR_HIRIST_CK1_COOKIE"
    }}
  }}
}}</code></pre>
        <h4>URL Parameters:</h4>
        <ul>
            <li><code>?token=&lt;jwt&gt;</code>: (Required) Your <code>HIRIST_CK1</code> or <code>hirist_seeker_enc</code> cookie from hirist.tech.</li>
            <li><code>&amp;phpsessid=&lt;id&gt;</code>: (Optional) Your <code>PHPSESSID</code> session cookie.</li>
            <li><code>&amp;resume=&lt;url&gt;</code>: (Optional) HTTP/HTTPS URL to your candidate PDF resume.</li>
        </ul>
        <p>Custom HTTP headers are also supported: <code>X-Hirist-Token</code>, <code>X-Hirist-CK1</code>, <code>X-PHPSESSID</code>.</p>
    </div>

    <div class="card">
        <h3>How to get your <code>HIRIST_CK1</code> cookie:</h3>
        <ol>
            <li>Log in to <a href="https://www.hirist.tech" target="_blank">hirist.tech</a> in your browser.</li>
            <li>Open Developer Tools (F12 or Cmd+Option+I) &rarr; <strong>Storage</strong> / <strong>Application</strong> &rarr; <strong>Cookies</strong> &rarr; <code>https://www.hirist.tech</code>.</li>
            <li>Copy the value of the <code>HIRIST_CK1</code> cookie.</li>
        </ol>
    </div>

    <div class="card">
        <h3>Server Status &amp; Diagnostics</h3>
        <p><a href="/health"><code>/health</code></a> &mdash; Health probe endpoint for container orchestrators and uptime checks.</p>
    </div>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


# ---------------------------------------------------------------------------
# TOOLS DEFINITIONS (Consolidated 6-Tool Architecture)
# ---------------------------------------------------------------------------

@mcp.tool()
def manage_profile(
    action: Literal["get", "update", "pulse", "get_resume", "upload_resume"] = "get",
    personal: Optional[Dict[str, Any]] = None,
    skills: Optional[List[str]] = None,
    experience: Optional[List[Dict[str, Any]]] = None,
    education: Optional[List[Dict[str, Any]]] = None,
    additional_info: Optional[Dict[str, Any]] = None,
    cover_letter: Optional[str] = None,
    file_path: Optional[str] = None,
    extract_text: bool = False,
    max_pages: int = 10,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Candidate profile management: view profile, update career details/skills,
    boost recruiter search ranking via activity pulse, and manage resumes.
    Args:
        action: 'get' (view full profile), 'update' (modify provided fields), 'pulse' (bump recruiter activity timestamp),
                'get_resume' (fetch resume metadata and optionally extracted text), 'upload_resume' (upload local PDF/DOCX)
        personal: Personal details to update (designation, company, exp_year, exp_month, current_ctc, expected_ctc,
                  notice_period, location, phone, linkedin, name, etc.)
        skills: List of key skill strings (e.g. ['Python', 'FastAPI', 'Docker'])
        experience: List of work experience records to add/update
        education: List of education records to add/update
        additional_info: Additional profile fields (about summary, github, linkedin, handle_team, career_break)
        cover_letter: Default cover letter text
        file_path: Local filesystem path to PDF/DOCX resume file (required for 'upload_resume')
        extract_text: If True when calling 'get_resume', downloads and parses resume PDF text
        max_pages: Maximum pages to extract when extract_text=True (default: 10)
    """
    if action == "pulse":
        status, res = client.touch_profile_pulse(token=token)
        return {"status_code": status, "result": res}

    elif action == "upload_resume":
        if not file_path:
            return {"status_code": 400, "error": "file_path is required for upload_resume"}
        status, res = client.upload_resume(file_path=file_path, token=token)
        return {"status_code": status, "result": res}

    elif action == "get_resume":
        if extract_text:
            text_res = client.download_resume_text(max_pages=max_pages, token=token)
            return {"status_code": 200 if text_res.get("status") == "success" or "resume_text" in text_res else 400, "result": text_res}
        status, res = client.get_resume(token=token)
        return {"status_code": status, "result": res}

    elif action == "update":
        updates_performed = []
        errors = []

        if personal:
            st, res = client.update_personal_details(**personal, token=token)
            if st == 200:
                updates_performed.append("personal_details")
            else:
                errors.append({"section": "personal_details", "error": res})

        if skills is not None:
            st, res = client.update_skills(skills=skills, token=token)
            if st == 200:
                updates_performed.append("skills")
            else:
                errors.append({"section": "skills", "error": res})

        if experience is not None:
            st, res = client.update_work_experience(experience_list=experience, token=token)
            if st == 200:
                updates_performed.append("work_experience")
            else:
                errors.append({"section": "work_experience", "error": res})

        if education is not None:
            st, res = client.update_education(education_list=education, token=token)
            if st == 200:
                updates_performed.append("education")
            else:
                errors.append({"section": "education", "error": res})

        if additional_info:
            st, res = client.update_additional_info(**additional_info, token=token)
            if st == 200:
                updates_performed.append("additional_info")
            else:
                errors.append({"section": "additional_info", "error": res})

        if cover_letter is not None:
            st, res = client.update_cover_letter(coverletter=cover_letter, token=token)
            if st == 200:
                updates_performed.append("cover_letter")
            else:
                errors.append({"section": "cover_letter", "error": res})

        return {
            "status_code": 200 if not errors else 207,
            "status": "success" if not errors else "partial_success",
            "updated_sections": updates_performed,
            "errors": errors if errors else None
        }

    else:  # "get"
        status, profile_data = client.get_profile(token=token)
        if status != 200 or not profile_data:
            status, profile_data = client.get_full_profile_v2(token=token)
        st_skills, skills_res = client.get_skills(token=token)
        st_resume, resume_res = client.get_resume(token=token)

        unified_profile = {
            "profile": profile_data if status == 200 else None,
            "skills": skills_res if st_skills == 200 else None,
            "resume": resume_res if st_resume == 200 else None
        }
        return {"status_code": 200, "result": unified_profile}


@mcp.tool()
def search_jobs(
    query: Optional[str] = None,
    location: Optional[str] = None,
    min_exp: Optional[int] = None,
    max_exp: Optional[int] = None,
    category_id: Optional[Union[int, str]] = None,
    page: int = 1,
    size: int = 20,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search tech jobs on Hirist or retrieve your personalized curated job feed.
    If query and all filters are omitted, automatically returns your curated Job Feed.
    Args:
        query: Search keywords (e.g. 'Senior Python Developer', 'Full Stack', 'Machine Learning')
        location: City or location filter (e.g. 'Bangalore', 'Remote', 'Mumbai', 'Pune', 'Delhi')
        min_exp: Minimum years of experience (e.g. 3)
        max_exp: Maximum years of experience (e.g. 8)
        category_id: Optional job category ID
        page: Page number (default: 1)
        size: Number of jobs to return (default: 20)
    """
    if not any([query, location, min_exp is not None, max_exp is not None, category_id]):
        status, res = client.get_job_feed(token=token)
        return {"status_code": status, "mode": "feed", "result": res}

    status, res = client.search_jobs(
        query=query or "",
        min_exp=min_exp,
        max_exp=max_exp,
        location=location,
        category_id=category_id,
        page=page,
        size=size,
        token=token
    )
    return {"status_code": status, "mode": "search", "result": res}


@mcp.tool()
def get_job_details(
    job_ids: Union[int, str, List[Union[int, str]]],
    include_assessment: bool = True,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch comprehensive job details and requirements for one or more jobs.
    Accepts a single job ID (e.g. 1684702) or a list of job IDs (e.g. [1684702, 1684614]).
    Includes full JD, tech stack tags, experience requirements, recruiter profile, and status.
    Args:
        job_ids: Single numeric job ID or list of numeric job IDs
        include_assessment: If True, automatically fetches screening questions if required by the job
    """
    if isinstance(job_ids, list):
        clean_ids = [int(j) if str(j).isdigit() else str(j) for j in job_ids]
        status, res = client.batch_get_job_details(job_ids=clean_ids, token=token)
        return {"status_code": status, "result": res}

    jid = int(job_ids) if str(job_ids).isdigit() else str(job_ids)
    status, res = client.get_job_details(job_id=jid, token=token)

    assessment_data = None
    if include_assessment and status == 200:
        st_a, res_a = client.get_job_assessment(job_id=jid, token=token)
        if st_a == 200 and res_a:
            assessment_data = res_a

    return {
        "status_code": status,
        "job_id": jid,
        "details": res,
        "assessment": assessment_data
    }


@mcp.tool()
def manage_job_pipeline(
    action: Literal["apply", "save", "unsave", "follow_up", "metrics"] = "apply",
    job_ids: Optional[Union[int, str, List[Union[int, str]]]] = None,
    coverletter: Optional[str] = None,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Manage job applications, saved bookmarks, recruiter follow-ups, and application statistics.
    Accepts single or multiple job IDs uniformly with safe server-side rate limiting.
    Args:
        action: 'apply' (submit application), 'save' (bookmark job), 'unsave' (remove bookmark),
                'follow_up' (nudge recruiter for applied job), 'metrics' (total applied & pending counts)
        job_ids: Single job ID or list of job IDs (required for apply, save, unsave, follow_up)
        coverletter: Optional custom cover letter (used when action='apply')
    """
    if action == "metrics":
        st_app, res_app = client.get_applied_job_count(token=token)
        st_pend, res_pend = client.get_pending_jobs_count(token=token)
        return {
            "status_code": 200,
            "metrics": {
                "applied_jobs_count": res_app.get("count", 0) if isinstance(res_app, dict) else res_app,
                "pending_jobs_count": res_pend.get("count", 0) if isinstance(res_pend, dict) else res_pend
            }
        }

    if not job_ids:
        return {"status_code": 400, "error": f"job_ids parameter is required for action='{action}'"}

    id_list = job_ids if isinstance(job_ids, list) else [job_ids]
    clean_ids = [int(j) if str(j).isdigit() else str(j) for j in id_list]

    if action == "apply":
        if len(clean_ids) == 1:
            st, res = client.apply_to_job(job_id=clean_ids[0], coverletter=coverletter, token=token)
            return {"status_code": st, "result": res}
        st, res = client.batch_apply_jobs(job_ids=clean_ids, coverletter=coverletter, token=token)
        return {"status_code": st, "result": res}

    elif action == "save":
        if len(clean_ids) == 1:
            st, res = client.save_job(job_id=clean_ids[0], token=token)
            return {"status_code": st, "result": res}
        st, res = client.batch_save_jobs(job_ids=clean_ids, token=token)
        return {"status_code": st, "result": res}

    elif action == "unsave":
        results = []
        for jid in clean_ids:
            st, res = client.unsave_job(job_id=jid, token=token)
            results.append({"job_id": jid, "status_code": st, "result": res})
        return {"status_code": 200, "result": results}

    elif action == "follow_up":
        if len(clean_ids) == 1:
            st, res = client.do_follow_up(job_id=clean_ids[0], token=token)
            return {"status_code": st, "result": res}
        st, res = client.batch_follow_up(job_ids=clean_ids, token=token)
        return {"status_code": st, "result": res}

    return {"status_code": 400, "error": f"Unknown action: '{action}'"}


@mcp.tool()
def manage_account(
    action: Literal["get_settings", "update_settings", "list_blocked", "block_company", "unblock_company", "suggest"] = "get_settings",
    company_id: Optional[Union[int, str]] = None,
    settings: Optional[Dict[str, Any]] = None,
    query: Optional[str] = None,
    category: Optional[Literal["company", "institute"]] = "company",
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Manage account settings, employer privacy (blocking competitors), and autocomplete suggestions.
    Args:
        action: 'get_settings' (view preferences), 'update_settings' (update preferences),
                'list_blocked' (view blocked companies), 'block_company' (block employer ID),
                'unblock_company' (unblock employer ID), 'suggest' (autocomplete company/institute)
        company_id: Company ID to block or unblock
        settings: Settings dictionary to update (when action='update_settings')
        query: Search string for autocompletion (when action='suggest')
        category: 'company' or 'institute' (when action='suggest')
    """
    if action == "get_settings":
        st, res = client.get_user_settings(token=token)
        return {"status_code": st, "result": res}

    elif action == "update_settings":
        if not settings:
            return {"status_code": 400, "error": "settings dictionary is required for update_settings"}
        st, res = client.update_user_settings(settings=settings, token=token)
        return {"status_code": st, "result": res}

    elif action == "list_blocked":
        st, res = client.get_blocked_companies(token=token)
        return {"status_code": st, "result": res}

    elif action in ("block_company", "unblock_company"):
        if not company_id:
            return {"status_code": 400, "error": f"company_id is required for {action}"}
        st, res = client.block_or_unblock_company(
            company_id=company_id,
            block=(action == "block_company"),
            token=token
        )
        return {"status_code": st, "result": res}

    elif action == "suggest":
        if not query:
            return {"status_code": 400, "error": "query string is required for suggest"}
        if category == "institute":
            st, res = client.suggest_institutes(query=query, token=token)
        else:
            st, res = client.suggest_companies(query=query, token=token)
        return {"status_code": st, "result": res}

    return {"status_code": 400, "error": f"Unknown action: '{action}'"}


@mcp.tool()
def manage_session(
    action: Literal["validate", "refresh"] = "validate",
    token: Optional[str] = None,
    phpsessid: Optional[str] = None
) -> Dict[str, Any]:
    """
    Session verification and token maintenance for Hirist.
    Args:
        action: 'validate' (check authentication & get candidate seekerId),
                'refresh' (manually renew 30-day JWT using PHPSESSID)
        token: Optional override token
        phpsessid: Optional override PHPSESSID
    """
    if action == "refresh":
        new_token, psess = auth.refresh_hirist_token(phpsessid_override=phpsessid, token_override=token)
        if new_token:
            return {
                "status_code": 200,
                "status": "success",
                "message": "Token refreshed successfully",
                "token": new_token,
                "phpsessid": psess
            }
        return {
            "status_code": 400,
            "status": "failed",
            "message": "Failed to refresh token. Check if PHPSESSID is valid."
        }

    status, res = client.validate_session(token=token)
    return {"status_code": status, "result": res}


# ---------------------------------------------------------------------------
# MULTI-TENANT SESSION MIDDLEWARE & PROTOCOL HANDLER
# ---------------------------------------------------------------------------

class MultiTenantSessionMiddleware:
    """
    ASGI middleware intercepting incoming requests to extract tenant credentials:
    1. Query parameters: ?token=, ?ck=, ?hirist_ck1=, ?phpsessid=, ?resume=
    2. HTTP Headers: X-Hirist-Token, X-Hirist-CK1, X-PHPSESSID, X-Resume-Url
    3. SSE / Streamable HTTP session_id correlation
    """
    def __init__(self, app_target: Any):
        self.app_target = app_target

    async def __call__(self, scope: Dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            clean_stale_sessions()
            query_string = scope.get("query_string", b"").decode("utf-8", errors="ignore")
            params = urllib.parse.parse_qs(query_string)

            headers = {k.decode("utf-8").lower(): v.decode("utf-8") for k, v in scope.get("headers", [])}

            token = ""
            for param_key in ["token", "ck", "hirist_ck1", "hirist_seeker_enc"]:
                if param_key in params and params[param_key]:
                    token = params[param_key][0].strip()
                    break

            if not token:
                token = (
                    headers.get("x-hirist-token")
                    or headers.get("x-hirist-ck1")
                    or headers.get("x-token")
                    or ""
                ).strip()

            phpsessid = ""
            if "phpsessid" in params and params["phpsessid"]:
                phpsessid = params["phpsessid"][0].strip()
            if not phpsessid:
                phpsessid = headers.get("x-phpsessid", "").strip()

            resume_url = ""
            for r_key in ["resume", "resume_url", "pdf"]:
                if r_key in params and params[r_key]:
                    resume_url = params[r_key][0].strip()
                    break
            if not resume_url:
                resume_url = headers.get("x-resume-url", "").strip()

            # Session ID resolution
            session_id = ""
            if "session_id" in params and params["session_id"]:
                session_id = params["session_id"][0].replace("-", "").strip()
            if not session_id and "mcp-session-id" in headers:
                session_id = headers["mcp-session-id"].replace("-", "").strip()

            if session_id:
                current_session_id.set(session_id)
                if token or phpsessid or resume_url:
                    if session_id not in SESSION_STORE:
                        SESSION_STORE[session_id] = {
                            "token": token,
                            "phpsessid": phpsessid,
                            "resume_url": resume_url,
                            "created_at": time.time(),
                            "last_seen": time.time()
                        }
                    else:
                        if token:
                            SESSION_STORE[session_id]["token"] = token
                        if phpsessid:
                            SESSION_STORE[session_id]["phpsessid"] = phpsessid
                        if resume_url:
                            SESSION_STORE[session_id]["resume_url"] = resume_url
                        SESSION_STORE[session_id]["last_seen"] = time.time()
                elif session_id in SESSION_STORE:
                    SESSION_STORE[session_id]["last_seen"] = time.time()
                    token = SESSION_STORE[session_id].get("token", "")
                    phpsessid = SESSION_STORE[session_id].get("phpsessid", "")
                    resume_url = SESSION_STORE[session_id].get("resume_url", "")

            if token:
                current_session_token.set(token)
            if phpsessid:
                current_session_phpsessid.set(phpsessid)
            if resume_url:
                current_session_resume_url.set(resume_url)

            async def custom_send(message: Dict[str, Any]) -> None:
                if message.get("type") == "http.response.start":
                    headers_dict = dict(message.get("headers", []))
                    if b"mcp-session-id" in headers_dict and token:
                        sess_id = headers_dict[b"mcp-session-id"].decode("utf-8").replace("-", "")
                        SESSION_STORE[sess_id] = {
                            "token": token,
                            "phpsessid": phpsessid,
                            "resume_url": resume_url,
                            "created_at": time.time(),
                            "last_seen": time.time()
                        }
                elif message.get("type") == "http.response.body":
                    body_bytes = message.get("body", b"")
                    if b"session_id=" in body_bytes and token:
                        m = re.search(r"session_id=([a-f0-9\-]+)", body_bytes.decode("utf-8", errors="ignore"))
                        if m:
                            sess_id = m.group(1).replace("-", "")
                            SESSION_STORE[sess_id] = {
                                "token": token,
                                "phpsessid": phpsessid,
                                "resume_url": resume_url,
                                "created_at": time.time(),
                                "last_seen": time.time()
                            }
                await send(message)

            await self.app_target(scope, receive, custom_send)
            return

        await self.app_target(scope, receive, send)


def get_app() -> Any:
    """Return unified Starlette app supporting both Streamable HTTP (/mcp) and SSE (/sse), with full CORS."""
    from starlette.applications import Starlette
    from starlette.middleware.cors import CORSMiddleware
    from starlette.routing import Route
    from mcp.server.transport_security import TransportSecuritySettings

    sec = TransportSecuritySettings(enable_dns_rebinding_protection=False)
    sse_subapp = mcp.sse_app(transport_security=sec)
    http_subapp = mcp.streamable_http_app(streamable_http_path="/mcp", transport_security=sec)

    http_handler = None
    for r in http_subapp.routes:
        if getattr(r, "path", "") == "/mcp":
            http_handler = r.endpoint
            break

    sse_handler = None
    for r in sse_subapp.routes:
        if getattr(r, "path", "") == "/sse":
            sse_handler = r.endpoint
            break

    routes = [
        Route("/sse", endpoint=sse_handler, methods=["GET", "HEAD"]),
        Route("/sse", endpoint=http_handler, methods=["POST"]),
        Route("/mcp", endpoint=http_handler, methods=["GET", "POST", "HEAD"]),
        Route("/", endpoint=http_handler, methods=["POST"]),
        *[r for r in sse_subapp.routes if getattr(r, "path", "") not in ("/sse", "/mcp")],
    ]

    unified_app = Starlette(
        routes=routes,
        lifespan=http_subapp.router.lifespan_context
    )

    wrapped_session_app = MultiTenantSessionMiddleware(unified_app)
    return CORSMiddleware(
        wrapped_session_app,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )


app = get_app()


# ---------------------------------------------------------------------------
# SERVER RUNNER
# ---------------------------------------------------------------------------

def run_server(transport: str = "stdio", port: Optional[int] = None, host: str = "0.0.0.0") -> None:
    """Run the FastMCP server in either stdio, sse, or streamable-http mode."""
    if port is None:
        port = int(os.getenv("PORT", 8000))

    if transport == "sse":
        import uvicorn
        import anyio
        print(f"Starting hirist-mcp in SSE mode on http://{host}:{port} ...")
        app_instance = get_app()
        config = uvicorn.Config(
            app_instance,
            host=host,
            port=port,
            log_level="info",
            timeout_keep_alive=65
        )
        server = uvicorn.Server(config)
        anyio.run(server.serve)
    elif transport == "streamable-http":
        print(f"Starting hirist-mcp in streamable-http mode on http://{host}:{port} ...")
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="hirist-mcp: Model Context Protocol Server for Hirist.tech")
    parser.add_argument("--transport", choices=["stdio", "sse", "streamable-http"], default="stdio", help="Transport mode")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 8000)), help="Port for SSE mode (default: PORT env or 8000)")
    parser.add_argument("--host", default="0.0.0.0", help="Host for SSE mode")
    args = parser.parse_args()

    run_server(transport=args.transport, port=args.port, host=args.host)
