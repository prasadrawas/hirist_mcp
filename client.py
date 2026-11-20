"""
HTTP REST client for Hirist Microservice APIs (Gladiator Gateway).
"""
import json
import ssl
import urllib.request
import urllib.error
import urllib.parse
from typing import Tuple, Dict, Any, Optional, List, Union

from hirist_mcp.auth import build_cookie_header, resolve_credentials

GLADIATOR_BASE_URL = "https://gladiator.hirist.tech"
AUTH_VALIDATE_URL = f"{GLADIATOR_BASE_URL}/auth/validate"
USER_BASE_URL = f"{GLADIATOR_BASE_URL}/user"
JOB_BASE_URL = f"{GLADIATOR_BASE_URL}/job"

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Standard SSL context
_SSL_CTX = ssl.create_default_context()


def get_headers(
    token: str,
    phpsessid: str = "",
    content_type: Optional[str] = None,
    extra_headers: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """Generate standardized HTTP headers for Hirist API requests."""
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.hirist.tech",
        "Referer": "https://www.hirist.tech/",
        "Cache-Control": "no-cache"
    }
    cookie_header = build_cookie_header(token, phpsessid)
    if cookie_header:
        headers["Cookie"] = cookie_header
    if content_type:
        headers["Content-Type"] = content_type
    if extra_headers:
        headers.update(extra_headers)
    return headers


def execute_request(
    url: str,
    method: str = "GET",
    token: Optional[str] = None,
    phpsessid: Optional[str] = None,
    data: Optional[Union[Dict[str, Any], bytes, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    content_type: Optional[str] = None,
    extra_headers: Optional[Dict[str, str]] = None,
    timeout: int = 15
) -> Tuple[int, Dict[str, Any]]:
    """
    Execute an HTTP request against Hirist API and return (status_code, json_body).
    """
    resolved_token, resolved_phpsessid = resolve_credentials(token, phpsessid)

    if params:
        clean_params = {k: v for k, v in params.items() if v is not None}
        encoded_params = urllib.parse.urlencode(clean_params)
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{encoded_params}"

    body_bytes = None
    default_content_type = content_type

    if data is not None:
        if isinstance(data, dict):
            if default_content_type == "application/x-www-form-urlencoded":
                body_bytes = urllib.parse.urlencode(data).encode("utf-8")
            else:
                default_content_type = "application/json"
                body_bytes = json.dumps(data).encode("utf-8")
        elif isinstance(data, str):
            body_bytes = data.encode("utf-8")
        elif isinstance(data, bytes):
            body_bytes = data

    headers = get_headers(
        token=resolved_token,
        phpsessid=resolved_phpsessid,
        content_type=default_content_type,
        extra_headers=extra_headers
    )

    req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout) as resp:
            status_code = resp.status
            raw_response = resp.read()
            try:
                json_data = json.loads(raw_response.decode("utf-8"))
            except Exception:
                json_data = {"raw": raw_response.decode("utf-8", errors="ignore")}
            return status_code, json_data
    except urllib.error.HTTPError as e:
        status_code = e.code
        err_body = e.read()
        try:
            err_json = json.loads(err_body.decode("utf-8"))
        except Exception:
            err_json = {"error": err_body.decode("utf-8", errors="ignore"), "statusCode": status_code}
        return status_code, err_json
    except Exception as e:
        return 500, {"error": str(e), "statusCode": 500}


# ---------------------------------------------------------------------------
# CORE CLIENT METHODS
# ---------------------------------------------------------------------------

def validate_session(token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Validate current candidate session."""
    return execute_request(AUTH_VALIDATE_URL, method="GET", token=token)


def get_profile(token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Fetch complete candidate profile schema."""
    return execute_request(f"{USER_BASE_URL}/profile", method="GET", token=token, params={"apply": "true"})


def get_skills(token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Fetch candidate key skills list."""
    return execute_request(f"{USER_BASE_URL}/skills", method="GET", token=token)


def update_skills(skills: List[str], token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Update candidate skills array."""
    return execute_request(f"{USER_BASE_URL}/skills", method="POST", token=token, data={"skills": skills})


def get_cover_letter(token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Fetch candidate cover letter."""
    return execute_request(f"{USER_BASE_URL}/coverletter", method="GET", token=token)


def update_cover_letter(
    coverletter: str,
    include_coverletter: bool = True,
    token: Optional[str] = None
) -> Tuple[int, Dict[str, Any]]:
    """Update candidate cover letter."""
    data = {
        "coverletter": coverletter,
        "includeCoverletter": "1" if include_coverletter else "0"
    }
    return execute_request(
        f"{USER_BASE_URL}/coverletter",
        method="POST",
        token=token,
        data=data,
        content_type="application/x-www-form-urlencoded"
    )


def touch_profile_pulse(token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """
    Touch candidate profile activity timestamp.
    Signals recruiters that the candidate is active today.
    """
    data = {"opt": "true", "isUpdate": "true"}
    return execute_request(
        f"{USER_BASE_URL}/updatestamp",
        method="POST",
        token=token,
        data=data,
        content_type="application/x-www-form-urlencoded"
    )


def get_job_feed(token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Fetch personalized candidate job feed."""
    return execute_request(
        f"{JOB_BASE_URL}/jobfeed",
        method="GET",
        token=token,
        extra_headers={"version": "2"}
    )


def search_jobs(
    query: str,
    size: int = 20,
    page: int = 1,
    min_exp: Optional[int] = None,
    max_exp: Optional[int] = None,
    location: Optional[str] = None,
    category_id: Optional[Union[int, str]] = None,
    token: Optional[str] = None
) -> Tuple[int, Dict[str, Any]]:
    """Search jobs across keywords, category, experience, and location."""
    params: Dict[str, Any] = {
        "query": query,
        "size": size,
        "page": page
    }
    if min_exp is not None:
        params["minexp"] = min_exp
    if max_exp is not None:
        params["maxexp"] = max_exp
    if location:
        params["loc"] = location
    if category_id:
        params["category"] = category_id

    return execute_request(
        f"{JOB_BASE_URL}/search",
        method="GET",
        token=token,
        params=params,
        extra_headers={"version": "2"}
    )


def get_job_details(job_id: Union[int, str], token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Fetch comprehensive details for a specific job."""
    return execute_request(
        f"{JOB_BASE_URL}/detail",
        method="GET",
        token=token,
        params={"jobcode": str(job_id)}
    )


def apply_to_job(
    job_id: Union[int, str],
    coverletter: Optional[str] = None,
    token: Optional[str] = None
) -> Tuple[int, Dict[str, Any]]:
    """Apply to a job on Hirist."""
    payload: Dict[str, Any] = {}
    if coverletter is not None:
        payload["coverletter"] = coverletter
    return execute_request(
        f"{JOB_BASE_URL}/apply",
        method="POST",
        token=token,
        params={"jobcode": str(job_id)},
        data=payload
    )


def save_job(job_id: Union[int, str], token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Save/bookmark a job."""
    return execute_request(
        f"{JOB_BASE_URL}/save/",
        method="POST",
        token=token,
        params={"jobcode": str(job_id)},
        data={}
    )


def unsave_job(job_id: Union[int, str], token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Remove bookmark from a job."""
    return execute_request(
        f"{JOB_BASE_URL}/unsave/",
        method="POST",
        token=token,
        params={"jobcode": str(job_id)},
        data={}
    )


def do_follow_up(job_id: Union[int, str], token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Send follow-up nudge to recruiter for an applied job."""
    return execute_request(
        f"{JOB_BASE_URL}/followup",
        method="POST",
        token=token,
        params={"jobcode": str(job_id)},
        data={}
    )


def get_applied_job_count(token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Fetch applied job count statistics."""
    return execute_request(f"{JOB_BASE_URL}/applied/count/", method="GET", token=token)


def get_pending_jobs_count(token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Fetch pending jobs count."""
    return execute_request(f"{JOB_BASE_URL}/pending-jobs/count", method="GET", token=token)


def get_user_settings(token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Fetch notification, privacy, and account settings."""
    return execute_request(f"{USER_BASE_URL}/settings", method="GET", token=token, params={"version": "v2"})


def update_user_settings(settings: Dict[str, Any], token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Update candidate account/notification settings."""
    return execute_request(
        f"{USER_BASE_URL}/settings",
        method="POST",
        token=token,
        data=settings,
        content_type="application/x-www-form-urlencoded"
    )


def get_blocked_companies(token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Fetch list of blocked employers."""
    return execute_request(f"{USER_BASE_URL}/settings/blocked-companies", method="GET", token=token)


def block_or_unblock_company(
    company_id: Union[int, str],
    block: bool = True,
    token: Optional[str] = None
) -> Tuple[int, Dict[str, Any]]:
    """Block or unblock a company from viewing candidate profile."""
    data = {"companyId": str(company_id), "action": "block" if block else "unblock"}
    return execute_request(
        f"{USER_BASE_URL}/settings/blocked-companies",
        method="POST",
        token=token,
        data=data,
        content_type="application/x-www-form-urlencoded"
    )


def suggest_companies(query: str, token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Auto-suggest companies by name."""
    clean_q = urllib.parse.quote(query).replace("%20", "%2520")
    return execute_request(f"{USER_BASE_URL}/company/autosuggest?name={clean_q}", method="GET", token=token)


def suggest_institutes(query: str, token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Auto-suggest colleges/universities."""
    clean_q = urllib.parse.quote(query)
    return execute_request(f"{USER_BASE_URL}/suggest/institute?astext={clean_q}&limit=50", method="GET", token=token)
