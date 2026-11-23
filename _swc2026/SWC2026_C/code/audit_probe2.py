
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""紧凑对账输出：一行一条，便于逐条核对。"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'data')


def load(n):
    with open(os.path.join(D, n), encoding='utf-8') as f:
        return json.load(f)


def f(x, n=4):
    return '' if x is None else (f'{x:.{n}f}' if isinstance(x, float) else str(x))


p1b = load('p1b_gpu.json')
print('P1B_META', {k: p1b[k] for k in ('best_epoch', 'val_auc_at_best', 'test_auc', 'test_ap', 'test_positive_rate', 'test_ap_lift', 'train_seconds', 'params')})
for r in p1b['per_env_test']:
    print('P1B_ENV', r)

p2g = load('p2_gpu.json')
print('P2G_BASE', json.dumps(p2g['_meta']['baseline_ridge'], ensure_ascii=False))
print('P2G_META', json.dumps({k: p2g['_meta'][k] for k in ('context_frames', 'epochs', 'batch', 'variants')}, ensure_ascii=False))
for r in p2g['rows']:
    print('P2G_ROW', r['L_frames'], r['L_s'], r['variant'], 'rmse', f(r['test_rmse_m']), 'med', f(r['test_median_err_m']),
          'ep', f(r['test_endpoint_rmse_m']), 'w2', f(r['test_within_2cm']), 'w5', f(r['test_within_5cm']),
          'n', r.get('n_test'), 'bestep', r.get('best_val_epoch'), 'valrmse', f(r.get('val_rmse_m')))

p2p = load('p2_prediction.json')
print('P2_ECON_OPT', json.dumps(p2p['economics']['optimum'], ensure_ascii=False))
for k, v in p2p['economics']['baselines'].items():
    print('P2_ECON_BASE', k, json.dumps(v, ensure_ascii=False))
for r in p2p['by_length']:
    if r['method'] in ('hold', 'ridge'):
        print('P2_ROW', r['method'], r['L_s'], 'n', r['n_windows'], 'rmse', f(r['rmse']), 'mae', f(r['mae']),
              'jump', f(r['jump_mean']), 'p95', f(r['jump_p95']), 'w2', f(r['within_2cm']), 'w5', f(r['within_5cm']))

for r in load('p2_interval.json')['by_length']:
    print('P2_INT', r['L_s'], r['L_frames'], 'nval', r['n_val'], 'ntest', r['n_test'], 'q90', f(r['q90_m']),
          'cov', f(r['coverage_test']), 'med', f(r['empirical_median_err_m']))

p1r = load('p1_reliability.json')
for r in p1r['per_env_test']:
    print('P1_ENV', r)
for r in p1r['threshold_sensitivity']:
    print('P1_THR', r['threshold'], f(r['retained']), f(r['bad_recall']), f(r['bad_precision']), f(r['f1']))

p1s = load('p1_segmentation.json')
for k, v in p1s['by_method'].items():
    print('P1_SEG', k, json.dumps(v, ensure_ascii=False))

p3 = load('p3_scheduling.json')
print('P3_META', json.dumps({k: p3['_meta'][k] for k in ('n_seeds', 'n_trials_per_policy', 'mappings', 'policies')}, ensure_ascii=False))
for r in p3['summary']:
    if r['alpha'] == 1.0 and r['beta'] == 0.5:
        print('P3_NOM', r['case'], r['policy'], 'eta', f(r['weighted_on_time_rate']), 'ci', f(r['weighted_on_time_rate_ci95']),
              'comp', f(r['weighted_completion_rate']), 'tard', f(r['weighted_tardiness_s']), 'cost', f(r['cost']),
              'rev', f(r['reviews']), 'elapsed', f(r['elapsed_s']), 'over', f(r['observed_overrun_s']),
              'idle', f(r['reserved_idle_s']), 'cens', f(r['censored_units']), 'ndone', f(r['n_done']), 'ndrop', f(r['n_drop']))
for r in p3['paired_vs_edf']:
    if r['alpha'] == 1.0 and r['beta'] == 0.5:
        print('P3_PAIR', r['case'], r['policy'], f(r['mean_diff']), f(r['ci95']))
for r in p3['constraint_nominal']:
    print('P3_CONSTR', r['case'], r['policy'], f(r['mean_eta']), r['met'])
for r in p3['review_bar_sensitivity']:
    print('P3_REVBAR', r['case'], r['review_bar'], 'eta', f(r['eta']), 'rev', f(r['reviews']), 'cost', f(r['cost']), 'idle', f(r['idle']), 'n', r['n_seeds'])
print('P3_RESID', json.dumps(p3['residuals'], ensure_ascii=False))
for r in p3['capacity']:
    print('P3_CAP', r)
for r in p3['capacity_analytic']:
    print('P3_CAPA', r)

p3s = load('p3_stochastic_schedule.json')
print('P3S_META', json.dumps(p3s['_meta'], ensure_ascii=False))
for r in p3s['summary']:
    print('P3S', r['case'], r['policy'], 'eta', f(r['weighted_on_time_rate']), 'ci', f(r['weighted_on_time_rate_ci95']),
          'comp', f(r['weighted_completion_rate']), 'tard', f(r['weighted_tardiness_s']), 'cost', f(r['cost']),
          'rev', f(r['reviews']), 'idle', f(r['reserved_idle_s']), 'over', f(r['observed_overrun_s']))
for r in p3s['paired_vs_slack_old']:
    print('P3S_PAIR', r['case'], r['policy'], f(r['mean_diff']), f(r['ci95']))
for r in p3s['mapping_sensitivity']:
    if r['alpha'] == 1.0 and r['beta'] == 0.5:
        print('P3S_MAP', r['case'], r['policy'], f(r['eta']), f(r['completion']), f(r['cost']))

p3f = load('p3_final_duration.json')
for r in p3f['evaluation']:
    print('P3F_EVAL', r['name'], r['split'], 'mae', f(r['mae']), 'spearman', f(r['spearman']), 'shrink', f(r['mean_shrink']))
    print('P3F_BYP', json.dumps(r['by_prefix'], ensure_ascii=False))
print('P3F_TOP', json.dumps(p3f['top10'], ensure_ascii=False))

p3d = load('p3_duration_selected.json')
print('P3D_SEL', json.dumps(p3d['selected'], ensure_ascii=False))
print('P3D_TEST', json.dumps(p3d['test'], ensure_ascii=False))

p3n = load('p3_neural_progress.json')
print('P3N_MET', json.dumps(p3n['metrics'], ensure_ascii=False))
print('P3N_META', json.dumps(p3n['_meta'], ensure_ascii=False))

p3pm = load('p3_progress_models.json')
for k, v in p3pm['results'].items():
    print('P3PM', k, json.dumps(v, ensure_ascii=False))

p3m = load('p3_prefix_marginal.json')
print('P3M_MED', f(p3m['validation_median_gain_frac']), f(p3m['test_median_gain_frac']),
      f(p3m['validation_median_shrink_gain']), f(p3m['test_median_shrink_gain']))
print('P3M_BEST', json.dumps(p3m['best_validation_1p0'], ensure_ascii=False))
for r in p3m['rows']:
    print('P3M_ROW', r['features'], r['model'], r['split'], f(r['mae_0p2'], 3), f(r['mae_0p6'], 3), f(r['mae_1p0'], 3),
          'gainf', f(r['mae_gain_frac']), 'shrink', f(r['shrink_gain']), 'sp', f(r['spearman_0p2'], 3), f(r['spearman_1p0'], 3))

p3v = load('p3_visual_duration.json')
for r in p3v['rows']:
    print('P3V', r['design'], r['model'], r['split'], 'mae', f(r['mae'], 3), 'sp', f(r['spearman']), 'shrink', f(r['mean_shrink']))

p3pi = load('p3_prefix_informativeness.json')
for r in p3pi['spread']:
    print('P3PI_SPREAD', r['split'], r['prefix'], 'n', r['n'], 'sd', f(r['sd_total'], 3), 'sdf', f(r['sd_resid_fusion'], 3), 'shrink', f(r['shrinkage_fusion']))
for r in p3pi['p_late_by_prefix']:
    print('P3PI_PLATE', r['bar'], r['prefix'], f(r['p_late']))
for r in p3pi['voi_bounds']:
    print('P3PI_VOI', json.dumps(r, ensure_ascii=False))
print('P3PI_MONO', p3pi['prefix_shrinks_spread_monotonically'], f(p3pi['relative_spread_reduction_0p2_to_1p0']))

p6 = load('p1_state_summary.json')
print('P1S', json.dumps(p6, ensure_ascii=False))
print('P1ST', json.dumps(load('p1_stage_stats.json'), ensure_ascii=False))