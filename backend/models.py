from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from backend.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    telegram_id = Column(String(100), unique=True, index=True, nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(200), nullable=True)
    address = Column(Text, nullable=True)
    company = Column(String(200), nullable=True)
    gstin = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    quotations = relationship("Quotation", back_populates="customer")
    conversations = relationship("Conversation", back_populates="customer")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), unique=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    unit = Column(String(50), default="piece")
    base_price = Column(Float, nullable=False)
    min_price = Column(Float, nullable=True)
    stock_quantity = Column(Float, default=0)
    reserved_quantity = Column(Float, default=0)
    hsn_code = Column(String(20), nullable=True)
    gst_percent = Column(Float, default=18.0)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def available_quantity(self):
        return self.stock_quantity - self.reserved_quantity


class Quotation(Base):
    __tablename__ = "quotations"

    id = Column(Integer, primary_key=True, index=True)
    quote_number = Column(String(50), unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    status = Column(String(50), default="draft")
    # statuses: draft, pending_approval, approved, sent, negotiating, accepted, rejected, converted

    valid_until = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
    notes = Column(Text, nullable=True)
    ai_notes = Column(Text, nullable=True)
    discount_percent = Column(Float, default=0.0)
    tax_percent = Column(Float, default=18.0)
    payment_terms = Column(String(200), default="100% advance")
    delivery_terms = Column(String(200), default="Ex-works")
    source_conversation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="quotations")
    items = relationship("QuotationItem", back_populates="quotation", cascade="all, delete-orphan")
    order = relationship("Order", back_populates="quotation", uselist=False)

    @property
    def subtotal(self):
        return sum(item.line_total for item in self.items)

    @property
    def discount_amount(self):
        return self.subtotal * (self.discount_percent / 100)

    @property
    def taxable_amount(self):
        return self.subtotal - self.discount_amount

    @property
    def tax_amount(self):
        return self.taxable_amount * (self.tax_percent / 100)

    @property
    def total(self):
        return self.taxable_amount + self.tax_amount


class QuotationItem(Base):
    __tablename__ = "quotation_items"

    id = Column(Integer, primary_key=True, index=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id"))
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    description = Column(String(500), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), default="piece")
    unit_price = Column(Float, nullable=False)
    hsn_code = Column(String(20), nullable=True)

    quotation = relationship("Quotation", back_populates="items")
    product = relationship("Product")

    @property
    def line_total(self):
        return self.quantity * self.unit_price


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, index=True)
    invoice_number = Column(String(50), unique=True, nullable=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id"))
    status = Column(String(50), default="pending_payment")
    # statuses: pending_payment, paid, processing, shipped, delivered, cancelled
    payment_link = Column(String(500), nullable=True)
    payment_status = Column(String(50), default="unpaid")
    payment_reference = Column(String(200), nullable=True)
    delivery_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    quotation = relationship("Quotation", back_populates="order")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    telegram_chat_id = Column(String(100), index=True)
    message = Column(Text, nullable=False)
    is_from_customer = Column(Boolean, default=True)
    message_type = Column(String(50), default="text")
    timestamp = Column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="conversations")
