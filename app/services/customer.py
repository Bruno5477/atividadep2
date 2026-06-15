from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.schemas.customer import CustomerCreate


class CustomerService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_customer(self, data: CustomerCreate) -> Customer:
        customer = Customer(**data.model_dump())
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer
