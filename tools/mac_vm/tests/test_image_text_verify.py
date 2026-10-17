import copy
import hashlib
import struct
import unittest

from image_text_verify import verify_region_text


class ImageTextEvidenceTests(unittest.TestCase):
    def setUp(self):
        # Header-only bytes exercise report validation, not native PNG decoding.
        self.png = b'\x89PNG\r\n\x1a\n'+b'\0\0\0\rIHDR'+struct.pack('>II',640,480)+b'\0'*9
        self.report = dict(version=1,engine='AppleVision',sha256=hashlib.sha256(self.png).hexdigest(),
                           width=640,height=480,items=[dict(text='A2',confidence=.99,rect=[10,20,30,20])])

    def verify(self, report=None, **kwargs):
        return verify_region_text(self.png,self.report if report is None else report,
                                  region=kwargs.get('region',[0,0,100,60]),expected=kwargs.get('expected','A2'))

    def test_text_evidence_does_not_grant_actions(self):
        result=self.verify()
        self.assertEqual(result['status'],'REGION_TEXT_OBSERVED')
        self.assertFalse(result['inputPermitted'])
        self.assertFalse(result['actionEffectVerified'])

    def test_wrong_image_dimensions_engine_rejected(self):
        for key,value in [('sha256','0'*64),('width',639),('height',False),('engine','model'),('version',2),('version',True)]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                self.verify(dict(self.report,**{key:value}))

    def test_exact_text_no_substring_or_case_folding(self):
        for text in ['A20','a2',' A2','A2\n','B2','']:
            report=copy.deepcopy(self.report);report['items'][0]['text']=text
            with self.subTest(text=text),self.assertRaises(ValueError): self.verify(report)

    def test_ambiguous_or_low_confidence_rejected(self):
        for items in [[],self.report['items']*2,[dict(self.report['items'][0],confidence=.89)]]:
            with self.subTest(items=items),self.assertRaises(ValueError):
                self.verify(dict(self.report,items=items))

    def test_partial_overlap_and_outside_evidence_rejected(self):
        for rect in [[90,20,30,20],[200,20,30,20],[-1,20,30,20],[10,20,0,20],[10,float('nan'),30,20]]:
            with self.subTest(rect=rect),self.assertRaises(ValueError):
                self.verify(dict(self.report,items=[dict(self.report['items'][0],rect=rect)]))

    def test_unrelated_text_outside_region_is_not_evidence(self):
        report=copy.deepcopy(self.report)
        report['items'].append(dict(text='B2',confidence=1,rect=[200,20,30,20]))
        self.assertEqual(self.verify(report)['text'],'A2')

    def test_invalid_regions(self):
        for region in [[0,0,641,60],[0,0,100,float('inf')],[0,0,0,60],[False,0,100,60]]:
            with self.subTest(region=region),self.assertRaises(ValueError): self.verify(region=region)

    def test_changed_pixels_rejected_even_with_same_dimensions(self):
        self.png=self.png[:-1]+b'1'
        with self.assertRaises(ValueError): self.verify()


if __name__=='__main__':unittest.main()
