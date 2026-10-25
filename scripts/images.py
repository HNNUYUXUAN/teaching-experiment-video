"""Bailian Qwen-Image synchronous adapter, usable by any agent with a terminal."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
from urllib.parse import urlparse
import requests
from PIL import Image
from settings import config, valid_endpoint

def payload_for(spec, cfg):
    prompt = spec.get('prompt','').strip()
    if not prompt:
        raise ValueError('prompt is required')
    model = cfg.get('IMAGE_MODEL','')
    if not model.startswith('qwen-image'):
        raise ValueError('This adapter supports Qwen-Image synchronous APIs; read images.md for other models')
    size = spec.get('size') or cfg.get('IMAGE_SIZE')
    width, height = [int(n) for n in size.split('*')]
    if width <= 0 or height <= 0 or not 512*512 <= width*height <= 2048*2048:
        raise ValueError('Image size outside supported total pixel range')
    params={'size':size,'n':1,'prompt_extend':cfg.get('IMAGE_PROMPT_EXTEND','false').lower()=='true','watermark':False}
    if spec.get('negative_prompt'): params['negative_prompt']=spec['negative_prompt']
    if 'seed' in spec: params['seed']=int(spec['seed'])
    return {'model':model,'input':{'messages':[{'role':'user','content':[{'text':prompt}]}]},'parameters':params}

def generate(spec, target, cfg, allow_paid=False, dry_run=False):
    target=Path(target)
    payload=payload_for(spec,cfg)
    identity=hashlib.sha256(json.dumps({'endpoint':cfg['IMAGE_ENDPOINT'],'payload':payload},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    if dry_run:
        return {'status':'dry_run','model':payload['model'],'size':payload['parameters']['size'],'request_sha256':identity,'network_called':False}
    if not allow_paid:
        raise ValueError('Cloud request needs user authorization; use --allow-paid only within that authorization')
    key=(cfg.get('DASHSCOPE_API_KEY') or '').strip()
    if not key:
        raise ValueError('Fill DASHSCOPE_API_KEY in the local .env; no request sent')
    if not valid_endpoint(cfg['IMAGE_ENDPOINT']):
        raise ValueError('Invalid Alibaba Cloud endpoint')
    if target.suffix.lower() != '.png':
        raise ValueError('Output filename must end in .png')
    target.parent.mkdir(parents=True,exist_ok=True)
    pending=target.with_suffix('.pending.json')
    audit=target.with_suffix('.image.json')
    if target.exists() or pending.exists() or audit.exists():
        raise FileExistsError('Existing output or pending request preserved; inspect before any paid retry')
    with pending.open('x',encoding='utf-8') as f:
        json.dump({'request_sha256':identity,'state':'started','model':payload['model']},f)
    try:
        response=requests.post(cfg['IMAGE_ENDPOINT'],json=payload,
            headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},
            timeout=(20,int(cfg['HTTP_TIMEOUT_SECONDS'])),allow_redirects=False)
    except requests.RequestException:
        raise RuntimeError('Image request outcome uncertain; pending marker preserved') from None
    if response.status_code != 200:
        raise RuntimeError('Bailian HTTP '+str(response.status_code)+'; check account/region/model and pending marker')
    try:
        data=response.json()
        parts=data['output']['choices'][0]['message']['content']
        urls=[p['image'] for p in parts if 'image' in p]
        if len(urls)!=1:
            raise ValueError()
        parsed=urlparse(urls[0])
        if parsed.scheme!='https' or not (parsed.hostname or '').endswith('.aliyuncs.com') or parsed.username or parsed.password:
            raise ValueError()
    except (KeyError,TypeError,ValueError,IndexError):
        raise RuntimeError('Unsupported image response or download host; inspect locally, do not resubmit automatically') from None
    # Do not persist signed URLs or send the API key to the image host.
    try:
        download=requests.get(urls[0],stream=True,timeout=(20,120),allow_redirects=False)
        if download.status_code!=200:
            raise RuntimeError('Image download failed; generation may already be billed')
        chunks=[];total=0
        for chunk in download.iter_content(1024*1024):
            total+=len(chunk)
            if total>32*1024*1024: raise RuntimeError('Image exceeds download limit')
            chunks.append(chunk)
        raw=b''.join(chunks)
    except requests.RequestException:
        raise RuntimeError('Image download interrupted; generation may already be billed') from None
    finally:
        if 'download' in locals(): download.close()
    with Image.open(io.BytesIO(raw)) as im:
        if im.format!='PNG': raise RuntimeError('Expected PNG output')
        dimensions=list(im.size);im.verify()
    with target.open('xb') as f: f.write(raw)
    result={'status':'generated','model':payload['model'],'filename':target.name,'size':dimensions,
            'sha256':hashlib.sha256(raw).hexdigest(),'request_sha256':identity,
            'visual_review':'pending','network_called':True}
    with audit.open('x',encoding='utf-8') as f: json.dump(result,f,ensure_ascii=False,indent=2)
    pending.unlink()
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--request',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--allow-paid',action='store_true')
    p.add_argument('--dry-run',action='store_true')
    a=p.parse_args()
    result=generate(json.loads(a.request.read_text(encoding='utf-8-sig')),a.output,config(),a.allow_paid,a.dry_run)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    try: main()
    except (ValueError,FileExistsError,RuntimeError) as exc:
        print(json.dumps({'status':'stopped','reason':str(exc)},ensure_ascii=False))
        sys.exit(1)
    except Exception as exc:
        print(json.dumps({'status':'stopped','error_type':type(exc).__name__,'reason':'Inspect local inputs and pending marker; no automatic retry.'}))
        sys.exit(1)
