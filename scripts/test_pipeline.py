import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave
import pipeline as p
from draft_ops import retime

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='jy-skill-test-')
        self.root=Path(self.tmp.name)
        self.cfg=p.config()
        self.wav=self.root/'speech.wav'
        p.wav(self.wav,48000,b'\x01\x00'*96000)
    def tearDown(self): self.tmp.cleanup()
    def assembly(self, **extra):
        manifest=self.root/'manifest.json'
        p.write(manifest,{'segments':[dict(id='S01',text='你好世界。',audio=str(self.wav),**extra),
                                      {'id':'S02','text':'你好世界。','audio':str(self.wav)}]})
        return p.assemble(manifest,self.root/'out',self.cfg)
    def response(self):
        return {'output':{'sentence':{'words':[{'text':'你好','begin_time':100,'end_time':900},
            {'text':'世界','begin_time':1000,'end_time':1800}]}},'request_id':'test'}
    def cache(self, placement):
        for item in p.read(placement)['segments']:
            p.write(Path(item['audio']).with_suffix('.asr.json'),
                    {'audio_sha256':item['audio_sha256'],'response':self.response()})
    def test_sample_exact_continuous_silence(self):
        place=self.assembly(lead_ms=125,slot_ms=3000)
        data=p.read(place)
        self.assertEqual(data['total_frames'],240000)
        combined=b''.join(p.audio(x['import_audio'])[1] for x in data['segments'])
        self.assertEqual(combined,p.audio(place.parent/'continuous.wav')[1])
        self.assertEqual(combined[:12000],bytes(12000))
        self.assertEqual(len(list((place.parent/'audio').glob('*.wav'))),2)
    def test_overflow_rejected(self):
        with self.assertRaisesRegex(ValueError,'exceeds slot'): self.assembly(slot_ms=1000)
    def test_bom_singleline_actual_offsets(self):
        place=self.assembly(lead_ms=125,slot_ms=3000);self.cache(place)
        cues=p.align(place,self.cfg)
        self.assertEqual(cues[0]['start_ms'],225)
        self.assertEqual(cues[1]['start_ms'],3100)
        self.assertTrue((place.parent/'captions.srt').read_bytes().startswith(b'\xef\xbb\xbf'))
        self.assertTrue(all('\n' not in c['text'] for c in cues))
        self.assertTrue(p.read(place.parent/'caption-report.json')['ready_for_import'])
        with self.assertRaises(FileExistsError):p.align(place,self.cfg)
    def test_mismatch_does_not_export(self):
        place=self.assembly();self.cache(place)
        data=p.read(place);data['segments'][0]['text']='完全不同。';p.write(place,data)
        with self.assertRaisesRegex(ValueError,'differs'):p.align(place,self.cfg)
        self.assertFalse((place.parent/'captions.srt').exists())
    def test_changed_audio_rejected(self):
        place=self.assembly();self.cache(place)
        item=p.read(place)['segments'][0];Path(item['audio']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'does not match'):p.align(place,self.cfg)
    def test_token_provenance(self):
        chars=p.tokens(self.response())
        self.assertTrue(all(x['provenance']=='within_word_interpolation' for x in chars))
        self.assertEqual(p.tokens(self.response(),{'你好':'您好'})[0]['provenance'],'reviewed_equivalence_interpolation')
    def test_blank_key_no_network(self):
        cfg=dict(self.cfg,DASHSCOPE_API_KEY='')
        with patch('pipeline.requests.post') as post:
            with self.assertRaises(ValueError):p.tts('测试',self.root/'tts.wav',cfg)
            self.assertFalse(post.called)
            self.assertFalse((self.root/'tts.pending.json').exists())
    def test_tts_http_mock_and_cache(self):
        class Reply:
            content=self.wav.read_bytes()
            def raise_for_status(self):pass
        result={'output':{'audio':{'url':'https://example.invalid/temp'}},'request_id':'mock','usage':{}}
        cfg=dict(self.cfg,DASHSCOPE_API_KEY='test-not-a-real-key')
        dest=self.root/'tts.wav'
        with patch('pipeline.post',return_value=result) as call, patch('pipeline.requests.get',return_value=Reply()):
            p.tts('测试',dest,cfg);p.tts('测试',dest,cfg)
            self.assertEqual(call.call_count,1)
        self.assertEqual(p.audio(dest)[0],48000)
        self.assertNotIn('example.invalid',dest.with_suffix('.tts.json').read_text())
    def test_asr_http_mock_and_cache(self):
        place=self.assembly()
        with patch('pipeline.post',return_value=self.response()) as call:
            p.asr(place,dict(self.cfg,DASHSCOPE_API_KEY='test'))
            p.asr(place,dict(self.cfg,DASHSCOPE_API_KEY='test'))
            self.assertEqual(call.call_count,2)
        self.assertEqual(len(p.align(place,self.cfg)),2)
    def test_draft_preserves_fields_and_rejects_video_stretch(self):
        content={'duration':100,'custom':{'keep':True},'materials':{'videos':[{'id':'m','path':str(self.wav),'type':'photo'}]},
                 'tracks':[{'id':'v','type':'video','segments':[{'id':'s','material_id':'m','clip':{'keep':1},
                            'target_timerange':{'start':0,'duration':100},'source_timerange':{'duration':100}}]},
                           {'id':'a','type':'audio','segments':[{'target_timerange':{'duration':200}}]}]}
        plan={'visual_track_id':'v','audio_track_id':'a','total_us':200,
              'visuals':[{'segment_id':'s','path':str(self.wav),'kind':'image','end_us':200}]}
        result,_=retime(content,plan)
        self.assertEqual(result['custom'],content['custom'])
        self.assertEqual(result['tracks'][0]['segments'][0]['clip'],{'keep':1})
        self.assertEqual(content['duration'],100)
        content['materials']['videos'][0]['type']='video';plan['visuals'][0]['kind']='video'
        with self.assertRaisesRegex(AssertionError,'Video timing'):retime(content,plan)

if __name__=='__main__':unittest.main(verbosity=2)
