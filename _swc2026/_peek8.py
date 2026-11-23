import json, os
D = r'E:\数学建模\_swc2026\SWC2026_C\data'

a = json.load(open(os.path.join(D, 'p3_adaptive.json'), encoding='utf-8'))
print('=== info_levels (case, info, on_time, ci95, reviews, cost) ===')
for r in a['info_levels']:
    print('  %-3s %-12s %.4f ±%.4f  rev=%.2f cost=%.2f tard=%.2f resv=%.1f' % (
        r['case'], r['info'], r['weighted_on_time_rate'], r['weighted_on_time_rate_ci95'],
        r['n_reviews'], r['cost'], r['weighted_tardiness_s'], r['reserved_s']))

print('\n=== upper_bound S3 full ===')
print(json.dumps(a['upper_bound']['S3'], ensure_ascii=False, indent=1))

print('\n=== final_policy S3 ===')
for r in a['final_policy']:
    if r['case'] == 'S3':
        print('  a=%.2f b=%.2f on_time=%.4f ±%.4f' % (
            r['alpha'], r['beta'], r['weighted_on_time_rate'], r['weighted_on_time_rate_ci95']))

print('\n=== regret all ===')
for r in a['regret']:
    print('  %-3s a=%.2f b=%.2f mine=%.4f best=%s %.4f regret=%.4f (risk %.4f, slack %.4f)' % (
        r['case'], r['alpha'], r['beta'], r['mine'], r['best_policy'], r['best'],
        r['regret'], r['risk_fusion'], r['slack_old']))

print('\n=== best_p3_sens paired S3 ===')
p = json.load(open(os.path.join(D, 'best_p3_sens.json'), encoding='utf-8'))
print(json.dumps(p['paired_vs_default']['S3'], ensure_ascii=False, indent=1)[:900])