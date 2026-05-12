from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class CustomerBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    company: Optional[str] = None
    gstin: Optional[str] = None
    telegram_id: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerOut(CustomerBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    unit: str = "piece"
    base_price: float
    min_price: Optional[float] = None
    stock_quantity: float = 0
    hsn_code: Optional[str] = None
    gst_percent: float = 18.0


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    base_price: Optional[float] = None
    min_price: Optional[float] = None
    stock_quantity: Optional[float] = None
    unit: Optional[str] = None
    active: Optional[bool] = None


class ProductOut(ProductBase):
    id: int
    reserved_quantity: float
    available_quantity: float
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class QuotationItemBase(BaseModel):
    description: str
    quantity: float
    unit: str = "piece"
    unit_price: float
    product_id: Optional[int] = None
    hsn_code: Optional[str] = None


class QuotationItemCreate(QuotationItemBase):
    pass


class QuotationItemOut(QuotationItemBase):
    id: int
    line_total: float

    class Config:
        from_attributes = True


class QuotationCreate(BaseModel):
    customer_id: int
    items: List[QuotationItemCreate]
    discount_percent: float = 0.0
    tax_percent: float = 18.0
    payment_terms: str = "100% advance"
    delivery_terms: str = "Ex-works"
    notes: Optional[str] = None
    source_conversation: Optional[str] = None


class QuotationUpdate(BaseModel):
    status: Optional[str] = None
    discount_percent: Optional[float] = None
    tax_percent: Optional[float] = None
    payment_terms: Optional[str] = None
    delivery_terms: Optional[str] = None
    notes: Optional[str] = None
    items: Optional[List[QuotationItemCreate]] = None


class QuotationOut(BaseModel):
    id: int
    quote_number: str
    customer_id: int
    customer: CustomerOut
    status: str
    items: List[QuotationItemOut]
    discount_percent: float
    tax_percent: float
    subtotal: float
    discount_amount: float
    taxable_amount: float
    tax_amount: float
    total: float
    payment_terms: str
    delivery_terms: str
    notes: Optional[str]
    ai_notes: Optional[str]
    valid_until: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    order_number: str
    invoice_number: Optional[str]
    quotation_id: int
    status: str
    payment_status: str
    payment_link: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    id: int
    customer_id: int
    telegram_chat_id: str
    message: str
    is_from_customer: bool
    timestamp: datetime

    class Config:
        from_attributes = True


class AIQuoteRequest(BaseModel):
    conversation_text: str
    customer_id: Optional[int] = None


class AIQuoteResponse(BaseModel):
    customer_name: Optional[str]
    items: List[QuotationItemCreate]
    payment_terms: str
    delivery_terms: str
    notes: str
    ai_suggestions: str
    confidence: float
