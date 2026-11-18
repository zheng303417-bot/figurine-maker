import io, json, os, struct, sys, tempfile, unittest, urllib.error
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from figurine_runtime.providers import generate, meshy

class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self,*args): self.close()

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.root=Path(self.tmp.name); (self.root/'a.png').write_bytes(b'fake image'); self.dest=self.root/'model.glb'
        self.job={'provider':'meshy','source_images':['a.png'],'allow_external_image_upload':True,'max_paid_credits':20}
    def run_provider(self): return generate(self.job,self.root,self.dest,approve_paid=True,approve_upload=True)
    def test_mock_watertight(self):
        result=generate({'provider':'mock'},self.root,self.dest); data=self.dest.read_bytes(); self.assertTrue(result['synthetic']); self.assertEqual(struct.unpack('<4sII',data[:12]),(b'glTF',2,len(data)))
        size=struct.unpack('<I',data[12:16])[0]; doc=json.loads(data[20:20+size]); off=20+size+8; bv=doc['bufferViews']; acc=doc['accessors']; raw=data[off+bv[1]['byteOffset']:off+bv[1]['byteOffset']+bv[1]['byteLength']]; idx=struct.unpack('<%dH'%acc[1]['count'],raw); edges={}
        for i in range(0,len(idx),3):
            for a,b in ((idx[i],idx[i+1]),(idx[i+1],idx[i+2]),(idx[i+2],idx[i])): edges[tuple(sorted((a,b)))]=edges.get(tuple(sorted((a,b))),0)+1
        self.assertTrue(all(v==2 for v in edges.values()))
    def test_approval_budget(self):
        with patch.object(meshy.OPENER,'open') as op:
            with self.assertRaises(meshy.ProviderError): generate(self.job,self.root,self.dest)
            self.job['max_paid_credits']=19
            with self.assertRaises(meshy.ProviderError): self.run_provider()
            op.assert_not_called()
    @patch.dict(os.environ,{'MESHY_API_KEY':'secret'})
    def test_success_and_auth(self):
        generate({'provider':'mock'},self.root,self.dest); glb=self.dest.read_bytes(); self.dest.unlink()
        responses=[Response(json.dumps({'result':'task-123'}).encode()),Response(json.dumps({'status':'SUCCEEDED','model_urls':{'glb':'https://assets.meshy.ai/model.glb?sig=x'}}).encode()),Response(glb)]
        with patch.object(meshy.OPENER,'open',side_effect=responses) as op:
            result=self.run_provider(); self.assertEqual(result['task_id'],'task-123'); self.assertEqual(self.dest.read_bytes(),glb)
            self.assertEqual(op.call_args_list[0].args[0].get_header('Authorization'),'Bearer secret'); self.assertIsNone(op.call_args_list[2].args[0].get_header('Authorization'))
            body=json.loads(op.call_args_list[0].args[0].data); self.assertEqual(body['target_formats'],['glb']); self.assertEqual(body['ai_model'],'meshy-7.1')
    @patch.dict(os.environ,{'MESHY_API_KEY':'secret'})
    def test_http_and_malformed(self):
        for code in (401,402,429,302):
            with self.subTest(code=code), patch.object(meshy.OPENER,'open',side_effect=urllib.error.HTTPError('https://x',code,'',{},None)):
                with self.assertRaises(meshy.ProviderError) as e: self.run_provider()
                self.assertNotIn('secret',str(e.exception)); self.assertIn(str(code),str(e.exception))
        with patch.object(meshy.OPENER,'open',return_value=Response(b'not json')):
            with self.assertRaises(meshy.ProviderError): self.run_provider()
    @patch.dict(os.environ,{'MESHY_API_KEY':'secret'})
    def test_bad_host_retains_task(self):
        responses=[Response(b'{"result":"abc"}'),Response(b'{"status":"SUCCEEDED","model_urls":{"glb":"https://evil.example/a"}}')]
        with patch.object(meshy.OPENER,'open',side_effect=responses):
            with self.assertRaises(meshy.ProviderError) as e: self.run_provider()
            self.assertEqual(e.exception.task_id,'abc'); self.assertEqual(e.exception.status,'SUCCEEDED')
    def test_redirect_disabled(self):
        self.assertIsNone(meshy.NoRedirect().redirect_request(None,None,302,None,None,'https://evil.example'))

    @patch.dict(os.environ, {"MESHY_API_KEY": "test-secret"})
    def test_multiview_transport_failure_does_not_repeat_paid_post(self):
        (self.root / "b.png").write_bytes(b"second synthetic image")
        self.job["source_images"].append("b.png")
        with patch.object(meshy.OPENER, "open", side_effect=urllib.error.URLError("test-secret")) as transport:
            with self.assertRaises(meshy.ProviderError) as exc:
                self.run_provider()
            self.assertNotIn("test-secret", str(exc.exception))
            self.assertFalse(self.dest.exists())
            transport.assert_called_once()
            request = transport.call_args.args[0]
            self.assertTrue(request.full_url.endswith("/multi-image-to-3d"))
            self.assertEqual(len(json.loads(request.data)["image_urls"]), 2)

if __name__=='__main__': unittest.main()
