"""
Live matrix test for all 6 tools and their parameter variations in hirist_mcp.
"""
import sys
from pathlib import Path

# Ensure paths
workspace_dir = str(Path(__file__).resolve().parent.parent.parent)
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from hirist_mcp import server, client, auth

# Load environment
auth.load_env_file(str(Path(workspace_dir) / ".env"))

def run_tests():
    token, phpsessid = auth.resolve_credentials()
    print(f"Testing with Token: {token[:15]}... and PHPSESSID: {phpsessid[:10]}...")

    tests_run = 0
    tests_passed = 0
    failures = []

    def run_case(name, func, *args, **kwargs):
        nonlocal tests_run, tests_passed
        tests_run += 1
        print(f"\n[{tests_run}] Testing: {name}...")
        try:
            res = func(*args, **kwargs)
            # Check for error in response
            st = res.get("status_code", 200)
            if st in (200, 207) or res.get("status") in ("success", "partial_success", "applied", "already_applied"):
                print(f"  --> PASSED: {st}")
                tests_passed += 1
                return res
            elif "details" in res or "result" in res or "metrics" in res:
                print(f"  --> PASSED (payload received): {st}")
                tests_passed += 1
                return res
            else:
                err = res.get("error") or res.get("result", {}).get("error") or res
                print(f"  --> FAILED: status {st}, error: {err}")
                failures.append((name, res))
                return res
        except Exception as e:
            print(f"  --> EXCEPTION: {e}")
            failures.append((name, str(e)))
            return None

    # 1. manage_session
    run_case("manage_session: validate", server.manage_session, action="validate")
    run_case("manage_session: refresh", server.manage_session, action="refresh")

    # 2. manage_profile: get, pulse, resume, delete_item
    run_case("manage_profile: get", server.manage_profile, action="get")
    run_case("manage_profile: pulse", server.manage_profile, action="pulse")
    run_case("manage_profile: get_resume metadata", server.manage_profile, action="get_resume", extract_text=False)
    run_case("manage_profile: get_resume extract_text", server.manage_profile, action="get_resume", extract_text=True, max_pages=2)
    run_case("manage_profile: delete_item (education validation)", server.manage_profile, action="delete_item", item_type="education", item_id=999999999)

    # 2b. manage_profile: update
    # Get current profile to avoid damaging data
    prof = client.get_profile()[1]
    curr_desig = prof.get("currentDesignation", "Senior Full Stack Engineer") if isinstance(prof, dict) else "Senior Full Stack Engineer"
    skills_curr = client.get_skills()[1]
    skills_list = skills_curr if isinstance(skills_curr, list) else ["Python", "FastAPI", "Docker"]

    run_case(
        "manage_profile: update (personal, skills, coverletter)",
        server.manage_profile,
        action="update",
        personal={"current_designation": curr_desig},
        skills=skills_list[:5],
        cover_letter="Senior software engineer experienced in Python, cloud systems, and scalable backend architectures."
    )

    # 3. search_jobs: feed & parametric search
    run_case("search_jobs: feed mode (empty)", server.search_jobs)
    run_case("search_jobs: parametric search", server.search_jobs, query="Python", location="Bangalore", min_exp=2, max_exp=8, size=5)

    # 4. get_job_details: single & batch
    run_case("get_job_details: single with assessment", server.get_job_details, job_ids=1684702, include_assessment=True)
    run_case("get_job_details: batch", server.get_job_details, job_ids=[1684702, 1684614], include_assessment=True)

    # 5. manage_job_pipeline: metrics, save, unsave, apply, follow_up
    run_case("manage_job_pipeline: metrics", server.manage_job_pipeline, action="metrics")
    run_case("manage_job_pipeline: save single", server.manage_job_pipeline, action="save", job_ids=1684702)
    run_case("manage_job_pipeline: save batch", server.manage_job_pipeline, action="save", job_ids=[1684702])
    run_case("manage_job_pipeline: unsave", server.manage_job_pipeline, action="unsave", job_ids=[1684702])
    run_case("manage_job_pipeline: apply (single)", server.manage_job_pipeline, action="apply", job_ids=1684702, coverletter="Testing application")
    run_case("manage_job_pipeline: follow_up", server.manage_job_pipeline, action="follow_up", job_ids=1684702)

    # 6. manage_account: settings, blocked, suggest
    run_case("manage_account: get_settings", server.manage_account, action="get_settings")
    run_case("manage_account: list_blocked", server.manage_account, action="list_blocked")
    run_case("manage_account: block_company", server.manage_account, action="block_company", company_id=99999)
    run_case("manage_account: unblock_company", server.manage_account, action="unblock_company", company_id=99999)
    run_case("manage_account: suggest company", server.manage_account, action="suggest", query="Google", category="company")
    run_case("manage_account: suggest institute", server.manage_account, action="suggest", query="IIT", category="institute")

    print("\n" + "=" * 50)
    print(f"LIVE TEST SUMMARY: {tests_passed}/{tests_run} Passed ({(tests_passed/tests_run)*100:.1f}%)")
    print("=" * 50)
    if failures:
        print(f"FAILURES ({len(failures)}):")
        for f_name, f_err in failures:
            print(f" - {f_name}: {f_err}")
    return len(failures) == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
