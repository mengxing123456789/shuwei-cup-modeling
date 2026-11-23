import re,os,sys,json
import urllib.request
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'}
urls={
 'A':'https://blog.csdn.net/LegendNoTitle/article/details/134433175',
 'B':'https://blog.csdn.net/LegendNoTitle/article/details/134433498',
 'C':'https://blog.csdn.net/LegendNoTitle/article/details/134433583',
 'D':'https://blog.csdn.net/LegendNoTitle/article/details/134433678',
}
os.makedirs('src_2023',exist_ok=True)
for k,u in urls.items():
    try:
        req=urllib.request.Request(u,headers=UA)
        h=urllib.request.urlopen(req,timeout=40).read().decode('utf-8','ignore')
    except Exception as e:
        print(k,'ERR',e); continue
    m=re.search(r'<div id="content_views".*?>(.*?)<div id="treeSkill"',h,re.S) or re.search(r'<div id="content_views".*?>(.*?)</article>',h,re.S)
    body=m.group(1) if m else h
    body=re.sub(r'<script.*?</script>','',body,flags=re.S)
    body=re.sub(r'<style.*?</style>','',body,flags=re.S)
    body=re.sub(r'<br\s*/?>','\n',body)
    body=re.sub(r'</(p|div|li|h\d|tr)>','\n',body)
    body=re.sub(r'<[^>]+>','',body)
    import html as H
    body=H.unescape(body)
    body='\n'.join(l.strip() for l in body.split('\n') if l.strip())
    open(f'src_2023/{k}_csdn.txt','w',encoding='utf-8').write(body)
    print(k,'chars',len(body))
