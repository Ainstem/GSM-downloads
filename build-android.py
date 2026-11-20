"""Fetch only the mobile subtree and sign the bundled release without logging secrets."""
import base64,hashlib,json,os,subprocess,sys,tarfile,tempfile,urllib.request,zipfile
from pathlib import Path,PurePosixPath
from urllib.parse import urlparse
request=json.loads(Path('android-build-request.json').read_text())
private=json.loads(Path('android-private-build.json').read_text())
if sys.argv[1]=='fetch':
    if urlparse(private['source_url']).hostname!='codeload.github.com':raise ValueError('Unexpected source host')
    target=Path('source/mobile');target.mkdir(parents=True)
    with tempfile.TemporaryFile() as archive:
        digest=hashlib.sha256();size=0
        with urllib.request.urlopen(private['source_url'],timeout=90) as f:
            while chunk:=f.read(1024*1024):
                size+=len(chunk)
                if size>100*1024*1024:raise ValueError('Source too large')
                digest.update(chunk);archive.write(chunk)
        if digest.hexdigest()!=request['source_sha256']:raise ValueError('Source checksum mismatch')
        archive.seek(0)
        with tarfile.open(fileobj=archive,mode='r:gz') as tar:
            for entry in tar:
                p=PurePosixPath(entry.name)
                if len(p.parts)<3 or p.parts[1]!='mobile':continue
                relative=PurePosixPath(*p.parts[2:])
                if relative.is_absolute() or '..' in relative.parts or entry.issym() or entry.islnk():raise ValueError('Unsafe archive entry')
                if any(x in relative.parts for x in ['node_modules','.git','.env']) or relative.suffix in ['.jks','.keystore']:raise ValueError('Unexpected source entry')
                out=target/str(relative)
                if entry.isdir():out.mkdir(parents=True,exist_ok=True)
                elif entry.isfile():
                    out.parent.mkdir(parents=True,exist_ok=True)
                    with tar.extractfile(entry) as src,out.open('wb') as dst:
                        while chunk:=src.read(1024*1024):dst.write(chunk)
                    out.chmod(entry.mode&0o777)
    print('Verified mobile source extracted')
elif sys.argv[1]=='sign':
    sdk=Path(os.environ['ANDROID_HOME'])/'build-tools/36.0.0';candidate='source/mobile/android/app/build/outputs/apk/release/app-release.apk';output='GSM-Android-0.2.0-alpha.apk'
    with tempfile.TemporaryDirectory() as d:
        key=Path(d)/'release.jks';key.write_bytes(base64.b64decode(private['keystore_base64'],validate=True));key.chmod(0o600)
        env=dict(os.environ,GSM_ANDROID_SIGN_PASSWORD=private['store_password'])
        subprocess.run([str(sdk/'apksigner'),'sign','--ks',str(key),'--ks-key-alias',private['alias'],'--ks-pass','env:GSM_ANDROID_SIGN_PASSWORD','--key-pass','env:GSM_ANDROID_SIGN_PASSWORD','--out',output,candidate],env=env,check=True)
    verified=subprocess.check_output([str(sdk/'apksigner'),'verify','--verbose','--print-certs',output],text=True)
    if request['certificate_sha256'] not in verified:raise ValueError('Unexpected signing certificate')
    manifest=subprocess.check_output([str(sdk/'aapt'),'dump','badging',output],text=True)
    for token in ["name='app.gsm.mobile'","versionName='0.2.0'","versionCode='2'"]:
        if token not in manifest:raise ValueError('Unexpected Android manifest')
    with zipfile.ZipFile(output) as z:
        if 'assets/index.android.bundle' not in z.namelist():raise ValueError('No offline JavaScript bundle')
        for abi in ['armeabi-v7a','arm64-v8a','x86_64']:
            if not any(n.startswith('lib/'+abi+'/') for n in z.namelist()):raise ValueError('Missing ABI')
    digest=hashlib.sha256(Path(output).read_bytes()).hexdigest();Path('SHA256SUMS-Android.txt').write_text(digest+'  '+output+'\n')
    Path('android-private-build.json').unlink();print('Release signature, package, native ABIs and embedded bundle verified. APK SHA256:',digest)
else:raise ValueError('Unknown operation')
