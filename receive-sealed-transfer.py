#!/usr/bin/env python3
"""Receive temporary asset URLs without placing bearer URLs in public metadata.

The RSA private key exists only in the publication runner's memory. The public
repository receives the public key and an authenticated encrypted response.
"""
import base64
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def decode(private_key, response, request, revision, fingerprint):
    if response.get('request_commit') != revision or response.get('key_sha256') != fingerprint:
        raise ValueError('Transfer response belongs to another request/key')
    key = private_key.decrypt(base64.b64decode(response['wrapped_key'], validate=True), padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    nonce = base64.b64decode(response['nonce'], validate=True)
    ciphertext = base64.b64decode(response['ciphertext'], validate=True)
    if len(key) != 32 or len(nonce) != 12 or len(ciphertext) > 32768:
        raise ValueError('Invalid encrypted transfer size')
    urls = json.loads(AESGCM(key).decrypt(nonce, ciphertext, revision.encode()))
    if set(urls) != {item['filename'] for item in request['assets']}:
        raise ValueError('Unexpected transfer asset list')
    result = dict(request, assets=[dict(item, url=urls[item['filename']], archive=False) for item in request['assets']])
    for item in result['assets']:
        if not isinstance(item['url'], str) or len(item['url']) > 8192:
            raise ValueError('Invalid transfer URL')
    return result


def main():
    request = json.loads(Path('publish-request.json').read_text())
    repository = os.environ['GITHUB_REPOSITORY']
    revision = os.environ['GITHUB_SHA']
    if repository != 'Ainstem/GSM-downloads' or not request.get('sealed_transfer') or not re.fullmatch('[a-f0-9]{40}', revision):
        raise ValueError('Unexpected publication request')
    headers = {'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json', 'User-Agent': 'GSM-sealed-publication'}
    def api(method, path, data=None):
        body = None if data is None else json.dumps(data).encode()
        with urllib.request.urlopen(urllib.request.Request('https://api.github.com/repos/' + repository + path, headers=headers, data=body, method=method), timeout=60) as response:
            return json.load(response)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    pem = private_key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    fingerprint = hashlib.sha256(pem).hexdigest()
    public = {'request_commit': revision, 'run_id': os.environ['GITHUB_RUN_ID'], 'key_sha256': fingerprint, 'public_key': pem.decode()}
    path = '/contents/publication-transfer-public-key.json'
    body = {'message': 'Prepare sealed publication transfer', 'branch': 'main', 'content': base64.b64encode((json.dumps(public, indent=2) + '\n').encode()).decode()}
    try:
        body['sha'] = api('GET', path)['sha']
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    api('PUT', path, body)
    print('Sealed transfer ready for request', revision, flush=True)
    for _ in range(90):
        try:
            item = api('GET', '/contents/publication-transfer-response.json')
            response = json.loads(base64.b64decode(item['content']))
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
            response = {}
        if response.get('request_commit') == revision:
            result = decode(private_key, response, request, revision, fingerprint)
            for asset in result['assets']:
                print('::add-mask::' + asset['url'], flush=True)
            output = Path('sealed-transfer-request.json')
            output.write_text(json.dumps(result))
            output.chmod(0o600)
            print('Authenticated transfer received for three checksum-pinned assets.', flush=True)
            return
        time.sleep(5)
    raise TimeoutError('No matching encrypted transfer response received')

if __name__ == '__main__':
    main()
