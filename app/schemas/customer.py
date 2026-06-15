from pydantic import BaseModel, EmailStr, Field, field_validator


class CustomerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    city: str = Field(min_length=2, max_length=80)
    state: str = Field(min_length=2, max_length=2)

    @field_validator("state")
    @classmethod
    def state_upper(cls, value: str) -> str:
        return value.upper()


class CustomerRead(CustomerCreate):
    id: int

    model_config = {"from_attributes": True}
