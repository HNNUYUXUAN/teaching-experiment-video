"""Read-only native codec round-trip check. No live draft files are written."""
import argparse
import hashlib
import json
from pathlib import Path
from draft_ops import codec
from pipeline import write

p=argparse.ArgumentParser()
p.add_argument('draft');p.add_argument('--app',required=True);p.add_argument('--report',required=True)
a=p.parse_args()
path=Path(a.draft)
original=path.read_bytes()
decode,encode=codec(a.app)
value=decode(original)
reencoded=encode(value,original)
assert decode(reencoded)==value
assert path.read_bytes()==original
write(a.report,{'native_roundtrip':'passed','source_unchanged':True,
      'source_sha256':hashlib.sha256(original).hexdigest(), 'app':str(Path(a.app).resolve()),
      'in_app_validation':'not_performed'})
print('PASS native codec round-trip; source unchanged; no in-app validation')
