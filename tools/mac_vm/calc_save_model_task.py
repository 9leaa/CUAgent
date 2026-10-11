"""Explicit save protocol on the original input ledger; no arbitrary paths."""
from calc_input_model_task import CalcInputModelTask
from calc_save_task import CalcSaveTask


class CalcSaveModelTask(CalcInputModelTask, CalcSaveTask):
    protocol = 'calc-save-v1'

    def commit_cell(self, args):
        with self.lock:
            try:
                if not isinstance(args, dict) or set(args) != {'snapshot_id'}:
                    raise ValueError('only current confirmed snapshot allowed')
                result = self.commit_once(**args)
                confirmation = self.confirm_commit(
                    snapshot_id=result['state']['snapshot_id'],
                    name_box_index=self._name_box())
                return self.envelope(dict(result, status=confirmation['status'],
                    confirmation=confirmation, commitEffectVerified=True, saved=False))
            except Exception:
                self.stop()
                raise

    def open_save_dialog(self, args):
        with self.lock:
            try:
                if not isinstance(args, dict) or set(args) != {'snapshot_id'}:
                    raise ValueError('only current committed snapshot allowed')
                return self.envelope(self.open_save(**args, name_box_index=self._name_box()))
            except Exception:
                self.stop()
                raise
