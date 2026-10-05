"""Frozen project materials, not execution authority or a generated report."""
import csv
from datetime import date
import hashlib
import io
import re
from typing import Literal
import unicodedata
from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator, model_validator


def text(value, limit, *, multiline=False, empty=False):
    if (not empty and not value.strip()) or len(value.encode('utf-8')) > limit:
        raise ValueError('empty or oversized text')
    for char in value:
        if multiline and char in '\n\r\t':
            continue
        if unicodedata.category(char) in {'Cc', 'Cf', 'Cs', 'Zl', 'Zp'}:
            raise ValueError('control or format character denied')
    return value


def identifier(value):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value):
        raise ValueError('bounded source identifier required')
    return value


def calendar_date(value):
    if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
        raise ValueError('YYYY-MM-DD required')
    date.fromisoformat(value)
    return value


class HandoffNote(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, revalidate_instances='always')
    id: StrictStr
    content: StrictStr

    _id = field_validator('id')(identifier)

    @field_validator('content')
    @classmethod
    def content_text(cls, value):
        return text(value, 6 * 1024, multiline=True)


class HandoffTask(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, revalidate_instances='always')
    task_id: StrictStr
    title: StrictStr
    owner: StrictStr
    status: Literal['todo', 'doing', 'done', 'blocked']
    due_date: StrictStr

    _id = field_validator('task_id')(identifier)
    _date = field_validator('due_date')(calendar_date)

    @field_validator('title', 'owner')
    @classmethod
    def single_line(cls, value, info):
        return text(value, 12 * 1024, empty=info.field_name == 'owner' and value == '')


class HandoffSubmission(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, revalidate_instances='always')
    kind: Literal['project-handoff']
    project: StrictStr
    asOf: StrictStr
    notes: tuple[HandoffNote, ...] = Field(min_length=1, max_length=3)
    tasksCsv: StrictStr
    previousReport: StrictStr

    _date = field_validator('asOf')(calendar_date)

    @field_validator('project')
    @classmethod
    def project_text(cls, value):
        return text(value, 256)

    @field_validator('tasksCsv')
    @classmethod
    def csv_text(cls, value):
        return text(value, 12 * 1024, multiline=True)

    @field_validator('previousReport')
    @classmethod
    def prior_text(cls, value):
        return text(value, 8 * 1024, multiline=True, empty=True)

    def tasks(self) -> tuple[HandoffTask, ...]:
        columns = ['task_id', 'title', 'owner', 'status', 'due_date']
        try:
            rows = list(csv.reader(io.StringIO(self.tasksCsv, newline=''), strict=True))
        except csv.Error:
            raise ValueError('invalid task CSV') from None
        if not rows or rows[0] != columns or not 2 <= len(rows) <= 21:
            raise ValueError('fixed CSV header and 1-20 tasks required')
        if any(len(row) != len(columns) for row in rows[1:]):
            raise ValueError('invalid CSV row width')
        tasks = tuple(HandoffTask.model_validate(dict(zip(columns, row))) for row in rows[1:])
        if len({task.task_id for task in tasks}) != len(tasks):
            raise ValueError('duplicate task ID')
        return tasks

    @model_validator(mode='after')
    def bounded_sources(self):
        if len({note.id for note in self.notes}) != len(self.notes):
            raise ValueError('duplicate note ID')
        strings = [self.kind, self.project, self.asOf, self.tasksCsv, self.previousReport]
        strings.extend(value for note in self.notes for value in (note.id, note.content))
        if sum(len(value.encode('utf-8')) for value in strings) > 32 * 1024:
            raise ValueError('total input exceeds 32 KiB')
        self.tasks()
        return self

    def source_hashes(self):
        sources = {f'notes/{note.id}': note.content for note in self.notes}
        sources.update(tasksCsv=self.tasksCsv, previousReport=self.previousReport)
        return {key: hashlib.sha256(value.encode('utf-8')).hexdigest() for key, value in sources.items()}
