import importlib.util,tempfile,pathlib,zipfile,hashlib,io,unittest
spec=importlib.util.spec_from_file_location('transfer',str(pathlib.Path(__file__).parent/'prepare-release.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Test(unittest.TestCase):
 def fixture(self):
  assets=[]
  for kind,name in [('linux','GSM-Linux-x86_64-0.6.0-alpha.run'),('windows','GSM-Setup-0.6.0-alpha.exe'),('sources','GSM-Linux-Media-Sources-0.6.0-alpha.tar.gz')]:
   assets.append({'kind':kind,'filename':name,'sha256':'a'*64,'url':'https://github.com/Ainstem/GSM-downloads/releases/download/v0.6.0-alpha/'+name})
  return {'version':'0.6.0-alpha','notes':'## Novidades\n- Perfil 🎮','source_commit':'a'*40,'assets':assets}
 def test_request(self):self.assertEqual(len(m.validate_request(self.fixture())),3)
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
