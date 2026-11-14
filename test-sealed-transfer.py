import base64,hashlib,importlib.util,json,unittest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import padding,rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
spec=importlib.util.spec_from_file_location('sealed','receive-sealed-transfer.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Test(unittest.TestCase):
 def setUp(self):
  self.private=rsa.generate_private_key(public_exponent=65537,key_size=2048);self.revision='a'*40;self.fingerprint='f'*64
  self.request={'assets':[{'filename':'installer','sha256':'b'*64}]};self.urls={'installer':'https://release-assets.githubusercontent.com/selected?sig=private-fixture'}
  key=AESGCM.generate_key(bit_length=256);nonce=b'012345678901'
  self.response={'request_commit':self.revision,'key_sha256':self.fingerprint,'wrapped_key':base64.b64encode(self.private.public_key().encrypt(key,padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))).decode(),'nonce':base64.b64encode(nonce).decode(),'ciphertext':base64.b64encode(AESGCM(key).encrypt(nonce,json.dumps(self.urls).encode(),self.revision.encode())).decode()}
 def test_urls_remain_encrypted_and_roundtrip(self):
  self.assertNotIn('private-fixture',json.dumps(self.response));result=m.decode(self.private,self.response,self.request,self.revision,self.fingerprint);self.assertEqual(result['assets'][0]['url'],self.urls['installer']);self.assertEqual(result['assets'][0]['sha256'],'b'*64)
 def test_tampering_refused(self):
  value=bytearray(base64.b64decode(self.response['ciphertext']));value[0]^=1;self.response['ciphertext']=base64.b64encode(value).decode()
  with self.assertRaises(InvalidTag):m.decode(self.private,self.response,self.request,self.revision,self.fingerprint)
 def test_wrong_request_refused(self):
  with self.assertRaises(ValueError):m.decode(self.private,self.response,self.request,'c'*40,self.fingerprint)
 def test_wrong_public_key_refused(self):
  with self.assertRaises(ValueError):m.decode(self.private,self.response,self.request,self.revision,'d'*64)
 def test_unexpected_files_refused(self):
  with self.assertRaises(ValueError):m.decode(self.private,self.response,{'assets':[{'filename':'other'}]},self.revision,self.fingerprint)
unittest.main()
