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

SCHEMA_FIELD_MAP = {
    "pd": {
        "picPath": "a1", "name": "a2", "gender": "a3", "dob": "a4",
        "currentLocation": "a5", "preferredLocations": "a6", "phone": "a7",
        "countryCode": "a8", "industry": "a9", "careerObjective": "i3",
        "functionalArea": "b1", "noticePeriod": "b2", "expYear": "b3",
        "expMonth": "b4", "currentCtc": "b5", "currentSalary": "h9",
        "confidential": "b6", "expectedCtc": "b7", "expectedSalary": "i1",
        "negotiable": "b8", "resumePath": "b9", "currentOrganization": "c2",
        "fresher": "j6", "linkedin": "j7", "currentDesignation": "j2",
        "skills": "s1"
    },
    "we": {
        "designation": "c1", "organization": "c2", "fromExpMonth": "c3",
        "fromExpYear": "c4", "toExpMonth": "c5", "toExpYear": "c6",
        "isCurrent": "c7", "salary": "c8", "wantToRejoin": "g7",
        "description": "i4", "city": "i5"
    },
    "ed": {
        "institute": "c9", "degree": "d1", "courseType": "d2",
        "batchFrom": "d3", "batchTo": "d4", "isPrimary": "d5",
        "specialization": "j3", "description": "i6"
    },
    "ai": {
        "about": "e7", "handleTeam": "f2", "github": "k2",
        "linkedin": "h6", "facebook": "h7", "twitter": "h8",
        "maritalStatus": "f9", "careerBreak": "g3", "roleAndResponsibility": "l5"
    },
    "co": {
        "course": "d6", "institute": "d7", "fromExpYear": "e1",
        "toExpYear": "e3", "description": "j5"
    }
}


def validate_session(token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Validate current candidate session."""
    return execute_request(AUTH_VALIDATE_URL, method="GET", token=token)


def get_profile(token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Fetch complete candidate profile schema."""
    return execute_request(f"{USER_BASE_URL}/profile", method="GET", token=token, params={"apply": "true"})


def get_full_profile_v2(token: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Fetch structured multi-section profile with all sections (pd, we, ed, rd, ai, atr)."""
    return execute_request(f"{USER_BASE_URL}/profile/v2", method="GET", token=token, params={"fields": "11111111"})


def update_profile_section(
    section: str,
    payload_data: Dict[str, Any],
    token: Optional[str] = None
) -> Tuple[int, Dict[str, Any]]:
    """
    Update a profile section (pd, we, ed, ai, co) using Hirist's schema-validated mapping.
    Automatically generates infoString with the mapped field keys.
    """
    field_map = SCHEMA_FIELD_MAP.get(section, {})
    keys_present = [field_map[k] for k in payload_data if k in field_map]
    info_string = "".join(keys_present) if keys_present else "default"

    body: Dict[str, Any] = dict(payload_data)
    body["infoString"] = info_string
    body["requiredString"] = ""

    return execute_request(
        f"{USER_BASE_URL}/profile/v2",
        method="POST",
        token=token,
        data={section: body}
    )


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
) -> Tuple[int, Dict[str, Any]]:
    """Update candidate personal & career details."""
    data: Dict[str, Any] = {}
    if name is not None:
        data["name"] = name
    if current_designation is not None:
        data["currentDesignation"] = current_designation
    if current_organization is not None:
        data["currentOrganization"] = current_organization
    if exp_year is not None:
        data["expYear"] = exp_year
    if exp_month is not None:
        data["expMonth"] = exp_month
    if current_ctc is not None:
        data["currentCtc"] = str(current_ctc)
    if expected_ctc is not None:
        data["expectedCtc"] = str(expected_ctc)
    if notice_period is not None:
        data["noticePeriod"] = str(notice_period)
    if phone is not None:
        data["phone"] = int(phone) if str(phone).isdigit() else phone
    if current_location is not None:
        data["currentLocation"] = str(current_location)
    if linkedin is not None:
        data["linkedin"] = linkedin
    if career_objective is not None:
        data["careerObjective"] = career_objective

    return update_profile_section("pd", data, token=token)


def update_work_experience(
    experiences: List[Dict[str, Any]],
    token: Optional[str] = None
) -> Tuple[int, Dict[str, Any]]:
    """
    Update work experience history.
    Each item can contain: designation, organization, fromExpMonth, fromExpYear, toExpMonth, toExpYear, isCurrent, salary, description, city.
    """
    field_map = SCHEMA_FIELD_MAP.get("we", {})
    all_keys = set()
    formatted_list = []
    for exp in experiences:
        for k in exp:
            if k in field_map:
                all_keys.add(field_map[k])
        formatted_list.append(exp)

    return execute_request(
        f"{USER_BASE_URL}/profile/v2",
        method="POST",
        token=token,
        data={
            "we": formatted_list,
            "infoString": "".join(sorted(all_keys)),
            "requiredString": ""
        }
    )


def update_education(
    educations: List[Dict[str, Any]],
    token: Optional[str] = None
) -> Tuple[int, Dict[str, Any]]:
    """
    Update education history.
    Each item can contain: institute, degree, courseType (1=Full-time, 2=Part-time, 3=Correspondence), batchFrom, batchTo, specialization, description.
    """
    field_map = SCHEMA_FIELD_MAP.get("ed", {})
    all_keys = set()
    formatted_list = []
    for edu in educations:
        for k in edu:
            if k in field_map:
                all_keys.add(field_map[k])
        formatted_list.append(edu)

    return execute_request(
        f"{USER_BASE_URL}/profile/v2",
        method="POST",
        token=token,
        data={
            "ed": formatted_list,
            "infoString": "".join(sorted(all_keys)),
            "requiredString": ""
        }
    )


def update_additional_info(
    about: Optional[str] = None,
    github: Optional[str] = None,
    linkedin: Optional[str] = None,
    handle_team: Optional[bool] = None,
    career_break: Optional[bool] = None,
    role_and_responsibility: Optional[str] = None,
    token: Optional[str] = None
) -> Tuple[int, Dict[str, Any]]:
    """Update additional profile information (about summary, GitHub, team handling, role & responsibility)."""
    data: Dict[str, Any] = {}
    if about is not None:
        data["about"] = about
    if github is not None:
        data["github"] = github
    if linkedin is not None:
        data["linkedin"] = linkedin
    if handle_team is not None:
        data["handleTeam"] = 1 if handle_team else 0
    if career_break is not None:
        data["careerBreak"] = 1 if career_break else 0
    if role_and_responsibility is not None:
        data["roleAndResponsibility"] = role_and_responsibility

    return update_profile_section("ai", data, token=token)


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
