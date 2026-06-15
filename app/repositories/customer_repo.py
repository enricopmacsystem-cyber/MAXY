from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.customer import CustomerCache


class CustomerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[CustomerCache], int]:
        pattern = f"%{query.strip()}%"
        filters = or_(
            CustomerCache.company_name.ilike(pattern),
            CustomerCache.customer_code.ilike(pattern),
            CustomerCache.phone.ilike(pattern),
            CustomerCache.email.ilike(pattern),
            CustomerCache.vat_number.ilike(pattern),
        )
        count_stmt = select(func.count()).select_from(CustomerCache).where(filters)
        total = self.session.scalar(count_stmt) or 0

        stmt = (
            select(CustomerCache)
            .where(filters)
            .order_by(CustomerCache.company_name)
            .limit(limit)
            .offset(offset)
        )
        items = list(self.session.scalars(stmt))
        return items, total

    def get_by_code(self, customer_code: str) -> CustomerCache | None:
        normalized = customer_code.strip()
        stmt = select(CustomerCache).where(
            func.upper(CustomerCache.customer_code) == normalized.upper()
        )
        return self.session.scalar(stmt)

    def list_all(
        self,
        *,
        limit: int = 2000,
        offset: int = 0,
    ) -> tuple[list[CustomerCache], int]:
        total = self.session.scalar(select(func.count()).select_from(CustomerCache)) or 0
        stmt = (
            select(CustomerCache)
            .order_by(CustomerCache.company_name.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt)), int(total)

    def count_all(self) -> int:
        return int(self.session.scalar(select(func.count()).select_from(CustomerCache)) or 0)

    def upsert_from_easyone(self, customer) -> bool:
        """Inserisce o aggiorna cliente da schema CustomerResponse. Ritorna True se nuovo."""
        existing = self.get_by_code(customer.customer_code)
        if existing:
            existing.company_name = customer.company_name
            existing.vat_number = customer.vat_number
            existing.phone = customer.phone
            existing.email = customer.email
            existing.city = customer.city
            existing.address_line = customer.address_line
            existing.postal_code = customer.postal_code
            existing.province = customer.province
            existing.country = customer.country
            existing.latitude = customer.latitude
            existing.longitude = customer.longitude
            existing.sales_agent = customer.sales_agent
            existing.source_system = customer.source_system or "easyone"
            existing.fetched_at = customer.fetched_at
            self.session.flush()
            return False

        entity = CustomerCache(
            id=customer.id,
            customer_code=customer.customer_code,
            company_name=customer.company_name,
            vat_number=customer.vat_number,
            phone=customer.phone,
            email=customer.email,
            city=customer.city,
            address_line=customer.address_line,
            postal_code=customer.postal_code,
            province=customer.province,
            country=customer.country,
            latitude=customer.latitude,
            longitude=customer.longitude,
            sales_agent=customer.sales_agent,
            source_system=customer.source_system or "easyone",
            fetched_at=customer.fetched_at,
        )
        self.session.add(entity)
        self.session.flush()
        return True

    def get_by_phone(self, phone: str) -> CustomerCache | None:
        normalized = phone.strip().replace(" ", "")
        stmt = select(CustomerCache).where(
            or_(
                CustomerCache.phone == phone,
                CustomerCache.phone == normalized,
            )
        )
        return self.session.scalar(stmt)
