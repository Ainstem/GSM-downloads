import hashlib,json,os,subprocess,zipfile
from pathlib import Path
request=json.loads(Path('android-validation-request.json').read_text());path=Path('GSM-Android-0.2.0-alpha.apk');digest=hashlib.sha256(path.read_bytes()).hexdigest()
if digest!=request['candidate_sha256']:raise ValueError('Candidate checksum mismatch')
if Path('SHA256SUMS-Android.txt').read_text().split()[0]!=digest:raise ValueError('Candidate checksum manifest mismatch')
sdk=Path(os.environ['ANDROID_HOME'])/'build-tools/36.0.0'
cert=subprocess.check_output([str(sdk/'apksigner'),'verify','--verbose','--print-certs',str(path)],text=True)
expected=json.loads(Path('android-build-request.json').read_text())
if expected['certificate_sha256'] not in cert:raise ValueError('Unexpected signer')
manifest=subprocess.check_output([str(sdk/'aapt'),'dump','badging',str(path)],text=True)
for token in ["name='app.gsm.mobile'","versionName='0.2.0'","versionCode='2'"]:
 if token not in manifest:raise ValueError('Unexpected package')
if 'application-debuggable' in manifest:raise ValueError('Debug app is not a release')
with zipfile.ZipFile(path) as z:
 if 'assets/index.android.bundle' not in z.namelist():raise ValueError('No bundled code')
 for abi in ['armeabi-v7a','arm64-v8a','x86_64']:
  if not any(n.startswith('lib/'+abi+'/') for n in z.namelist()):raise ValueError('Missing native architecture')
print('PASS: exact preserved candidate, production signature, release manifest and bundled code')
