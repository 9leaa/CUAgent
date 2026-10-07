import unittest
import test_handoff_task as fixtures
from driver_smoke import StopRun


class QuoteTests(unittest.TestCase):
    setUp = fixtures.HandoffTaskTests.setUp
    set_lease = fixtures.HandoffTaskTests.set_lease
    make_task = fixtures.HandoffTaskTests.make_task
    rows = fixtures.HandoffTaskTests.rows
    def lookup(self, **args):
        return self.task.locate_quote(dict(sourceId='notes/note', quote='中文🙂', **args))

    def test_lookup_admission_trace_and_no_gui(self):
        self.task.snapshot = {'snapshot_id':'old'}
        result = self.lookup()
        start = self.payload['notes'][0]['content'].index('中文🙂')
        self.assertEqual(result['matches'], [dict(start=start,end=start+3)])
        self.assertEqual(result['used'], 1)
        self.assertEqual(self.sent, [])
        self.assertIsNone(self.task.snapshot)
        self.assertEqual(self.task.inflight, set())
        args = next(r for r in self.rows() if r['event']=='helper_arguments')
        done = next(r for r in self.rows() if r['event']=='result')
        self.assertEqual(args['call_id'], done['call_id'])
        self.assertEqual(done['value'], result)

    def test_lookup_invalid_arguments_consume_original_budget(self):
        for args in ({}, {'sourceId':'notes/note','quote':''},
                     {'sourceId':'notes/note','quote':'x','path':'/secret'}):
            with self.assertRaises(ValueError): self.task.locate_quote(args)
        self.assertEqual(self.task.used,3)
        self.assertEqual(self.task.inflight,set())

    def test_lookup_stop_and_lease(self):
        self.set_lease(stopped=True)
        with self.assertRaises(StopRun): self.lookup()
        self.assertEqual(self.task.used,0)

    def test_lookup_budget_and_restart(self):
        for _ in range(30): self.lookup()
        with self.assertRaises(StopRun): self.lookup()
        self.task = self.make_task()
        with self.assertRaises(StopRun): self.lookup()
        self.assertEqual(self.task.used,30)

    def test_lookup_reopen_denied_and_counted(self):
        self.task.reopen_phase='reopened'
        with self.assertRaises(StopRun): self.lookup()
        self.assertEqual(self.task.used,1)

    def test_lookup_tampered_materials(self):
        self.path.write_bytes(self.raw+b' ')
        with self.assertRaises(StopRun): self.lookup()
        self.assertEqual(self.task.used,1)

    def test_stop_during_lookup_returns_only_original_admitted_result(self):
        original = self.task._read_frozen_input
        def stopped_read():
            self.task.stop()
            return original()
        self.task._read_frozen_input = stopped_read
        self.assertEqual(self.lookup()['used'],1)
        with self.assertRaises(StopRun): self.lookup()
        self.assertEqual(self.task.used,1)
        self.assertEqual(self.task.inflight,set())


if __name__ == '__main__': unittest.main()
