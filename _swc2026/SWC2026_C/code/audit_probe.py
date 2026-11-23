
# --- generative-tool note (required by the organiser's notice of 2026-11) ---
# Drafted with DeepSeek Harness 0.2.2-rc.3, a command-line coding agent developed and
# released by DeepSeek (November 2026); used 18-22 November 2026. Every number this
# file produces was re-executed by the team from a clean shell and traced to data/*.json.
# team from a clean shell and traced to data/*.json through code/fill_numbers.py.
# -*- coding: utf-8 -*-
"""靶向读取：只打印对账需要的行/字段。"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, 'data')


def load(n):
    with open(os.path.join(D, n), encoding='utf-8') as f:
        return json.load(f)


def show(title, obj):
    print('\n### ' + title)
    print(json.dumps(obj, ensure_ascii=False, indent=1, default=str))


p1b = load('p1b_gpu.json')
show('p1b per_env', p1b['per_env_test'])

p2g = load('p2_gpu.json')
show('p2_gpu meta', p2g['_meta'])
show('p2_gpu rows', p2g['rows'])

p2p = load('p2_prediction.json')
show('p2 econ', p2p['economics'])
show('p2 ridge rows', [r for r in p2p['by_length'] if r['method'] == 'ridge'])
show('p2 hold rows', [r for r in p2p['by_length'] if r['method'] == 'hold'])

p2i = load('p2_interval.json')
show('p2 interval', p2i['by_length'])

p1r = load('p1_reliability.json')
show('p1 rel per_env', p1r['per_env_test'])
show('p1 rel thresholds', p1r['threshold_sensitivity'])

p1s = load('p1_segmentation.json')
show('p1 seg by_method', {k: {kk: vv for kk, vv in v.items()} for k, v in p1s['by_method'].items()})

p3 = load('p3_scheduling.json')
nom = [r for r in p3['summary'] if r['alpha'] == 1.0 and r['beta'] == 0.5]
show('p3 nominal summary', nom)
show('p3 paired nominal', [r for r in p3['paired_vs_edf'] if r['alpha'] == 1.0 and r['beta'] == 0.5])
show('p3 constraint', p3['constraint_nominal'])
show('p3 review bar sens', p3['review_bar_sensitivity'])
show('p3 residuals', p3['residuals'])
show('p3 capacity', p3['capacity'])
show('p3 capacity_analytic', p3['capacity_analytic'])

p3s = load('p3_stochastic_schedule.json')
show('p3s meta', p3s['_meta'])
show('p3s summary', p3s['summary'])
show('p3s paired', p3s['paired_vs_slack_old'])
show('p3s mapping nominal', [r for r in p3s['mapping_sensitivity'] if r['alpha'] == 1.0 and r['beta'] == 0.5])

p3f = load('p3_final_duration.json')
show('p3 final eval', p3f['evaluation'])
show('p3 final top10', p3f['top10'])

p3d = load('p3_duration_selected.json')
show('p3 dur selected by_prefix', p3d['selected'])
show('p3 dur selected test', p3d['test'])

p3n = load('p3_neural_progress.json')
show('p3 neural metrics', p3n['metrics'])

p3pm = load('p3_progress_models.json')
show('p3 progress results', p3pm['results'])

p3m = load('p3_prefix_marginal.json')
show('p3 prefix marginal medians', {
    'validation_median_gain_frac': p3m['validation_median_gain_frac'],
    'test_median_gain_frac': p3m['test_median_gain_frac'],
    'validation_median_shrink_gain': p3m['validation_median_shrink_gain'],
    'test_median_shrink_gain': p3m['test_median_shrink_gain'],
    'best_validation_1p0': p3m['best_validation_1p0'],
})
show('p3 prefix marginal rows names', [(r['features'], r['model'], r['split'], round(r['mae_gain_frac'], 4)) for r in p3m['rows']])

p3v = load('p3_visual_duration.json')
show('p3 visual rows summary', [(r['design'], r['model'], r['split'], round(r['mae'], 3), round(r['spearman'], 3), round(r['mean_shrink'], 3)) for r in p3v['rows']])

p3pi = load('p3_prefix_informativeness.json')
show('p3 prefix informativeness', {
    'spread': [{k: r[k] for k in ('split', 'prefix', 'n', 'sd_total', 'sd_resid_fusion', 'shrinkage_fusion')} for r in p3pi['spread']],
    'p_late': p3pi['p_late_by_prefix'],
    'voi_bounds': p3pi['voi_bounds'],
    'monotone': p3pi['prefix_shrinks_spread_monotonically'],
    'reduction': p3pi['relative_spread_reduction_0p2_to_1p0'],
})

for fn in ('p1_stage_stats.json', 'p1_state_summary.json', 'feature_names.json'):
    o = load(fn)
    show(fn, {k: v for k, v in o.items() if k != 'dominant'})