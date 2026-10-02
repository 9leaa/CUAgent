from datetime import date
import csv
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


class Note(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(pattern=r'^[A-Za-z0-9_-]+\.md$', max_length=80)
    content: str = Field(min_length=1, max_length=6000)

    @field_validator('content')
    @classmethod
    def valid_text(cls, value):
        if '\0' in value or value.startswith('\ufeff') or len(value.encode()) > 6000:
            raise ValueError('note must be bounded UTF-8 without NUL/BOM')
        return value


class Csv(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(pattern=r'^[A-Za-z0-9_-]+\.csv$', max_length=80)
    content: str = Field(min_length=1, max_length=65536)
    numericColumns: list[str] = Field(min_length=1, max_length=4)

    @field_validator('content')
    @classmethod
    def valid_text(cls, value):
        if '\0' in value or value.startswith('\ufeff') or len(value.encode()) > 65536:
            raise ValueError('CSV must be bounded UTF-8 without NUL/BOM')
        return value


class Submission(BaseModel):
    model_config = ConfigDict(extra='forbid')
    date: date
    releaseAt: AwareDatetime | None = None
    notes: list[Note] = Field(min_length=1, max_length=3)
    csv: list[Csv] = Field(min_length=1, max_length=2)

    @model_validator(mode='after')
    def validate_sources(self):
        from agent.daily_report import csv_oracle, markdown, note_record
        names = [n.name for n in self.notes] + [t.name for t in self.csv]
        if len(set(names)) != len(names):
            raise ValueError('duplicate source name')
        notes = [note_record('inputs/' + n.name, n.content.encode()) for n in self.notes]
        try:
            tables = [csv_oracle('inputs/' + t.name, t.content.encode(), t.numericColumns) for t in self.csv]
        except csv.Error as error:
            raise ValueError('malformed CSV') from error
        report = markdown({'date': self.date.isoformat(), 'notes': notes, 'csv': tables})
        if len(report.splitlines()) >= 180 or len(report.encode()) >= 50000:
            raise ValueError('report exceeds complete readback limit')
        return self
