from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from backend import models, schemas


# ── Customers ─────────────────────────────────────────────────────────────────

def get_customer(db: Session, customer_id: int) -> Optional[models.Customer]:
    return db.query(models.Customer).filter(models.Customer.id == customer_id).first()


def get_customer_by_telegram_id(db: Session, telegram_id: str) -> Optional[models.Customer]:
    return db.query(models.Customer).filter(models.Customer.telegram_id == telegram_id).first()


def get_customers(db: Session, skip: int = 0, limit: int = 100) -> List[models.Customer]:
    return db.query(models.Customer).offset(skip).limit(limit).all()


def create_customer(db: Session, customer: schemas.CustomerCreate) -> models.Customer:
    db_customer = models.Customer(**customer.model_dump())
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer


def update_customer(db: Session, customer_id: int, data: dict) -> Optional[models.Customer]:
    cust = get_customer(db, customer_id)
    if not cust:
        return None
    for k, v in data.items():
        setattr(cust, k, v)
    db.commit()
    db.refresh(cust)
    return cust


# ── Products ──────────────────────────────────────────────────────────────────

def get_products(db: Session, active_only: bool = True) -> List[models.Product]:
    q = db.query(models.Product)
    if active_only:
        q = q.filter(models.Product.active == True)
    return q.all()


def get_product(db: Session, product_id: int) -> Optional[models.Product]:
    return db.query(models.Product).filter(models.Product.id == product_id).first()


def create_product(db: Session, product: schemas.ProductCreate) -> models.Product:
    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def update_product(db: Session, product_id: int, data: schemas.ProductUpdate) -> Optional[models.Product]:
    product = get_product(db, product_id)
    if not product:
        return None
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(product, k, v)
    db.commit()
    db.refresh(product)
    return product


def reserve_inventory(db: Session, product_id: int, quantity: float) -> bool:
    product = get_product(db, product_id)
    if not product or product.available_quantity < quantity:
        return False
    product.reserved_quantity += quantity
    db.commit()
    return True


# ── Quotations ────────────────────────────────────────────────────────────────

def _next_quote_number(db: Session) -> str:
    count = db.query(models.Quotation).count()
    year = datetime.utcnow().strftime("%y")
    return f"QT-{year}-{count + 1:04d}"


def _next_order_number(db: Session) -> str:
    count = db.query(models.Order).count()
    year = datetime.utcnow().strftime("%y")
    return f"ORD-{year}-{count + 1:04d}"


def _next_invoice_number(db: Session) -> str:
    count = db.query(models.Order).filter(models.Order.invoice_number != None).count()
    year = datetime.utcnow().strftime("%y")
    return f"INV-{year}-{count + 1:04d}"


def create_quotation(db: Session, data: schemas.QuotationCreate, ai_notes: str = "") -> models.Quotation:
    quote = models.Quotation(
        quote_number=_next_quote_number(db),
        customer_id=data.customer_id,
        discount_percent=data.discount_percent,
        tax_percent=data.tax_percent,
        payment_terms=data.payment_terms,
        delivery_terms=data.delivery_terms,
        notes=data.notes,
        ai_notes=ai_notes,
        source_conversation=data.source_conversation,
        status="draft",
    )
    db.add(quote)
    db.flush()

    for item_data in data.items:
        item = models.QuotationItem(
            quotation_id=quote.id,
            **item_data.model_dump()
        )
        db.add(item)

    db.commit()
    db.refresh(quote)
    return quote


def get_quotation(db: Session, quote_id: int) -> Optional[models.Quotation]:
    return db.query(models.Quotation).filter(models.Quotation.id == quote_id).first()


def get_quotations(
    db: Session,
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50
) -> List[models.Quotation]:
    q = db.query(models.Quotation).order_by(models.Quotation.created_at.desc())
    if status:
        q = q.filter(models.Quotation.status == status)
    if customer_id:
        q = q.filter(models.Quotation.customer_id == customer_id)
    return q.offset(skip).limit(limit).all()


def update_quotation(db: Session, quote_id: int, data: schemas.QuotationUpdate) -> Optional[models.Quotation]:
    quote = get_quotation(db, quote_id)
    if not quote:
        return None

    update_data = data.model_dump(exclude_unset=True)
    items = update_data.pop("items", None)

    for k, v in update_data.items():
        setattr(quote, k, v)
    quote.updated_at = datetime.utcnow()

    if items is not None:
        for existing_item in quote.items:
            db.delete(existing_item)
        for item_data in items:
            item = models.QuotationItem(quotation_id=quote.id, **item_data)
            db.add(item)

    db.commit()
    db.refresh(quote)
    return quote


def set_quote_status(db: Session, quote_id: int, status: str) -> Optional[models.Quotation]:
    quote = get_quotation(db, quote_id)
    if not quote:
        return None
    quote.status = status
    quote.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(quote)
    return quote


# ── Orders ────────────────────────────────────────────────────────────────────

def convert_quote_to_order(db: Session, quote_id: int, payment_link: str = "") -> Optional[models.Order]:
    quote = get_quotation(db, quote_id)
    if not quote or quote.status != "accepted":
        return None

    order = models.Order(
        order_number=_next_order_number(db),
        invoice_number=_next_invoice_number(db),
        quotation_id=quote_id,
        payment_link=payment_link,
        status="pending_payment",
        payment_status="unpaid",
    )
    db.add(order)
    quote.status = "converted"

    for item in quote.items:
        if item.product_id:
            reserve_inventory(db, item.product_id, item.quantity)

    db.commit()
    db.refresh(order)
    return order


def get_orders(db: Session, skip: int = 0, limit: int = 50) -> List[models.Order]:
    return db.query(models.Order).order_by(models.Order.created_at.desc()).offset(skip).limit(limit).all()


def get_order(db: Session, order_id: int) -> Optional[models.Order]:
    return db.query(models.Order).filter(models.Order.id == order_id).first()


def update_order_status(db: Session, order_id: int, status: str, payment_status: str = None) -> Optional[models.Order]:
    order = get_order(db, order_id)
    if not order:
        return None
    order.status = status
    if payment_status:
        order.payment_status = payment_status
    order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return order


# ── Conversations ─────────────────────────────────────────────────────────────

def save_message(
    db: Session,
    customer_id: int,
    telegram_chat_id: str,
    message: str,
    is_from_customer: bool = True
) -> models.Conversation:
    conv = models.Conversation(
        customer_id=customer_id,
        telegram_chat_id=telegram_chat_id,
        message=message,
        is_from_customer=is_from_customer,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def get_conversation_history(
    db: Session,
    telegram_chat_id: str,
    limit: int = 20
) -> List[models.Conversation]:
    return (
        db.query(models.Conversation)
        .filter(models.Conversation.telegram_chat_id == telegram_chat_id)
        .order_by(models.Conversation.timestamp.desc())
        .limit(limit)
        .all()
    )


def get_all_conversations(db: Session, customer_id: int) -> List[models.Conversation]:
    return (
        db.query(models.Conversation)
        .filter(models.Conversation.customer_id == customer_id)
        .order_by(models.Conversation.timestamp.asc())
        .all()
    )
