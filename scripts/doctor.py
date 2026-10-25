"""No network requests or credential output; reports capabilities separately."""
import argparse
import importlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--health-only', action='store_true')
    args = parser.parse_args()
    problems = []
    if sys.version_info[:2] != (3,11):
        problems.append('python_3_11_required')
    for name in ('requests','dotenv','PIL','yaml'):
        try: importlib.import_module(name)
        except ImportError: problems.append('missing_'+name)
    for binary in ('ffmpeg','ffprobe'):
        path = shutil.which(binary)
        if not path:
            problems.append('missing_'+binary)
        else:
            try:
                result = subprocess.run([path,'-version'],capture_output=True,timeout=15)
                if result.returncode: problems.append(binary+'_not_runnable')
            except (OSError,subprocess.TimeoutExpired): problems.append(binary+'_not_runnable')
    result = {'local_ready':not problems,'problems':problems,'python':platform.python_version(),
              'cloud_tested':False,'browser_connected':'agent_must_verify'}
    if not args.health_only and not problems:
        from settings import config, ensure_config
        cfg=config()
        result.update(config_file=str(ensure_config()),credential_present=bool(cfg.get('DASHSCOPE_API_KEY')),
                      image_provider=cfg.get('IMAGE_PROVIDER'),browser_preference=cfg.get('BROWSER'))
        candidates=[]
        if os.name=='nt':
            for base in (os.environ.get('PROGRAMFILES',''),os.environ.get('PROGRAMFILES(X86)',''),os.environ.get('LOCALAPPDATA','')):
                if base:
                    candidates += [Path(base)/'Google/Chrome/Application/chrome.exe',
                                   Path(base)/'Microsoft/Edge/Application/msedge.exe']
        else:
            candidates += [Path('/Applications/Google Chrome.app'),Path('/Applications/Microsoft Edge.app')]
        result['browser_installations_found']=[p.name for p in candidates if p.exists()]
        result['browser_commands_found']=[n for n in ('google-chrome','chromium','microsoft-edge') if shutil.which(n)]
        result['next_step']='connect_browser_or_choose_image_provider' if cfg.get('DASHSCOPE_API_KEY') else 'fill_local_env_then_choose_image_provider'
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if not problems else 1

if __name__=='__main__':
    try: sys.exit(main())
    except Exception as exc:
        print(json.dumps({'local_ready':False,'error_type':type(exc).__name__,'next_step':'inspect_local_config_and_recovery_guide'}))
        sys.exit(1)
