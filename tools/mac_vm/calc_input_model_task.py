"""Explicit input protocol adapter; not registered by the selection HTTP server."""
import json

from calc_input_task import CalcInputTask
from calc_model_task import CalcModelTask
from calc_selection import _save
from calc_targeting import _number


class CalcInputModelTask(CalcModelTask, CalcInputTask):
    protocol = 'calc-input-v1'
    stop_after_selection = False

    def __init__(self, *args, controls_region, editor_regions, **kwargs):
        # Trusted launcher supplies these, not a model tool invocation.
        regions=json.loads(json.dumps(dict(controls_region=controls_region,
            editor_regions=editor_regions),allow_nan=False))
        if not isinstance(editor_regions,(list,tuple)) or len(editor_regions)!=2:
            raise ValueError('two trusted editor regions required')
        for region in [controls_region,*editor_regions]:
            if (not isinstance(region,(list,tuple)) or len(region)!=4
                    or not all(_number(v) for v in region)
                    or not 0<=region[0]<region[2] or not 0<=region[1]<region[3]):
                raise ValueError('valid trusted region required')
        a,b=editor_regions
        if not (a[2]<=b[0] or b[2]<=a[0] or a[3]<=b[1] or b[3]<=a[1]):
            raise ValueError('independent editor regions required')
        self.input_regions=regions
        super().__init__(*args, **kwargs)
        try:
            path=self.directory/'input-verifier-binding.json'
            if path.exists() or path.is_symlink():
                if path.is_symlink() or json.loads(path.read_bytes())!=regions:
                    raise ValueError('input verifier binding changed')
            else:_save(path,json.dumps(regions).encode())
        except Exception:
            self.close()
            raise

    def input_cell(self, args):
        with self.lock:
            try:
                if not isinstance(args,dict) or set(args)!={'snapshot_id','text','kind'}:
                    raise ValueError('only bound snapshot and approved payload allowed')
                result=self.input_once(**args,name_box_index=self._name_box())
                confirmation=self.confirm_input(snapshot_id=result['state']['snapshot_id'],
                    name_box_index=self._name_box(),**self.input_regions)
                return self.envelope(dict(result,status=confirmation['status'],confirmation=confirmation))
            except Exception:
                self.stop()
                raise

    def commit_cell(self, args):
        with self.lock:
            try:
                if not isinstance(args,dict) or set(args)!={'snapshot_id'}:
                    raise ValueError('only current confirmed snapshot allowed')
                result=self.commit_once(**args)
                self.stop()
                return self.envelope(result)
            except Exception:
                self.stop()
                raise
