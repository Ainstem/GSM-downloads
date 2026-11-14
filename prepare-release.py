#!/usr/bin/env python3
"""Import only the three explicitly selected, checksummed release files."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile


def validate_request(data):
    version=data.get('version','')
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?',version):
        raise ValueError('Invalid release version')
    expected={'linux':f'GSM-Linux-x86_64-{version}.run','windows':f'GSM-Setup-{version}.exe','sources':f'GSM-Linux-Media-Sources-{version}.tar.gz'}
    assets=data.get('assets',[])
    if len(assets)!=3 or {a.get('kind') for a in assets}!=set(expected):
        raise ValueError('Exactly the Linux installer, Windows installer and corresponding sources are required')
    for item in assets:
        if item.get('filename')!=expected[item['kind']]: raise ValueError('Unexpected asset filename')
        if not re.fullmatch(r'[a-f0-9]{64}',item.get('sha256','')):raise ValueError('Missing release file SHA256')
        parts=item.get('chunks')
        if parts:
            if item['kind']!='sources' or not 2<=len(parts)<=8:raise ValueError('Only corresponding sources may use a chunk transfer')
            for index,part in enumerate(parts):
                if part.get('filename')!=item['filename']+f'.part-{index:02d}':raise ValueError('Unexpected source chunk order')
        for part in parts or [item]:
            address=urllib.parse.urlsplit(part.get('url',''));host=address.hostname or ''
            if address.scheme!='https' or address.username or address.password or address.fragment or not(host=='github.com' or host.endswith('.oaiusercontent.com')):
                raise ValueError('Untrusted release transfer URL')
            for name in ['sha256']+(['archive_sha256'] if part.get('archive') else []):
                if not re.fullmatch(r'[a-f0-9]{64}',part.get(name,'')):raise ValueError('Missing SHA256 for release transfer')
    if not isinstance(data.get('notes'),str) or not data['notes'].strip():raise ValueError('Release notes are required')
    if len(data['notes'])>12000:raise ValueError('Release notes exceed channel size limit')
    if not re.fullmatch(r'[a-f0-9]{40}',data.get('source_commit','')):raise ValueError('Tested source commit is required')
    return expected


def copy_checked(source,destination,expected):
    digest=hashlib.sha256();total=0
    with destination.open('wb') as out:
        while chunk:=source.read(1024*1024):
            total+=len(chunk)
            if total>2147483648: raise ValueError('Release file exceeds size limit')
            digest.update(chunk);out.write(chunk)
    if digest.hexdigest()!=expected:
        destination.unlink(missing_ok=True);raise ValueError('Release file checksum mismatch: '+destination.name)


def materialize(item,directory,opener=urllib.request.urlopen):
    destination=directory/item['filename']
    if item.get('chunks'):
        with tempfile.TemporaryDirectory() as work:
            root=Path(work)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                futures=[pool.submit(materialize,part,root,opener) for part in item['chunks']]
                for future in futures:future.result()
            digest=hashlib.sha256();total=0
            with destination.open('wb') as out:
                for part in item['chunks']:
                    with (root/part['filename']).open('rb') as stream:
                        while chunk:=stream.read(1024*1024):
                            total+=len(chunk)
                            if total>2147483648:raise ValueError('Joined source archive exceeds size limit')
                            digest.update(chunk);out.write(chunk)
            if digest.hexdigest()!=item['sha256']:
                destination.unlink(missing_ok=True);raise ValueError('Reassembled source archive checksum mismatch')
        print('Verified reassembled '+destination.name+' '+item['sha256'],flush=True)
        return
    # The transfer grants access only to the intended public artifact; mask its temporary URL in CI logs.
    if os.environ.get('GITHUB_ACTIONS'):print('::add-mask::'+item['url'],flush=True)
    with tempfile.TemporaryDirectory() as work:
        downloaded=Path(work)/'transfer'
        with opener(item['url'],timeout=180) as response:
            copy_checked(response,downloaded,item['archive_sha256'] if item.get('archive') else item['sha256'])
        if item.get('archive'):
            with zipfile.ZipFile(downloaded) as archive:
                matches=[i for i in archive.infolist() if not i.is_dir() and Path(i.filename).name==item['filename']]
                if len(matches)!=1 or matches[0].file_size>2147483648:raise ValueError('Missing or ambiguous release file in artifact')
                with archive.open(matches[0]) as source:copy_checked(source,destination,item['sha256'])
        else:shutil.move(downloaded,destination)
    print('Verified '+destination.name+' '+item['sha256'],flush=True)


def main():
    request=json.loads(Path(sys.argv[1]).read_text());validate_request(request)
    directory=Path(sys.argv[2]);directory.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(materialize,item,directory) for item in request['assets']]
        for future in futures:future.result()
    metadata={'name':request.get('title','GSM '+request['version'])[:160],'body':request['notes']}
    Path('release-info.json').write_text(json.dumps(metadata,ensure_ascii=False)+'\n')
    Path('release-notes.md').write_text(request['notes']+'\n')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as out:out.write('tag=v'+request['version']+'\n')

if __name__=='__main__':main()
