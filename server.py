"""
Hirist MCP Server implementation using official FastMCP / MCPServer SDK.
Provides Tools, Resources, and Prompts for Hirist.tech.
"""
import os
import re
import time
import json
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from starlette.requests import Request
from starlette.responses import Response, JSONResponse, HTMLResponse

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except Exception:
    from mcp.server.fastmcp import FastMCP  # type: ignore

from hirist_mcp import client
from hirist_mcp.auth import (
    SESSION_STORE,
    clean_stale_sessions,
    current_session_id,
    current_session_token,
    current_session_phpsessid,
    current_session_resume_url,
    decode_jwt
)

# Initialize the FastMCP server
mcp = FastMCP(
    "hirist-mcp",
    instructions=(
        "Hirist MCP Server: Manage Hirist candidate profile, update key skills, "
        "search tech jobs, inspect job descriptions, submit applications, bookmark jobs, "
        "nudge recruiters via follow-ups, and optimize recruiter search visibility via activity pulse."
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
# TOOLS DEFINITIONS
# ---------------------------------------------------------------------------

@mcp.tool()
def validate_session(token: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate the current Hirist candidate session.
    Returns candidate seekerId, authentication status, and token details.
    """
    status, res = client.validate_session(token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def refresh_session_token(
    phpsessid: Optional[str] = None,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Refresh and renew the Hirist access token (HIRIST_CK1) using the session cookie (PHPSESSID).
    Automatically mints a new 30-day JWT token from Gladiator Auth.
    """
    new_token, psid = auth.refresh_hirist_token(phpsessid_override=phpsessid, token_override=token)
    if new_token:
        return {
            "status": "success",
            "message": "Hirist access token refreshed successfully.",
            "token_preview": f"{new_token[:25]}...{new_token[-15:]}"
        }
    return {
        "status": "error",
        "message": "Failed to refresh token. Please check that PHPSESSID cookie is valid."
    }


@mcp.tool()
def get_profile(token: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch the complete candidate profile from Hirist.
    Includes candidate name, email, phone, current designation, experience (years/months),
    current CTC, expected CTC, institute, graduation year, resume path, and visibility status.
    """
    status, res = client.get_profile(token=token)
    return {"status_code": status, "profile": res}


@mcp.tool()
def get_full_profile_v2(token: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch comprehensive structured profile data including personal details (pd),
    work experiences (we), educations (ed), IT skills/resume details (rd),
    and additional profile info (ai).
    """
    status, res = client.get_full_profile_v2(token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def update_personal_details(
    name: Optional[str] = None,
    current_designation: Optional[str] = None,
    current_organization: Optional[str] = None,
    exp_year: Optional[int] = None,
    exp_month: Optional[int] = None,
    current_ctc: Optional[str] = None,
    expected_ctc: Optional[str] = None,
    notice_period: Optional[Union[int, str]] = None,
    phone: Optional[Union[int, str]] = None,
    current_location: Optional[str] = None,
    linkedin: Optional[str] = None,
    career_objective: Optional[str] = None,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update candidate's personal and career details on Hirist.
    Args:
        name: Full name
        current_designation: Current job title / role (e.g. 'Senior Software Engineer')
        current_organization: Current company name
        exp_year: Total years of professional experience
        exp_month: Total months of experience (0-11)
        current_ctc: Current CTC in Lakhs (e.g. '15')
        expected_ctc: Expected CTC in Lakhs (e.g. '25')
        notice_period: Notice period in days (e.g. 15, 30, 60, 90)
        phone: Contact mobile number
        current_location: Current city location ID or name
        linkedin: LinkedIn profile URL
        career_objective: Short summary / objective
    """
    status, res = client.update_personal_details(
        name=name,
        current_designation=current_designation,
        current_organization=current_organization,
        exp_year=exp_year,
        exp_month=exp_month,
        current_ctc=current_ctc,
        expected_ctc=expected_ctc,
        notice_period=notice_period,
        phone=phone,
        current_location=current_location,
        linkedin=linkedin,
        career_objective=career_objective,
        token=token
    )
    return {"status_code": status, "result": res}


@mcp.tool()
def update_work_experience(
    experiences: List[Dict[str, Any]],
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update candidate's work experience history on Hirist.
    Args:
        experiences: List of employment records. Each dictionary accepts:
            - designation (str): Job title
            - organization (str): Company name
            - fromExpMonth (int): Start month (1-12)
            - fromExpYear (int): Start year (e.g. 2021)
            - toExpMonth (int): End month (1-12, or 0 if current)
            - toExpYear (int): End year (e.g. 2023, or 0 if current)
            - isCurrent (int): 1 if currently working, 0 otherwise
            - salary (int): Annual salary
            - description (str): Responsibilities and achievements
            - city (str): Job location city
    """
    status, res = client.update_work_experience(experiences=experiences, token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def update_education(
    educations: List[Dict[str, Any]],
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update candidate's education history on Hirist.
    Args:
        educations: List of education records. Each dictionary accepts:
            - institute (str): University, college, or school name
            - degree (str): Degree identifier or title (e.g. '8' for B.Tech/B.E.)
            - courseType (int): 1=Full Time, 2=Part Time, 3=Correspondence
            - batchFrom (int): Start year (e.g. 2018)
            - batchTo (int): Graduation year (e.g. 2021)
            - isPrimary (int): 1 if primary highest degree, 0 otherwise
            - specialization (str): Branch or specialization (e.g. 'Computer Science')
            - description (str): Additional notes or academic highlights
    """
    status, res = client.update_education(educations=educations, token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def update_additional_info(
    about: Optional[str] = None,
    github: Optional[str] = None,
    linkedin: Optional[str] = None,
    handle_team: Optional[bool] = None,
    career_break: Optional[bool] = None,
    role_and_responsibility: Optional[str] = None,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update additional profile details (About summary, GitHub URL, team handling, role & responsibility).
    Args:
        about: Professional profile summary / bio
        github: GitHub profile URL
        linkedin: LinkedIn profile URL
        handle_team: Whether candidate has team lead / management experience
        career_break: Whether candidate has had a career break
        role_and_responsibility: Key domain roles & responsibilities
    """
    status, res = client.update_additional_info(
        about=about,
        github=github,
        linkedin=linkedin,
        handle_team=handle_team,
        career_break=career_break,
        role_and_responsibility=role_and_responsibility,
        token=token
    )
    return {"status_code": status, "result": res}


@mcp.tool()
def get_key_skills(token: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch candidate's key skills list and tags from Hirist.
    """
    status, res = client.get_skills(token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def update_key_skills(skills: List[str], token: Optional[str] = None) -> Dict[str, Any]:
    """
    Update or replace candidate's key skills on Hirist.
    Args:
        skills: List of skill names (e.g. ['Python', 'FastAPI', 'Docker', 'PostgreSQL'])
    """
    status, res = client.update_skills(skills=skills, token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def get_cover_letter(token: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch candidate's default cover letter and application preferences.
    """
    status, res = client.get_cover_letter(token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def update_cover_letter(
    coverletter: str,
    include_coverletter: bool = True,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update candidate's default cover letter on Hirist.
    Args:
        coverletter: Full cover letter text
        include_coverletter: Whether to automatically attach cover letter when applying
    """
    status, res = client.update_cover_letter(
        coverletter=coverletter,
        include_coverletter=include_coverletter,
        token=token
    )
    return {"status_code": status, "result": res}


@mcp.tool()
def touch_profile_pulse(token: Optional[str] = None) -> Dict[str, Any]:
    """
    Touch candidate profile activity timestamp ('Active Today').
    This boosts recruiter visibility by signaling that the candidate is actively looking for opportunities today.
    """
    status, res = client.touch_profile_pulse(token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def get_job_feed(token: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch personalized tech job recommendations curated by Hirist for the candidate.
    """
    status, res = client.get_job_feed(token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def search_jobs(
    query: str,
    size: int = 20,
    page: int = 1,
    min_exp: Optional[int] = None,
    max_exp: Optional[int] = None,
    location: Optional[str] = None,
    category_id: Optional[Union[int, str]] = None,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search tech jobs on Hirist by keyword, experience, location, or category.
    Args:
        query: Search keywords (e.g. 'Python Developer', 'Full Stack', 'Backend')
        size: Number of jobs to return per page (default: 20)
        page: Page number (default: 1)
        min_exp: Minimum years of experience
        max_exp: Maximum years of experience
        location: City/location name
        category_id: Optional Hirist category ID
    """
    status, res = client.search_jobs(
        query=query,
        size=size,
        page=page,
        min_exp=min_exp,
        max_exp=max_exp,
        location=location,
        category_id=category_id,
        token=token
    )
    return {"status_code": status, "result": res}


@mcp.tool()
def get_job_details(job_id: Union[int, str], token: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch comprehensive details for a specific job on Hirist.
    Includes full Job Description (JD), required skills/tags, experience requirements,
    locations, recruiter profile, company metadata, and application status.
    Args:
        job_id: The Hirist job ID or job code (e.g. 1684278)
    """
    status, res = client.get_job_details(job_id=job_id, token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def get_job_assessment(job_id: Union[int, str], token: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch assessment / screening questions required for applying to a job.
    Args:
        job_id: The Hirist job ID
    """
    status, res = client.get_job_assessment(job_id=job_id, token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def apply_to_job(
    job_id: Union[int, str],
    coverletter: Optional[str] = None,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Apply to a job on Hirist.
    Args:
        job_id: The Hirist job ID to apply for
        coverletter: Optional custom cover letter for this specific application
    """
    status, res = client.apply_to_job(job_id=job_id, coverletter=coverletter, token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def save_job(job_id: Union[int, str], token: Optional[str] = None) -> Dict[str, Any]:
    """
    Save/bookmark a job on Hirist for later review.
    Args:
        job_id: The Hirist job ID
    """
    status, res = client.save_job(job_id=job_id, token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def unsave_job(job_id: Union[int, str], token: Optional[str] = None) -> Dict[str, Any]:
    """
    Remove a saved/bookmarked job on Hirist.
    Args:
        job_id: The Hirist job ID
    """
    status, res = client.unsave_job(job_id=job_id, token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def do_follow_up(job_id: Union[int, str], token: Optional[str] = None) -> Dict[str, Any]:
    """
    Send a follow-up nudge to the recruiter for an already applied job.
    Args:
        job_id: The Hirist job ID
    """
    status, res = client.do_follow_up(job_id=job_id, token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def get_applied_job_count(token: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch the total count of jobs applied to on Hirist.
    """
    status, res = client.get_applied_job_count(token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def get_pending_jobs_count(token: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch count of pending job assessments or actions.
    """
    status, res = client.get_pending_jobs_count(token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def get_user_settings(token: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch candidate notification and account settings on Hirist.
    """
    status, res = client.get_user_settings(token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def update_user_settings(settings: Dict[str, Any], token: Optional[str] = None) -> Dict[str, Any]:
    """
    Update candidate notification and account settings on Hirist.
    """
    status, res = client.update_user_settings(settings=settings, token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def get_blocked_companies(token: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch the list of employers blocked from seeing candidate profile.
    """
    status, res = client.get_blocked_companies(token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def block_or_unblock_company(
    company_id: Union[int, str],
    block: bool = True,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Block or unblock a company from viewing candidate profile.
    Args:
        company_id: Company ID or numeric identifier
        block: True to block, False to unblock
    """
    status, res = client.block_or_unblock_company(company_id=company_id, block=block, token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def suggest_companies(query: str, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Auto-suggest company names matching the given query string.
    """
    status, res = client.suggest_companies(query=query, token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def suggest_institutes(query: str, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Auto-suggest universities/colleges matching the given query string.
    """
    status, res = client.suggest_institutes(query=query, token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def download_resume(
    pdf_url: Optional[str] = None,
    max_pages: int = 10,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Download and extract plain text from candidate's PDF resume.
    If pdf_url is omitted, uses the URL configured via server parameters (?resume=) or profile.
    Args:
        pdf_url: Optional direct HTTP/HTTPS URL to download the candidate's PDF resume
        max_pages: Maximum number of PDF pages to extract (default: 10)
    """
    target_url = (pdf_url or "").strip()
    if not target_url:
        target_url = current_session_resume_url.get().strip()

    sess_id = current_session_id.get().strip()
    if not target_url and sess_id and sess_id in SESSION_STORE:
        target_url = SESSION_STORE[sess_id].get("resume_url", "").strip()

    if not target_url:
        # Check active resume media endpoint
        st_res, res_res = client.get_resume(token=token)
        if st_res == 200 and isinstance(res_res, dict):
            target_url = res_res.get("data", {}).get("textResume", "")

    if not target_url:
        # Fallback to candidate profile metadata
        status, profile_data = client.get_profile(token=token)
        if status == 200 and isinstance(profile_data, dict):
            resume_path = profile_data.get("resumePath")
            return {
                "status": "partial",
                "message": (
                    f"Candidate has resume '{resume_path}' on Hirist. "
                    "To extract full text, pass direct pdf_url or connect with ?resume=<url>."
                ),
                "profile_resume_path": resume_path,
                "profile_id": profile_data.get("id"),
                "profile_name": profile_data.get("name")
            }
        return {"error": "No resume URL provided or found in session."}

    import io
    import urllib.request
    try:
        req = urllib.request.Request(target_url, headers={"User-Agent": client.DEFAULT_USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            pdf_bytes = resp.read()

        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        num_pages = len(reader.pages)
        pages_to_read = min(num_pages, max_pages)

        extracted_text = []
        for i in range(pages_to_read):
            page_text = reader.pages[i].extract_text() or ""
            extracted_text.append(f"--- PAGE {i+1} ---\n{page_text.strip()}")

        full_text = "\n\n".join(extracted_text)
        return {
            "status": "success",
            "source_url": target_url,
            "total_pages": num_pages,
            "pages_extracted": pages_to_read,
            "resume_text": full_text
        }
    except Exception as e:
        return {"error": f"Failed to download or parse PDF: {str(e)}", "source_url": target_url}


@mcp.tool()
def get_resume(token: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch active resume document URL and metadata for the candidate.
    Returns the presigned S3 URL of the active resume.
    """
    status, res = client.get_resume(token=token)
    return {"status_code": status, "result": res}


@mcp.tool()
def upload_resume(
    file_path: str,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Upload a resume file (PDF or DOCX) to the candidate's Hirist account.
    Args:
        file_path: Absolute or relative local path to the resume document (e.g. '/path/to/resume.pdf')
    """
    status, res = client.upload_resume(file_path=file_path, token=token)
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
            log_level="info"
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
