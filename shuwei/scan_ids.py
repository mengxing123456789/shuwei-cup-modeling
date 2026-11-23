# -*- coding: utf-8 -*-
import re, sys, concurrent.futures, urllib.request, ssl
sys.stdout.reconfigure(encoding="utf-8")
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def fetch(i):
    for path in ("News", "Awards"):
        url = "https://www.nmmcm.org.cn/%s/%d.html" % (path, i)
        try:
            req = urllib.request.Request(url, headers=HDR)
            html = urllib.request.urlopen(req, timeout=20, context=ctx).read()
            try:
                txt = html.decode("utf-8")
            except Exception:
                txt = html.decode("gbk", "replace")
            m = re.search(r"<title>(.*?)</title>", txt, re.S)
            title = (m.group(1).strip() if m else "")
            body = re.sub(r"<[^>]+>", " ", txt)
            body = re.sub(r"\s+", " ", body)
            pan = re.findall(r"https://pan\.baidu\.com/s/[A-Za-z0-9_\-]+", body)
            pw = re.findall(r"提取码[:：]?\s*\**\s*([A-Za-z0-9]{4})", body)
            return (i, path, title, pan[:2], pw[:2], len(body))
        except Exception as e:
            continue
    return None

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    for r in ex.map(fetch, range(100, 215)):
        if r and r[2]:
            i, path, title, pan, pw, n = r
            print("%3d %-6s %s" % (i, path, title[:60]))
            if pan:
                print("      PAN", pan, pw)