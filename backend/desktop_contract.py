"""Opt-in VM TextEdit request contract; no execution or business artifact writes.

Not yet exposed by the production API. A valid body alone grants no permission.
"""
from typing import Literal
import unicodedata
from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator, model_validator


class DesktopSubmission(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    kind: Literal['desktop-textedit']
    lines: tuple[StrictStr, ...] = Field(min_length=1, max_length=10)

    @field_validator('lines')
    @classmethod
    def single_line_text(cls, lines):
        for line in lines:
            if not line.strip() or any(unicodedata.category(char) in
                                      {'Cc', 'Cf', 'Cs', 'Zl', 'Zp'} for char in line):
                raise ValueError('each line must be nonempty text without controls or line separators')
        return lines

    @model_validator(mode='after')
    def bounded_document(self):
        if len(self.expected_document()) > 4096:
            raise ValueError('document exceeds 4096 UTF-8 bytes including final newline')
        return self

    def expected_document(self) -> bytes:
        """Frozen acceptance expectation, not proof of GUI execution or a saved file."""
        return ('\n'.join(self.lines) + '\n').encode('utf-8')
