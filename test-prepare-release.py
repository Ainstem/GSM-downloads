import importlib.util,tempfile,pathlib,zipfile,hashlib,io,unittest,json,subprocess,sys
spec=importlib.util.spec_from_file_location('transfer',str(pathlib.Path(__file__).parent/'prepare-release.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Test(unittest.TestCase):
 def fixture(self):
  assets=[]
  for kind,name in [('linux','GSM-Linux-x86_64-0.6.0-alpha.run'),('windows','GSM-Setup-0.6.0-alpha.exe'),('sources','GSM-Linux-Media-Sources-0.6.0-alpha.tar.gz')]:
   assets.append({'kind':kind,'filename':name,'sha256':'a'*64,'url':'https://github.com/Ainstem/GSM-downloads/releases/download/v0.6.0-alpha/'+name})
  return {'version':'0.6.0-alpha','notes':'## Novidades\n- Perfil 🎮','source_commit':'a'*40,'assets':assets}
 def test_request(self):self.assertEqual(len(m.validate_request(self.fixture())),3)
 def windows_fixture(self):
  data=self.fixture();data['version']='0.10.2-alpha.windows.1';data['target_platforms']=['windows-x64'];data['assets']=[data['assets'][1]]
  data['assets'][0]['filename']='GSM-Setup-0.10.2-alpha.windows.1.exe'
  return data
 def test_explicit_windows_hotfix(self):self.assertEqual(set(m.validate_request(self.windows_fixture())),{'windows'})
 def test_windows_hotfix_requires_scope_and_matching_revision(self):
  for value in [None,[],['linux-x86_64'],['windows-x64','linux-x86_64']]:
   data=self.windows_fixture();data['target_platforms']=value
   with self.assertRaises(ValueError):m.validate_request(data)
  data=self.windows_fixture();data['version']='0.10.3-alpha'
  with self.assertRaises(ValueError):m.validate_request(data)
 def test_windows_hotfix_manifest_does_not_offer_linux_an_update(self):
  script=pathlib.Path(__file__).parent.resolve()/'make-manifest.py'
  with tempfile.TemporaryDirectory() as directory:
   root=pathlib.Path(directory);installer=root/'GSM-Setup-0.10.2-alpha.windows.1.exe';installer.write_bytes(b'MZchecked installer')
   (root/'metadata.json').write_text(json.dumps({'target_platforms':['windows-x64'],'name':'GSM Windows hotfix','body':'Windows only; Linux remains on 0.10.2-alpha.'}))
   subprocess.run([sys.executable,str(script),'v0.10.2-alpha.windows.1',str(root),str(root/'metadata.json')],cwd=root,check=True)
   manifest=json.loads((root/'update.json').read_text());self.assertEqual(set(manifest['platforms']),{'windows-x64'})
   self.assertEqual(manifest['version'],'0.10.2-alpha.windows.1');self.assertEqual(manifest['platforms']['windows-x64']['sha256'],hashlib.sha256(installer.read_bytes()).hexdigest())
   self.assertEqual(len((root/'SHA256SUMS').read_text().splitlines()),1)
 def test_signed_github_asset_host_allowed(self):
  data=self.fixture();data['assets'][0]['url']='https://release-assets.githubusercontent.com/github-production-release-asset/selected?sig=temporary'
  self.assertEqual(len(m.validate_request(data)),3)
 def test_github_asset_lookalike_refused(self):
  for host in ['release-assets.githubusercontent.com.evil.example','evil-release-assets.githubusercontent.com','127.0.0.1']:
   data=self.fixture();data['assets'][0]['url']='https://'+host+'/file'
   with self.assertRaises(ValueError):m.validate_request(data)
 def test_incomplete_refused(self):
  data=self.fixture();data['assets'].pop()
  with self.assertRaises(ValueError):m.validate_request(data)
 def test_wrong_url_refused(self):
  data=self.fixture();data['assets'][0]['url']='http://127.0.0.1/file'
  with self.assertRaises(ValueError):m.validate_request(data)
 def test_zip_is_checked_and_only_selected_file_is_copied(self):
  content=b'installer fixture';z=io.BytesIO()
  with zipfile.ZipFile(z,'w') as archive:
   archive.writestr('dist/GSM-Setup-0.6.0-alpha.exe',content);archive.writestr('../must-not-extract',b'ignored')
  raw=z.getvalue();asset=self.fixture()['assets'][1]|{'archive':True,'archive_sha256':hashlib.sha256(raw).hexdigest(),'sha256':hashlib.sha256(content).hexdigest()}
  with tempfile.TemporaryDirectory() as d:
   m.materialize(asset,pathlib.Path(d),lambda *a,**k:io.BytesIO(raw));self.assertEqual((pathlib.Path(d)/asset['filename']).read_bytes(),content);self.assertEqual(len(list(pathlib.Path(d).iterdir())),1)
 def test_sources_are_reassembled_in_order_and_checked(self):
  request=self.fixture();asset=request['assets'][2];raws=[b'first half',b'second half'];parts=[];responses={}
  for index,content in enumerate(raws):
   name=asset['filename']+f'.part-{index:02d}';z=io.BytesIO()
   with zipfile.ZipFile(z,'w') as archive:archive.writestr(name,content)
   raw=z.getvalue();url='https://github.com/Ainstem/GSM-downloads/part'+str(index);responses[url]=raw
   parts.append({'filename':name,'url':url,'archive':True,'sha256':hashlib.sha256(content).hexdigest(),'archive_sha256':hashlib.sha256(raw).hexdigest()})
  asset.pop('url');asset['chunks']=parts;asset['sha256']=hashlib.sha256(b''.join(raws)).hexdigest();m.validate_request(request)
  with tempfile.TemporaryDirectory() as d:
   m.materialize(asset,pathlib.Path(d),lambda url,**k:io.BytesIO(responses[url]));self.assertEqual((pathlib.Path(d)/asset['filename']).read_bytes(),b''.join(raws))
  parts.reverse()
  with self.assertRaises(ValueError):m.validate_request(request)
 def test_tampered_payload_refused(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):m.copy_checked(io.BytesIO(b'wrong'),pathlib.Path(d)/'file','a'*64)
 def test_duplicate_names_refused(self):
  z=io.BytesIO();name='GSM-Setup-0.6.0-alpha.exe'
  with zipfile.ZipFile(z,'w') as archive:archive.writestr('one/'+name,b'a');archive.writestr('two/'+name,b'a')
  raw=z.getvalue();asset=self.fixture()['assets'][1]|{'archive':True,'archive_sha256':hashlib.sha256(raw).hexdigest()}
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):m.materialize(asset,pathlib.Path(d),lambda *a,**k:io.BytesIO(raw))
unittest.main()
