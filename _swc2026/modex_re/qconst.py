import sys, os, importlib
sys.path.insert(0, r"C:\modex-mh-agent\resources\app"); sys.path.insert(0, r"C:\modex-mh-agent\resources\app\backend")
os.chdir(r"C:\modex-mh-agent\resources\app")
import backend.services.writing_review as w
for n in ["DRAFT_CHECK_SKILLS","FINAL_CHECK_SKILLS","PLAN_CHECK_SKILLS","REPORT_NAME","STEP_CHECK_TIMEOUT_SECONDS"]:
    print(n,"=",repr(getattr(w,n,None)))
import backend.services.submission_review as s
for n in ["CHECKER_NAME","COMPILE_SKILLS"]:
    print(n,"=",repr(getattr(s,n,None)))
