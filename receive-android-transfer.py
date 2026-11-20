"""Receive a checksum-pinned private Android build and signing material."""
import base64,hashlib,json,os,re,time,urllib.request,urllib.error
from pathlib import Path
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa,padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def decode(key,response,revision,fingerprint,source,source_only=False):
    if response.get('request_commit')!=revision or response.get('key_sha256')!=fingerprint: raise ValueError('Wrong transfer request or key')
    aes=key.decrypt(base64.b64decode(response['wrapped_key'],validate=True),padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
    nonce=base64.b64decode(response['nonce'],validate=True);cipher=base64.b64decode(response['ciphertext'],validate=True)
    if len(aes)!=32 or len(nonce)!=12 or len(cipher)>32768:raise ValueError('Invalid transfer size')
    result=json.loads(AESGCM(aes).decrypt(nonce,cipher,revision.encode()))
    expected={'source_commit','source_url'} if source_only else {'source_commit','source_url','keystore_base64','store_password','alias'}
    if set(result)!=expected or result['source_commit']!=source:raise ValueError('Unexpected build payload')
    return result

def main():
    repo=os.environ['GITHUB_REPOSITORY'];revision=os.environ['GITHUB_SHA'];request=json.loads(Path('android-build-request.json').read_text())
    if repo!='Ainstem/GSM-downloads' or not re.fullmatch('[a-f0-9]{40}',revision):raise ValueError('Unexpected repository')
    headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','User-Agent':'GSM-Android-build'}
    def api(method,path,data=None):
        with urllib.request.urlopen(urllib.request.Request('https://api.github.com/repos/'+repo+path,headers=headers,data=None if data is None else json.dumps(data).encode(),method=method),timeout=60) as f:return json.load(f)
    key=rsa.generate_private_key(public_exponent=65537,key_size=4096)
    pem=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo);fingerprint=hashlib.sha256(pem).hexdigest()
    value={'request_commit':revision,'run_id':os.environ['GITHUB_RUN_ID'],'key_sha256':fingerprint,'public_key':pem.decode()}
    path='/contents/android-transfer-public-key.json';body={'message':'Prepare protected Android build transfer','branch':'main','content':base64.b64encode(json.dumps(value).encode()).decode()}
    try:body['sha']=api('GET',path)['sha']
    except urllib.error.HTTPError as e:
        if e.code!=404:raise
    api('PUT',path,body);print('Protected Android transfer ready',flush=True)
    for _ in range(120):
        try:response=json.loads(base64.b64decode(api('GET','/contents/android-transfer-response.json')['content']))
        except urllib.error.HTTPError as e:
            if e.code!=404:raise
            response={}
        if response.get('request_commit')==revision:
            payload=decode(key,response,revision,fingerprint,request['source_commit'],os.environ.get('GSM_SOURCE_ONLY')=='1')
            for name in ['source_url','keystore_base64','store_password']:
                if name in payload:print('::add-mask::'+payload[name],flush=True)
            fd=os.open('android-private-build.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as f:json.dump(payload,f)
            print('Protected build transfer received',flush=True);return
        time.sleep(5)
    raise TimeoutError('No matching Android transfer')
if __name__=='__main__':main()
