"""Prepare a NEW draft copy from an already-imported project. Never register live projects."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import uuid
from pipeline import read, write

def retime(content, plan):
    result = copy.deepcopy(content)
    tracks = {t['id']:t for t in result['tracks']}
    track = tracks[plan['visual_track_id']]
    assert track['type'] == 'video'
    sequence = plan['visuals']
    assert len(sequence) == len(track['segments']), 'EDL and actual segment counts differ'
    materials = {m['id']:m for m in result['materials']['videos']}
    cursor = 0
    report = []
    for segment, row in zip(track['segments'], sequence):
        assert segment['id'] == row['segment_id'], 'Use observed IDs, not ambiguous filenames'
        material = materials[segment['material_id']]
        assert Path(material['path']).resolve() == Path(row['path']).resolve(), 'Material path mismatch'
        assert Path(material['path']).is_file(), 'Missing visual asset'
        end = int(row['end_us'])
        duration = end-cursor
        assert duration > 0
        kind = row['kind']
        actual_kind = str(material.get('type', '')).lower()
        assert kind in ('image','video')
        assert (kind == 'image' and actual_kind in ('photo','image')) or (kind == 'video' and actual_kind == 'video'), 'Media type mismatch'
        old_duration = segment['target_timerange']['duration']
        if kind == 'video':
            assert duration == old_duration, 'Video timing/rate edits require an explicitly revised source plan'
        else:
            segment['source_timerange']['duration'] = duration
        segment['target_timerange'] = dict(segment['target_timerange'], start=cursor, duration=duration)
        report.append({'segment_id':segment['id'], 'path':row['path'], 'kind':kind,
                       'start_us':cursor, 'end_us':end, 'duration_us':duration})
        cursor = end
    assert cursor == plan['total_us']
    # Audio is authoritative. Every retained audio segment must fit; main narration is continuous.
    narration = tracks[plan['audio_track_id']]
    assert narration['type'] == 'audio'
    audio_cursor = 0
    for segment in narration['segments']:
        timing = segment['target_timerange']
        assert timing.get('start',0) == audio_cursor, 'Narration gap/overlap; use padded audio'
        audio_cursor += timing['duration']
    assert audio_cursor == cursor, 'Narration and picture total durations differ'
    if 'captions' in plan:
        captions = tracks[plan['caption_track_id']]['segments']
        assert len(captions) == len(plan['captions'])
        texts = {m['id']:m for m in result['materials']['texts']}
        previous = 0
        for segment, cue in zip(captions,plan['captions']):
            assert json.loads(texts[segment['material_id']]['content'])['text'] == cue['text']
            start,end = cue['start_ms']*1000, cue['end_ms']*1000
            assert previous <= start < end <= cursor
            segment['target_timerange'] = dict(segment['target_timerange'],start=start,duration=end-start)
            previous = end
    for t in result['tracks']:
        for s in t.get('segments',[]):
            r = s.get('target_timerange',{})
            assert r.get('start',0)+r.get('duration',0) <= cursor, 'An unedited track extends past the timeline'
    result['duration'] = cursor
    return result,report

def codec(app):
    sys.path.insert(0,str(Path(__file__).parent/'vendor'))
    from draft_crypto import decrypt_draft_bytes, encrypt_draft_bytes
    def decode(data):
        try:
            return json.loads(data.decode('utf-8-sig'))
        except (UnicodeError,json.JSONDecodeError):
            return json.loads(decrypt_draft_bytes(data,jy_install_dir=Path(app),isolated=True))
    def encode(value, original):
        raw=json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()
        try:
            json.loads(original.decode('utf-8-sig'))
            return raw
        except (UnicodeError,json.JSONDecodeError):
            return encrypt_draft_bytes(raw,jy_install_dir=Path(app),isolated=True,validate_roundtrip=True)
    return decode,encode

def main():
    p=argparse.ArgumentParser()
    p.add_argument('mode',choices=['inspect','prepare'])
    p.add_argument('source');p.add_argument('--app',required=True)
    p.add_argument('--output',required=True);p.add_argument('--plan');p.add_argument('--destination')
    a=p.parse_args()
    source=Path(a.source).resolve(); output=Path(a.output).resolve()
    assert source != output and source not in output.parents, 'Output must be outside source draft'
    assert not output.exists(), 'Never overwrite a draft/output'
    decode,encode=codec(a.app)
    original=(source/'draft_content.json').read_bytes()
    content=decode(original)
    if a.mode=='inspect':
        write(output,content);return
    assert a.plan and a.destination
    destination=Path(a.destination).resolve()
    assert destination != source and not destination.exists(), 'Destination must be a new sibling draft'
    plan=read(a.plan)
    revised,report=retime(content,plan)
    meta_bytes=(source/'draft_meta_info.json').read_bytes()
    meta=decode(meta_bytes)
    nested=Path('Timelines')/content['id']/'draft_content.json'
    assert (source/nested).is_file(), 'Unknown draft layout; inspect instead of guessing'
    assert decode((source/nested).read_bytes()) == content, 'Root and timeline disagree; save/close app first'
    # Snapshot first; concurrent edits are checked again before producing the new copy.
    shutil.copytree(source,output)
    assert (source/'draft_content.json').read_bytes()==original, 'Source changed during snapshot'
    assert (source/'draft_meta_info.json').read_bytes()==meta_bytes, 'Source metadata changed'
    meta.update(draft_id=str(uuid.uuid4()).upper(),draft_name=destination.name,
                draft_fold_path=str(destination).replace('\\','/'),tm_duration=plan['total_us'])
    encoded=encode(revised,original); encoded_meta=encode(meta,meta_bytes)
    assert decode(encoded)==revised and decode(encoded_meta)==meta
    (output/'draft_content.json').write_bytes(encoded)
    (output/nested).write_bytes(encoded)
    (output/'draft_meta_info.json').write_bytes(encoded_meta)
    write(output.parent/(output.name+'.audit.json'),{'visuals':report,'source_sha256':hashlib.sha256(original).hexdigest(),
          'destination':str(destination),'draft_id':meta['draft_id'],'timeline_id':content['id'],
          'file_validation':'passed','registered':False,'in_app_validation':'not_performed'})
    print('Prepared new copy; registration and in-app verification are still required.')

if __name__=='__main__': main()
