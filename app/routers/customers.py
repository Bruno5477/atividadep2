from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.customer import CustomerCreate, CustomerRead
from app.services.customer import CustomerService

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerRead, status_code=201)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)) -> CustomerRead:
    return CustomerService(db).create_customer(data)
