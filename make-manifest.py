#!/usr/bin/env python3
import hashlib,json,re,sys
from pathlib import Path
version=sys.argv[1].removeprefix('v')
if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?',version):
    raise SystemExit('Invalid version tag')
root=Path(sys.argv[2])
files={'linux-x86_64':f'GSM-Linux-x86_64-{version}.run','windows-x64':f'GSM-Setup-{version}.exe'}
manifest={'version':version,'platforms':{}};checksums=[]
for platform,name in files.items():
    with (root/name).open('rb') as stream:
        digest=hashlib.file_digest(stream,'sha256').hexdigest()
    manifest['platforms'][platform]={'url':f'https://github.com/Ainstem/GSM-downloads/releases/download/v{version}/{name}','sha256':digest}
    checksums.append(f'{digest}  {name}')
Path('update.json').write_text(json.dumps(manifest,indent=2)+'\n')
Path('SHA256SUMS').write_text('\n'.join(checksums)+'\n')
