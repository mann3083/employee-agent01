# Employee Database API

Simple FastAPI app for managing employees stored in a JSON file keyed by email.

## Features
- Add employee
- Search by email
- Search by name
- Update employee
- Delete employee

## Run
1. Activate your conda environment: `conda activate reg1`
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Start the server:
   - `uvicorn app.main:app --reload`

## Endpoints
- `POST /employees`
- `GET /employees/{email}`
- `GET /employees?name=alice`
- `PUT /employees/{email}`
- `DELETE /employees/{email}`
