"""Shared local configuration; independent of any agent vendor."""
import os
from pathlib import Path
from urllib.parse import urlparse
from dotenv import dotenv_values

SKILL_ROOT = Path(__file__).resolve().parents[1]

def runtime_root():
    explicit = os.environ.get('TEACHING_VIDEO_HOME')
    if explicit:
        return Path(explicit).expanduser().resolve()
    if os.name == 'nt':
        return Path(os.environ.get('LOCALAPPDATA', Path.home()/'AppData/Local'))/'TeachingVideoSkill'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))/'teaching-video-skill'

def ensure_config():
    root = runtime_root()
    root.mkdir(parents=True, exist_ok=True)
    path = root/'.env'
    if not path.exists():
        data = (SKILL_ROOT/'assets/config-template.txt').read_bytes()
        try:
            fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        except FileExistsError:
            return path
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
    return path

def valid_endpoint(endpoint):
    parsed = urlparse(endpoint)
    host = parsed.hostname or ''
    return (parsed.scheme == 'https' and not parsed.username and not parsed.password
            and not parsed.query and not parsed.fragment and parsed.port in (None,443)
            and host.endswith('.aliyuncs.com'))

def config():
    defaults = dict(dotenv_values(SKILL_ROOT/'assets/config-template.txt'))
    path = ensure_config()
    local = dict(dotenv_values(path))
    cfg = {**defaults, **local}
    region = cfg.get('BAILIAN_REGION') or 'cn-beijing'
    bases = {'cn-beijing':'https://dashscope.aliyuncs.com',
             'ap-southeast-1':'https://dashscope-intl.aliyuncs.com'}
    if region not in bases:
        raise ValueError('Unsupported BAILIAN_REGION; configure a documented region first')
    base = (cfg.get('BAILIAN_BASE_URL') or bases[region]).rstrip('/')
    if not valid_endpoint(base):
        raise ValueError('BAILIAN_BASE_URL must be an Alibaba Cloud HTTPS base URL')
    routes = {'TTS_ENDPOINT':'/api/v1/services/audio/tts/SpeechSynthesizer',
              'ASR_ENDPOINT':'/api/v1/services/aigc/multimodal-generation/generation',
              'IMAGE_ENDPOINT':'/api/v1/services/aigc/multimodal-generation/generation'}
    for key, route in routes.items():
        cfg[key] = (cfg.get(key) or base+route).strip()
        if not valid_endpoint(cfg[key]):
            raise ValueError(key+' must be an Alibaba Cloud HTTPS endpoint')
    return cfg
