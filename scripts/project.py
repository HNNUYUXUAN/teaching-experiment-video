"""Create a resumable working folder without reading or copying private source media."""
import argparse
import json
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('command',choices=['init'])
p.add_argument('--directory',type=Path,required=True)
p.add_argument('--title',required=True)
p.add_argument('--provider',choices=['auto','agent','chatgpt-browser','bailian','manual'],default='auto')
a=p.parse_args()
root=a.directory.resolve()
if root.exists(): raise SystemExit('Existing project preserved; resume its state.json instead.')
root.mkdir(parents=True)
for name in ('evidence','storyboard','prompts','images','audio','subtitles','edit','delivery','checks'):
    (root/name).mkdir()
state={'schema_version':1,'title':a.title,'current_stage':'evidence','image_provider':a.provider,
       'stages':{s:'pending' for s in ('evidence','script','images','audio','subtitles','edit','export','archive')},
       'browser_connection':'not_verified','cloud_access':'not_verified','blockers':[],
       'next_action':'Inspect actual source media and complete the evidence table.'}
(root/'state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
(root/'evidence/index.csv').write_text('source,in_us,out_us,observed_action,observed_result,interpretation,limits\n',encoding='utf-8-sig')
(root/'storyboard/shots.csv').write_text('shot_id,source,in_us,out_us,start_us,end_us,narration_id,on_screen_text,status\n',encoding='utf-8-sig')
(root/'prompts/image-request.json').write_text(json.dumps({'prompt':'','size':'1664*928'},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':'initialized','stage':'evidence','next':'Inspect source media; empty prompt must be completed before image generation.'}))
