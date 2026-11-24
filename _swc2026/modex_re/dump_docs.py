# -*- coding: utf-8 -*-
import sys, os, json, inspect
sys.path.insert(0, r"C:\modex-mh-agent\resources\app")
sys.path.insert(0, r"C:\modex-mh-agent\resources\app\backend")
os.chdir(r"C:\modex-mh-agent\resources\app")
import backend.services.workflow_engine as we
names = ["run_workflow","run_single_step","_process_retry_policy","_retry_backoff_seconds","_fresh_retry_handoff",
"_primary_output_health","_primary_output_size","_main_output_receipt","_usable_main_output_receipt",
"_check_step_companions","_check_figures_step_health","_check_figures_step_health_static","_check_data_figure_quality",
"_check_figure_pdf_quality","_check_paper_body_pages","_check_paper_modeling_quality_raw","_check_stats_coherence",
"pending_check_state","step_recovery_state","_continue_state","_finish_continue_state","_uncount_paid_continue",
"_pause_for_check","_pause_for_access_mode","_pause_for_protected_content","_confirm_checkpoint_without_model",
"_verify_checkpoint_revision","_read_figure_manifest","_free_recheck","_recovery_outputs_pass","_health_requires_repair",
"recover_checked_step","_mark_active_step_failed","request_pause","is_pause_requested","clear_pause_request","load_run_scope","clear_run_scope","_build_step_prompt","_handoff_text"]
out=[]
for n in names:
    try:
        f=getattr(we,n)
        out.append({"name":n,"sig":str(inspect.signature(f)),"doc":inspect.getdoc(f) or ""})
    except Exception as e:
        out.append({"name":n,"error":repr(e)})
open(r"E:\数学建模\_swc2026\modex_re\engine_docs.json","w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,indent=1))
print(len(out))
