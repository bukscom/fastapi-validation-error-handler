from fastapi import FastAPI
from pydantic import BaseModel, EmailStr, Field

from fastapi_validation_error_handler import setup_validation_error_handling

app = FastAPI()
setup_validation_error_handling(app)


class User(BaseModel):
    email: EmailStr
    age: int = Field(..., gt=0)

    model_config = {"extra": "forbid"}


@app.post("/users/")
async def create_user(user: User):
    return user
