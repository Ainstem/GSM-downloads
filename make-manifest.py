#!/usr/bin/env python3
import hashlib,json,re,sys
from pathlib import Path
version=sys.argv[1].removeprefix('v')
if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?',version):
    raise SystemExit('Invalid version tag')
root=Path(sys.argv[2])
source=root/f'GSM-Linux-Media-Sources-{version}.tar.gz'
if not source.is_file(): raise SystemExit('Corresponding media sources must be published with the installers')
files={'linux-x86_64':f'GSM-Linux-x86_64-{version}.run','windows-x64':f'GSM-Setup-{version}.exe'}
metadata=json.loads(Path(sys.argv[3]).read_text()) if len(sys.argv)>3 else {}
manifest={'version':version,'release_title':str(metadata.get('name') or metadata.get('title') or '')[:160],
          'release_notes':str(metadata.get('body') or '')[:12000],'platforms':{}};checksums=[]
for platform,name in files.items():
    with (root/name).open('rb') as stream:
        digest=hashlib.file_digest(stream,'sha256').hexdigest()
    manifest['platforms'][platform]={'url':f'https://github.com/Ainstem/GSM-downloads/releases/download/v{version}/{name}','sha256':digest}
    checksums.append(f'{digest}  {name}')
with source.open('rb') as stream: checksums.append(hashlib.file_digest(stream,'sha256').hexdigest()+'  '+source.name)
Path('update.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
Path('SHA256SUMS').write_text('\n'.join(checksums)+'\n')
