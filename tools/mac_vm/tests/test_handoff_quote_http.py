import http.client
import json
import secrets
import threading
import unittest
import test_handoff_task as fixtures
from desktop_tools_http import tools_server


class QuoteHttpTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.HandoffTaskTests(); self.addCleanup(self.f.doCleanups); self.f.setUp()
        self.token = secrets.token_urlsafe(32)
        self.server = tools_server(self.f.task,self.token,control_token=secrets.token_urlsafe(32),port=0,loopback_test=True)
        self.thread = threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.01})
        self.thread.start(); self.addCleanup(self.close)

    def close(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(3)

    def request(self,args,token=None):
        c = http.client.HTTPConnection(*self.server.server_address,timeout=3)
        try:
            c.request('POST','/',json.dumps(dict(op='locate_quote',args=args)),
                      {'Authorization':'Bearer '+(token or self.token)})
            r=c.getresponse(); return r.status,json.loads(r.read())
        finally:c.close()

    def test_authorized_quote_and_bad_args_each_charge_once(self):
        code,result=self.request(dict(sourceId='notes/note',quote='中文🙂'))
        self.assertEqual((code,result['status'],result['used']),(200,'UNIQUE',1))
        self.assertEqual(self.request(dict(sourceId='notes/note',quote='中文🙂',path='/private')),
                         (409,dict(error='DESKTOP_REQUEST_REJECTED',used=2)))
        self.assertEqual(self.f.sent,[])

    def test_wrong_credential_revocation_and_thirty_limit(self):
        args=dict(sourceId='notes/note',quote='中文🙂')
        self.assertEqual(self.request(args,token='wrong')[0],403)
        self.assertEqual(self.f.task.used,0)
        for used in range(1,31): self.assertEqual(self.request(args)[1]['used'],used)
        self.assertEqual(self.request(args)[0],409)
        self.assertEqual(self.f.task.used,30)

    def test_revocation_blocks_dispatch_without_reset(self):
        args=dict(sourceId='notes/note',quote='中文🙂')
        self.request(args); self.f.set_lease(stopped=True)
        self.assertEqual(self.request(args)[0],409)
        self.assertEqual(self.f.task.used,1)


if __name__=='__main__': unittest.main()
