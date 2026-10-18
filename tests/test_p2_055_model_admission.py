"""Offline admission checks; fake bytes are never used for real inference."""
from hashlib import sha256
from pathlib import Path
import importlib.util
import os
import tempfile
import unittest

MODULE=Path(__file__).resolve().parents[1]/'scripts'/'start_native_model.py'
spec=importlib.util.spec_from_file_location('native_launcher',MODULE)
launcher=importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)

class Admission(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        d=Path(self.tmp.name)
        self.model=d/'fake.gguf'
        self.binary=d/'llama-server'
        self.model.write_bytes(b'GGUF fixture, NOT a real neural model. '*10)
        self.model.chmod(0o600)
        self.binary.write_bytes(b'fake executable used for file checks only')
        self.binary.chmod(0o700)
        self.cfg={
            'WORKSPACE_AUTH_MODE':'oidc',
            'MAT_LOCAL_MODEL_ENABLED':'1',
            'MAT_LOCAL_MODEL_LICENSE_REVIEWED':'1',
            'MAT_LOCAL_MODEL_POLICY_REVIEWED':'1',
            'MAT_LOCAL_MODEL_ISOLATION_APPROVED':'1',
            'MAT_LOCAL_MODEL_CHECKPOINT_FILE':str(self.model),
            'MAT_LOCAL_MODEL_CHECKPOINT_SHA256':sha256(self.model.read_bytes()).hexdigest(),
            'MAT_NATIVE_LLAMA_SERVER_BINARY':str(self.binary),
            'MAT_NATIVE_LLAMA_SERVER_SHA256':sha256(self.binary.read_bytes()).hexdigest(),
            'MAT_LOCAL_MODEL_URL':'http://127.0.0.1:11434/v1/chat/completions'
        }
    def tearDown(self):self.tmp.cleanup()
    def check(self):
        return launcher.verify(self.cfg,network_probe=lambda:True,
                               unprivileged_probe=lambda:True)
    def test_pinned_files_pass_offline_check_without_launching(self):
        binary,model,threads=self.check()
        self.assertEqual(binary,self.binary)
        self.assertEqual(model,self.model)
        self.assertEqual(threads,2)
    def test_tampered_model_and_executable_rejected(self):
        self.model.write_bytes(b'GGUF tampered')
        with self.assertRaises(launcher.AdmissionError):self.check()
        self.cfg['MAT_LOCAL_MODEL_CHECKPOINT_SHA256']=sha256(self.model.read_bytes()).hexdigest()
        self.binary.write_bytes(b'executable tampered')
        with self.assertRaises(launcher.AdmissionError):self.check()
    def test_non_loopback_missing_oidc_and_open_permissions_rejected(self):
        with self.assertRaises(launcher.AdmissionError):
            launcher.verify(self.cfg,network_probe=lambda:False,
                            unprivileged_probe=lambda:True)
        self.cfg['WORKSPACE_AUTH_MODE']='dev_key'
        with self.assertRaises(launcher.AdmissionError):self.check()
        self.cfg['WORKSPACE_AUTH_MODE']='oidc'
        self.model.chmod(0o644)
        with self.assertRaises(launcher.AdmissionError):self.check()
    def test_unapproved_threads_and_remote_url_rejected(self):
        self.cfg['MAT_NATIVE_MODEL_THREADS']='12'
        with self.assertRaises(launcher.AdmissionError):self.check()
        self.cfg['MAT_NATIVE_MODEL_THREADS']='2'
        self.cfg['MAT_LOCAL_MODEL_URL']='https://provider.example.com/v1/chat/completions'
        with self.assertRaises(launcher.AdmissionError):self.check()

if __name__=='__main__':unittest.main()
