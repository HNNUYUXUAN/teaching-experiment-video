"""Bailian audio pipeline. All generated artifacts stay in the chosen output folder."""
from __future__ import annotations
import argparse
import base64
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unicodedata
import wave
import requests
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]

def config():
    from settings import config as load_config
    return load_config()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, path)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def audio(path):
    with wave.open(str(path), 'rb') as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise ValueError('Expected mono PCM16 WAV; normalize first')
        return w.getframerate(), w.readframes(w.getnframes())

def wav(path, rate, pcm):
    with wave.open(str(path), 'wb') as w:
        w.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        w.writeframes(pcm)

def normalize(source, destination, rate):
    subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-y', '-i', str(source),
                    '-ac', '1', '-ar', str(rate), '-c:a', 'pcm_s16le', str(destination)], check=True)

def post(endpoint, payload, cfg):
    key = (cfg.get('DASHSCOPE_API_KEY') or '').strip()
    if not key:
        raise ValueError('Fill DASHSCOPE_API_KEY in the dedicated runtime .env; no API call made')
    if not endpoint.startswith('https://') or not re.match(r'^https://[\w.-]+\.aliyuncs\.com/', endpoint):
        raise ValueError('Endpoint must be an explicit Alibaba Cloud HTTPS endpoint')
    try:
        response = requests.post(endpoint, json=payload, headers={
            'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json',
            'X-DashScope-SSE': 'disable'}, timeout=int(cfg['HTTP_TIMEOUT_SECONDS']))
    except requests.RequestException:
        raise RuntimeError('API transport outcome uncertain; inspect pending marker before retrying') from None
    if response.status_code != 200:
        raise RuntimeError(f'Bailian HTTP {response.status_code}; inspect account/endpoint; no automatic paid retry')
    result = response.json()
    if 'output' not in result:
        raise RuntimeError('Bailian returned no output; no automatic retry')
    return result

def tts(text, destination, cfg):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {'model': cfg['TTS_MODEL'], 'input': {'text': text,
        'voice': cfg['TTS_VOICE'], 'format': 'wav', 'sample_rate': int(cfg['TTS_SAMPLE_RATE']),
        'volume': int(cfg['TTS_VOLUME']), 'rate': float(cfg['TTS_RATE']),
        'pitch': float(cfg['TTS_PITCH']), 'seed': int(cfg['TTS_SEED']),
        'language_hints': ['zh'], 'instruction': cfg['TTS_INSTRUCTION']}}
    identity = fingerprint({'endpoint': cfg['TTS_ENDPOINT'], 'payload': payload})
    metadata = destination.with_suffix('.tts.json')
    pending = destination.with_suffix('.pending.json')
    if destination.exists() and metadata.exists():
        previous = read(metadata)
        if previous['identity'] == identity and previous['sha256'] == sha(destination):
            return
        raise ValueError('Existing TTS output differs; choose a new version directory')
    if destination.exists() or pending.exists():
        raise ValueError('Unfinished/existing TTS output; inspect before retrying to avoid duplicate billing')
    if not cfg.get('DASHSCOPE_API_KEY'):
        raise ValueError('DASHSCOPE_API_KEY is empty; no API call made')
    write(pending, {'identity': identity, 'state': 'request_started'})
    result = post(cfg['TTS_ENDPOINT'], payload, cfg)
    url = result['output']['audio']['url']
    # Temporary signed URL is consumed immediately and never written to reports.
    try:
        response = requests.get(url, timeout=int(cfg['HTTP_TIMEOUT_SECONDS']))
        response.raise_for_status()
    except requests.RequestException:
        raise RuntimeError('TTS audio download failed; synthesis may have been billed; inspect pending marker') from None
    with tempfile.TemporaryDirectory(prefix='jy-tts-') as temp:
        raw = Path(temp) / 'raw.wav'
        raw.write_bytes(response.content)
        normalized = Path(temp) / 'normalized.wav'
        normalize(raw, normalized, int(cfg['TTS_SAMPLE_RATE']))
        audio(normalized)
        destination.write_bytes(normalized.read_bytes())
    write(metadata, {'identity': identity, 'sha256': sha(destination),
                     'request_id': result.get('request_id'), 'usage': result.get('usage')})
    pending.unlink()

def assemble(manifest_path, out, cfg, synthesize=False):
    manifest_path = Path(manifest_path).resolve()
    spec = read(manifest_path)
    out = Path(out).resolve()
    if out.exists():
        raise FileExistsError('Use a new output directory; existing package is preserved')
    segments = spec['segments']
    if not segments or len({s['id'] for s in segments}) != len(segments):
        raise ValueError('Segments must be nonempty with unique IDs')
    out.mkdir(parents=True)
    rate = int(cfg['TTS_SAMPLE_RATE'])
    all_pcm, positions, cursor = [], [], 0
    for number, item in enumerate(segments, 1):
        if not item.get('text', '').strip():
            raise ValueError('Each narration segment needs authoritative text')
        (out / 'audit').mkdir(exist_ok=True)
        (out / 'audio').mkdir(exist_ok=True)
        raw = out / 'audit' / f'{number:02d}_speech.wav'
        if synthesize:
            tts(item['text'], raw, cfg)
        else:
            source = (manifest_path.parent / item['audio']).resolve()
            normalize(source, raw, rate)
        _, pcm = audio(raw)
        spoken_frames = len(pcm) // 2
        lead = round(float(item.get('lead_ms', 0)) * rate / 1000)
        trail = round(float(item.get('tail_ms', 0)) * rate / 1000)
        if min(lead, trail) < 0:
            raise ValueError('Negative silence is not allowed')
        needed = lead + spoken_frames + trail
        requested = round(float(item.get('slot_ms', 0)) * rate / 1000)
        if requested and requested < needed:
            raise ValueError(f'{item["id"]}: speech exceeds slot; expand timeline or revise narration, never truncate')
        total = max(needed, requested)
        padded = bytes(lead * 2) + pcm + bytes((total - lead - spoken_frames) * 2)
        target = out / 'audio' / f'{number:02d}_narration.wav'
        wav(target, rate, padded)
        positions.append({'id': item['id'], 'text': item['text'], 'audio': str(raw),
                          'import_audio': str(target), 'audio_sha256': sha(raw),
                          'start_frame': cursor, 'frames': total, 'speech_start_frame': cursor + lead,
                          'speech_frames': spoken_frames, 'sample_rate': rate,
                          'equivalences': item.get('equivalences', {})})
        all_pcm.append(padded)
        cursor += total
    wav(out / 'continuous.wav', rate, b''.join(all_pcm))
    write(out / 'placement.json', {'sample_rate': rate, 'total_frames': cursor,
                                  'segments': positions, 'master_sha256': sha(out / 'continuous.wav')})
    return out / 'placement.json'

def asr(placement, cfg):
    data = read(placement)
    for item in data['segments']:
        path = Path(item['audio'])
        if sha(path) != item['audio_sha256']:
            raise ValueError('Audio changed since assembly')
        rate, pcm = audio(path)
        if len(pcm) / 2 / rate > float(cfg['ASR_MAX_SECONDS']):
            raise ValueError('Segment exceeds configured ASR duration; split at semantic silence and rebuild placement')
        encoded = base64.b64encode(path.read_bytes()).decode('ascii')
        if len(encoded) + 32 > int(cfg['ASR_MAX_BYTES']):
            raise ValueError('Base64 audio exceeds configured payload limit')
        payload = {'model': cfg['ASR_MODEL'], 'input': {'messages': [{'role': 'user',
            'content': [{'type': 'input_audio', 'input_audio': {'data': 'data:audio/wav;base64,' + encoded}}]}]},
            'parameters': {'format': 'wav', 'sample_rate': str(rate), 'speaker_diarization_enabled': True}}
        identity = fingerprint({'audio': sha(path), 'model': cfg['ASR_MODEL'], 'endpoint': cfg['ASR_ENDPOINT']})
        target = path.with_suffix('.asr.json')
        pending = path.with_suffix('.asr-pending.json')
        if target.exists():
            if read(target)['identity'] != identity:
                raise ValueError('ASR cache mismatch; use a new version')
            continue
        if pending.exists():
            raise ValueError('Previous ASR outcome uncertain; inspect before retry')
        if not cfg.get('DASHSCOPE_API_KEY'):
            raise ValueError('DASHSCOPE_API_KEY is empty; no API call made')
        write(pending, {'identity': identity})
        result = post(cfg['ASR_ENDPOINT'], payload, cfg)
        write(target, {'identity': identity, 'audio_sha256': sha(path), 'model': cfg['ASR_MODEL'], 'response': result})
        pending.unlink()

def content(char):
    return unicodedata.category(char)[0] in ('L', 'N')

def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKC', text) if content(c)).lower()

def tokens(response, equivalences=None):
    result = response['output']
    sentences = result.get('sentences') or result.get('sentence') or []
    if isinstance(sentences, dict):
        sentences = [sentences]
    chars = []
    for sentence in sentences:
        for word in sentence.get('words', []):
            value = normalized(str(word['text']))
            start, end = int(word['begin_time']), int(word['end_time'])
            if start < 0 or end < start or word.get('fixed') is False:
                raise ValueError('Unstable/invalid word timestamps')
            for index, char in enumerate(value):
                chars.append({'char': char, 'start': round(start + (end-start)*index/len(value)),
                              'end': round(start + (end-start)*(index+1)/len(value)),
                              'provenance': 'native_word' if len(value)==1 else 'within_word_interpolation'})
    # Explicit user-reviewed equivalences only; record that timestamps span the original tokens.
    for before, after in (equivalences or {}).items():
        before, after = normalized(before), normalized(after)
        if not before or not after:
            raise ValueError('Empty equivalence is not permitted')
        cursor = 0
        while cursor < len(chars):
            text = ''.join(x['char'] for x in chars)
            index = text.find(before, cursor)
            if index < 0:
                break
            start, end = chars[index]['start'], chars[index+len(before)-1]['end']
            mapped = [{'char': c, 'start': round(start+(end-start)*i/len(after)),
                       'end': round(start+(end-start)*(i+1)/len(after)),
                       'provenance': 'reviewed_equivalence_interpolation'} for i,c in enumerate(after)]
            chars[index:index+len(before)] = mapped
            cursor = index + len(mapped)
    if not chars:
        raise ValueError('No word timestamps; sentence-only timing is insufficient')
    if any(a['start'] > b['start'] for a,b in zip(chars, chars[1:])):
        raise ValueError('Nonmonotonic ASR timestamps')
    return chars

def stamp(ms):
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

def align(placement, cfg):
    path = Path(placement)
    if (path.parent / 'captions.srt').exists():
        raise FileExistsError('Existing SRT preserved; create a new package version before realignment')
    data = read(path)
    cues, audit, differences = [], [], []
    split_warnings = []
    for item in data['segments']:
        if sha(item['audio']) != item['audio_sha256']:
            raise ValueError('Current WAV does not match placement')
        stored = read(Path(item['audio']).with_suffix('.asr.json'))
        if stored['audio_sha256'] != item['audio_sha256']:
            raise ValueError('ASR response belongs to different audio')
        chars = tokens(stored['response'], item.get('equivalences'))
        text = re.sub(r'\s+', '', item['text'])
        expected, actual = normalized(text), ''.join(c['char'] for c in chars)
        if expected != actual:
            differences.append({'id': item['id'], 'expected': expected, 'recognized': actual,
                                'diff': list(difflib.ndiff(expected, actual))})
            continue
        offset = round(item['speech_start_frame'] * 1000 / item['sample_rate'])
        limit = round(item['speech_frames'] * 1000 / item['sample_rate'])
        if chars[-1]['end'] > limit + 30:
            raise ValueError('ASR timestamps exceed actual speech WAV')
        audit.append({'id': item['id'], 'chars': chars, 'offset_ms': offset,
                      'equivalences': item.get('equivalences', {})})
        # Pack complete clauses first. Only split inside a clause if unavoidable, and flag it.
        clauses, cursor = [], 0
        for phrase in re.findall(r'[^，,。！？；!?;]+[，,。！？；!?;]*', text):
            units = []
            for char in phrase:
                count = len(normalized(char))
                timing = chars[cursor:cursor+count]
                units.append((char,timing))
                cursor += count
            clauses.append(units)
        assert cursor == len(chars), 'Caption character coverage mismatch'
        buf = []
        def timed(units): return [t for _,ts in units for t in ts]
        def fits(units):
            ts=timed(units)
            return len(units)<=int(cfg['SUBTITLE_MAX_CHARS']) and (not ts or ts[-1]['end']-ts[0]['start']<=int(cfg['SUBTITLE_MAX_MS']))
        def emit(units):
            ts=timed(units)
            if ts:
                cues.append({'text':''.join(c for c,_ in units),'start_ms':offset+ts[0]['start'],'end_ms':offset+ts[-1]['end']})
        for clause in clauses:
            if buf and not fits(buf+clause): emit(buf);buf=[]
            for unit in clause:
                if buf and not fits(buf+[unit]):
                    split_warnings.append({'cue':len(cues)+1,'reason':'within_clause_split_needs_semantic_review'})
                    emit(buf);buf=[]
                buf.append(unit)
            if buf and buf[-1][0] in '。！？；!?;': emit(buf);buf=[]
        emit(buf)
    write(path.parent / 'alignment-audit.json', {'segments': audit, 'differences': differences})
    if differences:
        raise ValueError('Transcript differs from narration: review alignment-audit.json; SRT not exported')
    warnings = split_warnings
    for index, cue in enumerate(cues):
        if index+1 < len(cues):
            cue['end_ms'] = min(cue['end_ms'], cues[index+1]['start_ms']-int(cfg['SUBTITLE_GAP_MS']))
        duration = cue['end_ms']-cue['start_ms']
        if duration <= 0:
            raise ValueError('ASR boundaries cannot support nonoverlapping captions')
        if duration < int(cfg['SUBTITLE_MIN_MS']) or duration > int(cfg['SUBTITLE_MAX_MS']):
            warnings.append({'cue':index+1, 'duration_ms':duration, 'reason':'manual_readability_review'})
    output = '\n\n'.join(f'{i}\n{stamp(c["start_ms"])} --> {stamp(c["end_ms"])}\n{c["text"]}' for i,c in enumerate(cues,1))+'\n'
    (path.parent/'captions.srt').write_text(output, encoding='utf-8-sig')
    write(path.parent/'caption-report.json', {'cues':cues, 'warnings':warnings,
          'ready_for_import':not warnings, 'single_line':True, 'timing_source':'ASR word timestamps with labeled interpolation'})
    return cues

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('assemble','synthesize'):
        p = sub.add_parser(command); p.add_argument('manifest'); p.add_argument('output')
    for command in ('asr','align'):
        p = sub.add_parser(command); p.add_argument('placement')
    sub.add_parser('doctor')
    args = parser.parse_args()
    cfg = config()
    if args.command == 'doctor':
        print(json.dumps({'credential_present':bool(cfg.get('DASHSCOPE_API_KEY')), 'tts_model':cfg['TTS_MODEL'],
                          'asr_model':cfg['ASR_MODEL'], 'api_called':False}, ensure_ascii=False)); return
    if args.command in ('assemble','synthesize'):
        print(assemble(args.manifest,args.output,cfg,args.command=='synthesize'))
    elif args.command == 'asr': asr(args.placement,cfg)
    else: print(f'cues={len(align(args.placement,cfg))}')

if __name__ == '__main__':
    main()
