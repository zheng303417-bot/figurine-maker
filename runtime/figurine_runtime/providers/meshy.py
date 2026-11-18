import base64, json, math, os, re, time, urllib.error, urllib.request, urllib.parse
from pathlib import Path

class ProviderError(RuntimeError):
    def __init__(self, message, task_id=None, status=None):
        super().__init__(message); self.task_id=task_id; self.status=status

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl): return None

OPENER = urllib.request.build_opener(NoRedirect())

def generate(job, job_dir, destination, *, approve_paid=False, approve_upload=False):
    if not approve_paid or not approve_upload or job.get('allow_external_image_upload') is not True:
        raise ProviderError('Meshy requires explicit paid-call and image-upload approval')
    budget=job.get('max_paid_credits')
    if isinstance(budget,bool) or not isinstance(budget,(int,float)) or not math.isfinite(budget) or budget<20:
        raise ProviderError('Meshy requires a budget of at least 20 credits')
    key=os.environ.get('MESHY_API_KEY')
    if not key: raise ProviderError('MESHY_API_KEY is missing')
    images=job.get('source_images',[])
    if not isinstance(images,list) or not 1 <= len(images) <= 4: raise ProviderError('Meshy requires one to four images')
    root=Path(job_dir).resolve(); urls=[]
    for name in images:
        if not isinstance(name,str) or Path(name).is_absolute(): raise ProviderError('Invalid image path')
        p=(root/name).resolve()
        if not p.is_relative_to(root) or not p.is_file(): raise ProviderError('Invalid image path')
        mime={'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp'}.get(p.suffix.lower())
        if not mime or not 0<p.stat().st_size<=20_000_000: raise ProviderError('Invalid image type or size')
        urls.append('data:'+mime+';base64,'+base64.b64encode(p.read_bytes()).decode())
    endpoint='image-to-3d' if len(urls)==1 else 'multi-image-to-3d'
    payload={'image_url':urls[0]} if len(urls)==1 else {'image_urls':urls}
    payload.update(ai_model='meshy-7.1', geometry_resolution='standard', should_texture=False, target_formats=['glb'])
    base='https://api.meshy.ai/openapi/v1/'+endpoint; task=None; status=None
    def request(url, data=None, auth=True, limit=2_000_000):
        headers={'Authorization':'Bearer '+key} if auth else {}
        if data is not None: headers['Content-Type']='application/json'
        req=urllib.request.Request(url,data=data,headers=headers)
        try:
            with OPENER.open(req,timeout=30) as response:
                raw=response.read(limit+1)
                if len(raw)>limit: raise ProviderError('Response exceeds size limit',task,status)
                return raw
        except ProviderError: raise
        except urllib.error.HTTPError as e: raise ProviderError('Meshy HTTP error '+str(e.code),task,status) from None
        except Exception: raise ProviderError('Meshy request failed',task,status) from None
    try:
        task=json.loads(request(base,json.dumps(payload).encode()))['result']
        if not isinstance(task,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',task): task=None; raise ValueError()
    except (ValueError,KeyError,TypeError): raise ProviderError('Invalid Meshy submission response') from None
    for _ in range(120):
        try:
            result=json.loads(request(base+'/'+urllib.parse.quote(task,safe=''))); status=result['status']
            if not isinstance(status,str): raise ValueError()
        except (ValueError,KeyError,TypeError): raise ProviderError('Invalid Meshy task response',task,status) from None
        if status=='SUCCEEDED': break
        if status not in ('PENDING','IN_PROGRESS'): raise ProviderError('Meshy task did not succeed',task,status)
        time.sleep(5)
    else: raise ProviderError('Meshy polling timed out',task,status)
    try:
        url=result['model_urls']['glb']; parsed=urllib.parse.urlsplit(url)
        if parsed.scheme!='https' or parsed.hostname!='assets.meshy.ai' or parsed.username or parsed.password or parsed.port not in (None,443): raise ValueError()
    except (ValueError,KeyError,TypeError): raise ProviderError('Untrusted model URL',task,status) from None
    data=request(url,auth=False,limit=200_000_000)
    if len(data)<20 or data[:4]!=b'glTF' or int.from_bytes(data[4:8],'little')!=2 or int.from_bytes(data[8:12],'little')!=len(data): raise ProviderError('Invalid downloaded GLB',task,status)
    dest=Path(destination); dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(data)
    return {'provider':'meshy','task_id':task,'status':'SUCCEEDED'}
