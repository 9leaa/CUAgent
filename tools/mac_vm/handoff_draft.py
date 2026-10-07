"""Pure stdlib draft preflight. No permissions, I/O, inference or acceptance."""
import csv
import hashlib
import io
import json
import re
import unicodedata


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def require(ok, code='SCHEMA'):
    if not ok: raise ValueError(code)


def fields(value, names):
    require(type(value) is dict and set(value)==set(names.split()))


def prose(value, limit=2048):
    require(type(value) is str and bool(value.strip()) and len(value.encode())<=limit)
    require(all(c in '\r\n\t' or unicodedata.category(c) not in {'Cc','Cf','Cs','Zl','Zp'} for c in value))


def strict(raw):
    def pairs(items):
        out={}
        for key,value in items:
            require(key not in out,'JSON_NOT_STRICT');out[key]=value
        return out
    def constant(_): raise ValueError('JSON_NOT_STRICT')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)
    pending=[(value,0)]
    while pending:
        item,depth=pending.pop();require(depth<=32,'JSON_NOT_STRICT')
        if type(item) is dict:pending.extend((v,depth+1) for v in item.values())
        if type(item) is list:pending.extend((v,depth+1) for v in item)
    return value


def validate(source, report, run_id, session_id):
    fields(report,'kind runId sessionId inputSha256 counts tasks issues')
    uuid=r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}'
    require(type(run_id) is str and re.fullmatch('p2-'+uuid,run_id)
            and type(session_id) is str and re.fullmatch('session-'+uuid,session_id),'IDENTITY')
    require(report['kind']=='project-handoff' and report['runId']==run_id and report['sessionId']==session_id
            and report['inputSha256']==hashlib.sha256(canonical(source)).hexdigest(),'IDENTITY')
    columns=['task_id','title','owner','status','due_date']
    rows=list(csv.reader(io.StringIO(source['tasksCsv'],newline=''),strict=True))
    require(rows[0]==columns and 2<=len(rows)<=21 and all(len(r)==5 for r in rows[1:]),'SOURCE')
    originals={r[0]:dict(zip(columns,r)) for r in rows[1:]}
    require(len(originals)==len(rows)-1,'SOURCE')
    sources={f"notes/{n['id']}":n['content'] for n in source['notes']}
    sources.update(tasksCsv=source['tasksCsv'],previousReport=source['previousReport'])
    def statement(value, issue=False):
        fields(value,'text citations category taskIds' if issue else 'text citations')
        prose(value['text'])
        cites=value['citations'];require(type(cites) is list and 1<=len(cites)<=8)
        seen=set()
        for cite in cites:
            fields(cite,'sourceId sourceSha256 start end quote');prose(cite['quote'])
            sid,start,end=cite['sourceId'],cite['start'],cite['end']
            require(type(sid) is str and 0<len(sid)<=80 and sid in sources,'CITATION')
            require(type(start) is int and type(end) is int and 0<=start<end<=len(sources[sid]),'CITATION')
            require(sources[sid][start:end]==cite['quote'] and cite['sourceSha256']==hashlib.sha256(sources[sid].encode()).hexdigest(),'CITATION')
            key=(sid,start,end);require(key not in seen,'CITATION');seen.add(key)
        return seen
    tasks=report['tasks'];require(type(tasks) is list and 1<=len(tasks)<=20)
    seen=set();counts=dict.fromkeys(('todo','doing','done','blocked'),0);overdue=set();unknown=set()
    for task in tasks:
        fields(task,'task_id title owner status due_date overdue progress handoff')
        tid=task['task_id'];require(type(tid) is str and tid in originals and tid not in seen,'TASK_SET');seen.add(tid)
        original=originals[tid]
        require(all(type(task[k]) is str and task[k]==original[k] for k in columns),'TASK_FACTS')
        require(original['status'] in counts,'SOURCE');counts[original['status']]+=1
        late=original['status']!='done' and original['due_date']<source['asOf']
        require(type(task['overdue']) is bool and task['overdue']==late,'OVERDUE')
        if late:overdue.add(tid)
        if not original['owner']:unknown.add(tid)
        statement(task['progress']);statement(task['handoff'])
    require(seen==set(originals),'TASK_SET')
    fields(report['counts'],'todo doing done blocked')
    require(all(type(report['counts'][k]) is int and report['counts'][k]==v for k,v in counts.items()),'COUNTS')
    issues=report['issues'];require(type(issues) is list and len(issues)<=60)
    covered={'overdue':set(),'unknown_owner':set()};issue_keys=set()
    for issue in issues:
        refs=statement(issue,True);ids=issue['taskIds'];category=issue['category']
        require(type(category) is str and category in ('conflict','unknown_owner','overdue','needs_confirmation'))
        require(type(ids) is list and 1<=len(ids)<=20 and all(type(t) is str and t in originals for t in ids))
        require(len(set(ids))==len(ids))
        key=(category,tuple(sorted(ids)),issue['text']);require(key not in issue_keys);issue_keys.add(key)
        if category=='conflict':require(len(refs)>=2,'CONFLICT_REFERENCES')
        if category in covered:covered[category].update(ids)
    require(covered==dict(overdue=overdue,unknown_owner=unknown),'REQUIRED_ISSUES')
    return [next(t for t in tasks if t['task_id']==tid) for tid in originals]


def project(source, report, tasks):
    quote=lambda v:json.dumps(v,ensure_ascii=False)
    refs=lambda s:', '.join(f"{c['sourceId']}:{c['start']}-{c['end']}" for c in s['citations'])
    lines=[f"项目: {quote(source['project'])}",f"截至: {source['asOf']}",'','一、项目周报',
           '状态统计: '+', '.join(f'{k}={report["counts"][k]}' for k in ('todo','doing','done','blocked'))]
    for t in tasks:
        lines.extend([f'[{t["task_id"]}] {quote(t["title"])}',
            f'  负责人: {quote(t["owner"]) if t["owner"] else "待确认"}; 状态: {t["status"]}; 截止: {t["due_date"]}; 逾期: {"是" if t["overdue"] else "否"}',
            f'  进展: {quote(t["progress"]["text"])}',f'  来源: {refs(t["progress"])}'])
    lines.extend(['','二、交接清单'])
    for t in tasks:lines.extend([f'[{t["task_id"]}] 建议: {quote(t["handoff"]["text"])}',f'  来源: {refs(t["handoff"])}'])
    lines.extend(['','三、待确认问题'])
    for i in report['issues']:lines.extend([f'[{",".join(i["taskIds"])}] {i["category"]}: {quote(i["text"])}',f'  来源: {refs(i)}'])
    if not report['issues']:lines.append('无已列出问题（不等于无风险）')
    document='\n'.join(lines)+'\n';require(len(document.encode())<=4096,'DOCUMENT_PROJECTION_LIMIT')
    return document


def check(source, raw, *, run_id, session_id):
    """Source and identity are trusted caller bindings, never model arguments."""
    def rejected(code):return dict(status='DRAFT_REJECTED',code=code,semanticVerified=False,guiVerified=False)
    try:
        require(type(raw) is str,'JSON_TEXT_REQUIRED')
        require(0<len(raw.encode())<=65536,'DRAFT_SIZE_LIMIT')
        report=strict(raw);tasks=validate(source,report,run_id,session_id)
        document=project(source,report,tasks)
        return dict(status='DRAFT_STRUCTURE_VALID',semanticVerified=False,guiVerified=False,
            rawSha256=hashlib.sha256(raw.encode()).hexdigest(),canonicalJson=canonical(report).decode(),
            document=document,documentSha256=hashlib.sha256(document.encode()).hexdigest())
    except json.JSONDecodeError as error:
        return dict(rejected('JSON_SYNTAX'),line=error.lineno,column=error.colno)
    except (UnicodeError,RecursionError):return rejected('INVALID_UNICODE_OR_DEPTH')
    except ValueError as error:
        codes={'SCHEMA','IDENTITY','SOURCE','CITATION','TASK_SET','TASK_FACTS','OVERDUE','COUNTS',
               'CONFLICT_REFERENCES','REQUIRED_ISSUES','DOCUMENT_PROJECTION_LIMIT','JSON_TEXT_REQUIRED','DRAFT_SIZE_LIMIT','JSON_NOT_STRICT'}
        return rejected(str(error) if str(error) in codes else 'INVALID_DRAFT')
    except (KeyError,TypeError,IndexError):return rejected('INVALID_DRAFT')
