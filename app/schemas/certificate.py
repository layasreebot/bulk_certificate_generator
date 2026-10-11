
from datetime import date

from pydantic import BaseModel, Field, field_validator


class CertificateInfo(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    course_name: str = Field(min_length=1, max_length=200)
    event_name: str = Field(min_length=1, max_length=200)
    organization_name: str = Field(min_length=1, max_length=200)
    issue_date: date

    @field_validator(
        "title",
        "course_name",
        "event_name",
        "organization_name",
        mode="before",
    )
    @classmethod
    def clean_text(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
        return value
