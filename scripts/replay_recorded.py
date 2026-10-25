"""Offline replay of a previously collected WAV/ASR pair, not a new cloud test."""
import argparse
from pathlib import Path
import pipeline as p

parser=argparse.ArgumentParser()
parser.add_argument('--audio',required=True)
parser.add_argument('--response',required=True)
parser.add_argument('--transcript-audit',required=True)
parser.add_argument('--output',required=True)
a=parser.parse_args()
out=Path(a.output)
out.mkdir(parents=True,exist_ok=True)
record=p.read(a.transcript_audit)['segments'][0]
p.write(out/'manifest.json',{'segments':[{'id':'recorded-replay','text':record['script_text'],
                                        'audio':str(Path(a.audio).resolve()),'tail_ms':1000}]})
placement=p.assemble(out/'manifest.json',out/'package',p.config())
item=p.read(placement)['segments'][0]
p.write(Path(item['audio']).with_suffix('.asr.json'),
        {'audio_sha256':item['audio_sha256'],'response':p.read(a.response),
         'provenance':'offline replay of provided historical WAV/ASR pair; not a cloud call'})
cues=p.align(placement,p.config())
p.write(out/'replay-report.json',{'offline_replay':'passed','cues':len(cues),
        'cloud_api_called':False,'source_files_modified':False,
        'caption_report':str(placement.parent/'caption-report.json')})
print(f'PASS historical recording replay: {len(cues)} cues; no cloud call')
