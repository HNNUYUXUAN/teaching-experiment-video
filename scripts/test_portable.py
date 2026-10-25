import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import requests
from PIL import Image
import settings
import images

class PortableTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='teaching-video-test-')
        self.root=Path(self.tmp.name)
        self.env=patch.dict(os.environ,{'TEACHING_VIDEO_HOME':str(self.root/'runtime')})
        self.env.start()
        self.cfg=settings.config()
        self.spec={'prompt':'教学示意图','size':'1024*1024'}
    def tearDown(self):
        self.env.stop();self.tmp.cleanup()
    def test_first_run_and_preserve_env(self):
        path=settings.ensure_config()
        self.assertTrue(path.is_file())
        self.assertEqual(self.cfg['DASHSCOPE_API_KEY'],'')
        path.write_text('IMAGE_PROVIDER=manual\nDASHSCOPE_API_KEY=\n',encoding='utf-8')
        before=path.read_bytes();settings.ensure_config()
        self.assertEqual(path.read_bytes(),before)
        self.assertEqual(settings.config()['IMAGE_PROVIDER'],'manual')
    def test_region_and_endpoints(self):
        settings.ensure_config().write_text('BAILIAN_REGION=ap-southeast-1\n',encoding='utf-8')
        self.assertTrue(settings.config()['IMAGE_ENDPOINT'].startswith('https://dashscope-intl.aliyuncs.com/'))
        for endpoint in ('http://dashscope.aliyuncs.com/a','https://attacker.invalid/a','https://dashscope.aliyuncs.com@attacker.invalid/a'):
            self.assertFalse(settings.valid_endpoint(endpoint))
    def test_dry_run_never_networks(self):
        with patch('images.requests.post') as post:
            r=images.generate(self.spec,self.root/'img.png',self.cfg,dry_run=True)
            self.assertFalse(r['network_called']);post.assert_not_called()
    def test_missing_key_and_authorization(self):
        with patch('images.requests.post') as post:
            with self.assertRaises(ValueError):images.generate(self.spec,self.root/'img.png',self.cfg)
            with self.assertRaises(ValueError):images.generate(self.spec,self.root/'img.png',self.cfg,allow_paid=True)
            post.assert_not_called()
    def test_timeout_blocks_duplicate_request(self):
        cfg=dict(self.cfg,DASHSCOPE_API_KEY='test-not-a-real-key')
        with patch('images.requests.post',side_effect=requests.Timeout) as post:
            with self.assertRaises(RuntimeError):images.generate(self.spec,self.root/'img.png',cfg,allow_paid=True)
            with self.assertRaises(FileExistsError):images.generate(self.spec,self.root/'img.png',cfg,allow_paid=True)
            self.assertEqual(post.call_count,1)
    def test_success_metadata_excludes_signed_url(self):
        blob=io.BytesIO();Image.new('RGB',(16,16),'white').save(blob,format='PNG')
        class Reply:
            status_code=200
            def json(self):return {'output':{'choices':[{'message':{'content':[{'image':'https://example.oss-cn-beijing.aliyuncs.com/image.png?example=temporary'}]}}]}}
        class Download:
            status_code=200
            def iter_content(self,_):yield blob.getvalue()
            def close(self):pass
        with patch('images.requests.post',return_value=Reply()),patch('images.requests.get',return_value=Download()) as get:
            r=images.generate(self.spec,self.root/'img.png',dict(self.cfg,DASHSCOPE_API_KEY='test-not-a-real-key'),allow_paid=True)
            self.assertEqual(r['status'],'generated')
            self.assertNotIn('headers',get.call_args.kwargs)
            self.assertNotIn('aliyuncs.com',(self.root/'img.image.json').read_text())
            self.assertFalse((self.root/'img.pending.json').exists())
    def test_bad_model_and_size(self):
        with self.assertRaises(ValueError):images.payload_for(self.spec,dict(self.cfg,IMAGE_MODEL='other-family'))
        with self.assertRaises(ValueError):images.payload_for(dict(self.spec,size='1*1'),self.cfg)

if __name__=='__main__':unittest.main(verbosity=2)
