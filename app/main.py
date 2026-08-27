from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "employees.json"
DATA_LOCK = Lock()

#MAIN APPLICATION FOR OPENAPI VERSION
app = FastAPI(title="Employee Database API", version="1.0.0",openapi_version="3.0.3")


class Employee(BaseModel):
    fname: str = Field(..., min_length=1, description="First name")
    lname: str = Field(..., min_length=1, description="Last name")
    email: EmailStr


class EmployeeUpdate(BaseModel):
    fname: str | None = Field(default=None, min_length=1)
    lname: str | None = Field(default=None, min_length=1)
    email: EmailStr | None = None


class EmployeeResponse(Employee):
    pass


class SearchResponse(BaseModel):
    results: list[EmployeeResponse]


class MessageResponse(BaseModel):
    message: str


def _load_data() -> dict[str, dict[str, Any]]:
    if not DATA_FILE.exists():
        return {"employees": {}}

    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return {"employees": {}}

    employees = data.get("employees", {})
    if not isinstance(employees, dict):
        employees = {}

    return {"employees": employees}


def _save_data(data: dict[str, dict[str, Any]]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _get_employee_by_email(email: str) -> dict[str, Any] | None:
    data = _load_data()
    return data["employees"].get(email.lower())


@app.get("/health", response_model=MessageResponse)
def health() -> MessageResponse:
    return MessageResponse(message="ok")


@app.post(
    "/employees",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_employee(employee: Employee) -> EmployeeResponse:
    email = employee.email.lower()
    with DATA_LOCK:
        data = _load_data()
        if email in data["employees"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Employee with this email already exists.",
            )

        data["employees"][email] = employee.model_dump()
        _save_data(data)

    return EmployeeResponse(**employee.model_dump())


@app.get("/employees/{email}", response_model=EmployeeResponse)
def search_employee_by_email(email: EmailStr) -> EmployeeResponse:
    employee = _get_employee_by_email(str(email).lower())
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found.")
    return EmployeeResponse(**employee)


@app.get("/employees", response_model=SearchResponse)
def search_employees_by_name(name: str | None = Query(default=None, min_length=1)) -> SearchResponse:
    data = _load_data()
    employees = list(data["employees"].values())

    if name:
        needle = name.casefold()
        employees = [
            emp
            for emp in employees
            if needle in emp["fname"].casefold()
            or needle in emp["lname"].casefold()
            or needle in f"{emp['fname']} {emp['lname']}".casefold()
        ]

    return SearchResponse(results=[EmployeeResponse(**emp) for emp in employees])


@app.put("/employees/{email}", response_model=EmployeeResponse)
def update_employee(email: EmailStr, employee: EmployeeUpdate) -> EmployeeResponse:
    current_email = str(email).lower()
    with DATA_LOCK:
        data = _load_data()
        current = data["employees"].get(current_email)
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found.")

        updated = {**current}
        if employee.fname is not None:
            updated["fname"] = employee.fname
        if employee.lname is not None:
            updated["lname"] = employee.lname
        if employee.email is not None:
            updated_email = str(employee.email).lower()
            if updated_email != current_email and updated_email in data["employees"]:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Another employee already uses the new email.",
                )
            data["employees"].pop(current_email)
            updated["email"] = updated_email
            data["employees"][updated_email] = updated
        else:
            data["employees"][current_email] = updated

        _save_data(data)

    return EmployeeResponse(**updated)


@app.delete("/employees/{email}", response_model=MessageResponse)
def delete_employee(email: EmailStr) -> MessageResponse:
    key = str(email).lower()
    with DATA_LOCK:
        data = _load_data()
        if key not in data["employees"]:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found.")

        data["employees"].pop(key)
        _save_data(data)

    return MessageResponse(message="Employee deleted successfully.")
