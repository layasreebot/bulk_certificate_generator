
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RecipientIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
        return value


class CertificateItem(BaseModel):
    id: str
    name: str
    email: EmailStr
    status: str
    download_url: str | None = None
    error_message: str | None = None

    model_config = ConfigDict(from_attributes=True)
