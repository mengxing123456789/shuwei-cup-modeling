# -*- coding: utf-8 -*-
import os, json, subprocess, collections
BASE = r'C:\Users\29900\Desktop\Restocking_Problem_and_Data_EN\Raw_Data'
OUT = r'E:\数学建模\_swc2026\audit'
FF = r'C:\Users\29900\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffprobe.exe'
L = []
rows = []
for ds in ('EgoDemo', 'EgoPro', 'EgoStandard'):
    for dp, dns, fns in os.walk(os.path.join(BASE, ds)):
        for fn in sorted(fns):
            if not fn.lower().endswith('.mp4'):
                continue
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, BASE)
            cmd = [FF, '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                   'stream=codec_name,width,height,r_frame_rate,avg_frame_rate,nb_frames,pix_fmt,bit_rate,profile,level:format=duration,size,bit_rate',
                   '-of', 'json', p]
            try:
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                j = json.loads(out.stdout)
                s = j['streams'][0]
                f = j['format']
                rows.append(dict(ds=ds, rec=rel.split(os.sep)[2], name=os.sep.join(rel.split(os.sep)[3:]),
                                 codec=s.get('codec_name'), w=s.get('width'), h=s.get('height'),
                                 fps=s.get('avg_frame_rate'), rfps=s.get('r_frame_rate'),
                                 nb=s.get('nb_frames'), dur=float(f.get('duration', 0)), mb=float(f.get('size', 0)) / 1048576,
                                 pix=s.get('pix_fmt'), profile=s.get('profile'), level=s.get('level')))
            except Exception as e:
                rows.append(dict(ds=ds, rec=rel, err=str(e)[:200]))

L.append('===== video probe: %d files =====' % len(rows))
errs = [r for r in rows if r.get('err')]
L.append('errors: %d %s' % (len(errs), errs[:3]))
ok = [r for r in rows if not r.get('err')]
for ds in ('EgoDemo', 'EgoPro', 'EgoStandard'):
    sub = [r for r in ok if r['ds'] == ds]
    L.append('-- %s n=%d MB=%.1f' % (ds, len(sub), sum(r['mb'] for r in sub)))
    agg = collections.Counter((r['codec'], r['w'], r['h'], r['fps'], r['pix']) for r in sub)
    for k, c in agg.most_common():
        d = [r['dur'] for r in sub if (r['codec'], r['w'], r['h'], r['fps'], r['pix']) == k]
        L.append('   %-60s x%d  dur[%.2f..%.2f]' % (str(k), c, min(d), max(d)))
    L.append('   fps strings: %s' % collections.Counter(r['fps'] for r in sub))
    # name -> count
    L.append('   names: %s' % dict(collections.Counter(r['name'] for r in sub)))

# cross-check a few: duration*fps vs nb_frames
L.append('')
L.append('===== duration*fps vs nb_frames (first 8) =====')
for r in ok[:8]:
    fps = eval(r['fps'].replace('/', '/1')) if '/' in r['fps'] else float(r['fps'])
    L.append('  %-70s dur=%.3f fps=%s nb=%s calc=%.1f' % (r['ds'] + '/' + r['rec'] + '/' + r['name'], r['dur'], r['fps'], r['nb'], r['dur'] * fps))

# per-record min/max duration
L.append('')
L.append('===== per-record video duration (max of camera) =====')
for ds in ('EgoDemo', 'EgoPro', 'EgoStandard'):
    L.append('-- %s' % ds)
    byrec = collections.defaultdict(list)
    for r in ok:
        if r['ds'] == ds:
            byrec[r['rec']].append((r['name'], r['dur'], r['mb']))
    for rec in sorted(byrec):
        v = byrec[rec]
        L.append('   %-40s n=%d dur=%s' % (rec, len(v), ['%s:%.2f' % (n, d) for n, d, m in v]))

json.dump(ok, open(os.path.join(OUT, 'videos.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(os.path.join(OUT, 'videos.txt'), 'w', encoding='utf-8').write('\n'.join(L))
print('OK', len(rows), 'err', len(errs))