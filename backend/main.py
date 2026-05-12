import os
import asyncio
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import io

from backend.database import get_db, init_db
from backend import crud, schemas
from backend.ai_engine import extract_quote_from_conversation, generate_followup_message
from backend.pdf_generator import generate_quotation_pdf, generate_invoice_pdf
from backend.config import settings

app = FastAPI(
    title="AI Quotation-to-Order API",
    description="AI-powered quotation and order management for Indian SMBs",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    init_db()
    _seed_demo_data()


def _seed_demo_data():
    """Seed demo products and a customer if DB is empty."""
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        if db.query(__import__('backend.models', fromlist=['Product']).Product).count() == 0:
            from backend.models import Product, Customer
            products = [
                Product(sku="RICE-001", name="Basmati Rice", unit="kg", base_price=85.0, min_price=75.0,
                        stock_quantity=5000, hsn_code="1006", gst_percent=5),
                Product(sku="SUGAR-001", name="Sugar (M30)", unit="kg", base_price=42.0, min_price=38.0,
                        stock_quantity=10000, hsn_code="1701", gst_percent=5),
                Product(sku="OIL-001", name="Refined Sunflower Oil", unit="litre", base_price=145.0,
                        min_price=135.0, stock_quantity=2000, hsn_code="1512", gst_percent=5),
                Product(sku="WHEAT-001", name="Wheat Flour (Atta)", unit="kg", base_price=32.0,
                        min_price=28.0, stock_quantity=8000, hsn_code="1101", gst_percent=0),
                Product(sku="DAL-001", name="Toor Dal", unit="kg", base_price=120.0, min_price=110.0,
                        stock_quantity=3000, hsn_code="0713", gst_percent=0),
            ]
            for p in products:
                db.add(p)

            demo_customer = Customer(
                name="Ramesh Trading Co.",
                telegram_id="demo_customer",
                phone="+91-9876543210",
                email="ramesh@trading.com",
                address="Shop 12, Gandhi Market, Mumbai - 400001",
                company="Ramesh Trading Co.",
                gstin="27AABCR1234E1ZL"
            )
            db.add(demo_customer)
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


# ── Static Frontend ───────────────────────────────────────────────────────────

frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="frontend")


@app.get("/")
async def root():
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "AI Quotation-to-Order API", "docs": "/docs", "dashboard": "/app"}


# ── Customers ─────────────────────────────────────────────────────────────────

@app.get("/api/customers", response_model=List[schemas.CustomerOut], tags=["Customers"])
def list_customers(db: Session = Depends(get_db)):
    return crud.get_customers(db)


@app.post("/api/customers", response_model=schemas.CustomerOut, tags=["Customers"])
def create_customer(data: schemas.CustomerCreate, db: Session = Depends(get_db)):
    return crud.create_customer(db, data)


@app.get("/api/customers/{customer_id}", response_model=schemas.CustomerOut, tags=["Customers"])
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    cust = crud.get_customer(db, customer_id)
    if not cust:
        raise HTTPException(404, "Customer not found")
    return cust


@app.get("/api/customers/{customer_id}/conversations", tags=["Customers"])
def get_customer_conversations(customer_id: int, db: Session = Depends(get_db)):
    convs = crud.get_all_conversations(db, customer_id)
    return [{"id": c.id, "message": c.message, "is_from_customer": c.is_from_customer,
             "timestamp": c.timestamp.isoformat()} for c in convs]


# ── Products ──────────────────────────────────────────────────────────────────

@app.get("/api/products", response_model=List[schemas.ProductOut], tags=["Products"])
def list_products(db: Session = Depends(get_db)):
    return crud.get_products(db)


@app.post("/api/products", response_model=schemas.ProductOut, tags=["Products"])
def create_product(data: schemas.ProductCreate, db: Session = Depends(get_db)):
    return crud.create_product(db, data)


@app.put("/api/products/{product_id}", response_model=schemas.ProductOut, tags=["Products"])
def update_product(product_id: int, data: schemas.ProductUpdate, db: Session = Depends(get_db)):
    p = crud.update_product(db, product_id, data)
    if not p:
        raise HTTPException(404, "Product not found")
    return p


# ── Quotations ────────────────────────────────────────────────────────────────

@app.get("/api/quotations", tags=["Quotations"])
def list_quotations(
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    quotes = crud.get_quotations(db, status=status, customer_id=customer_id)
    result = []
    for q in quotes:
        result.append({
            "id": q.id,
            "quote_number": q.quote_number,
            "customer_name": q.customer.name,
            "customer_id": q.customer_id,
            "status": q.status,
            "total": q.total,
            "item_count": len(q.items),
            "created_at": q.created_at.isoformat(),
            "valid_until": q.valid_until.isoformat(),
        })
    return result


@app.post("/api/quotations", tags=["Quotations"])
def create_quotation(data: schemas.QuotationCreate, db: Session = Depends(get_db)):
    quote = crud.create_quotation(db, data)
    return {"id": quote.id, "quote_number": quote.quote_number, "status": quote.status}


@app.get("/api/quotations/{quote_id}", tags=["Quotations"])
def get_quotation(quote_id: int, db: Session = Depends(get_db)):
    q = crud.get_quotation(db, quote_id)
    if not q:
        raise HTTPException(404, "Quotation not found")
    return {
        "id": q.id,
        "quote_number": q.quote_number,
        "customer": {"id": q.customer.id, "name": q.customer.name,
                     "phone": q.customer.phone, "address": q.customer.address,
                     "company": q.customer.company, "gstin": q.customer.gstin},
        "status": q.status,
        "items": [{"id": i.id, "description": i.description, "quantity": i.quantity,
                   "unit": i.unit, "unit_price": i.unit_price, "line_total": i.line_total,
                   "hsn_code": i.hsn_code} for i in q.items],
        "subtotal": q.subtotal,
        "discount_percent": q.discount_percent,
        "discount_amount": q.discount_amount,
        "tax_percent": q.tax_percent,
        "tax_amount": q.tax_amount,
        "total": q.total,
        "payment_terms": q.payment_terms,
        "delivery_terms": q.delivery_terms,
        "notes": q.notes,
        "ai_notes": q.ai_notes,
        "valid_until": q.valid_until.isoformat(),
        "created_at": q.created_at.isoformat(),
    }


@app.put("/api/quotations/{quote_id}", tags=["Quotations"])
def update_quotation(quote_id: int, data: schemas.QuotationUpdate, db: Session = Depends(get_db)):
    q = crud.update_quotation(db, quote_id, data)
    if not q:
        raise HTTPException(404, "Quotation not found")
    return {"id": q.id, "quote_number": q.quote_number, "status": q.status, "total": q.total}


@app.post("/api/quotations/{quote_id}/approve", tags=["Quotations"])
def approve_quotation(quote_id: int, db: Session = Depends(get_db)):
    q = crud.set_quote_status(db, quote_id, "approved")
    if not q:
        raise HTTPException(404, "Quotation not found")
    return {"message": "Quotation approved", "status": q.status}


@app.post("/api/quotations/{quote_id}/send", tags=["Quotations"])
async def send_quotation(quote_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    q = crud.get_quotation(db, quote_id)
    if not q:
        raise HTTPException(404, "Quotation not found")
    if q.status not in ("approved", "draft"):
        raise HTTPException(400, f"Cannot send quotation in status: {q.status}")

    crud.set_quote_status(db, quote_id, "sent")

    if q.customer.telegram_id and settings.TELEGRAM_BOT_TOKEN:
        background_tasks.add_task(_send_quote_via_telegram, quote_id)

    return {"message": "Quotation marked as sent", "status": "sent"}


async def _send_quote_via_telegram(quote_id: int):
    try:
        from telegram import Bot
        from backend.database import SessionLocal
        db = SessionLocal()
        q = crud.get_quotation(db, quote_id)
        if not q or not q.customer.telegram_id:
            return

        pdf_bytes = generate_quotation_pdf(q)
        followup = await generate_followup_message(
            {"total": q.total, "item_count": len(q.items), "valid_until": q.valid_until.strftime("%d-%b-%Y")},
            q.customer.name
        )

        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        chat_id = q.customer.telegram_id
        await bot.send_message(chat_id=chat_id, text=followup)
        await bot.send_document(
            chat_id=chat_id,
            document=io.BytesIO(pdf_bytes),
            filename=f"{q.quote_number}.pdf",
            caption=f"Please find your quotation {q.quote_number} attached."
        )
        await bot.send_message(
            chat_id=chat_id,
            text=(f"To accept this quote, reply: ACCEPT {q.quote_number}\n"
                  f"To request changes, just send your message.")
        )
        db.close()
    except Exception as e:
        print(f"Telegram send error: {e}")


@app.post("/api/quotations/{quote_id}/reject", tags=["Quotations"])
def reject_quotation(quote_id: int, db: Session = Depends(get_db)):
    q = crud.set_quote_status(db, quote_id, "rejected")
    if not q:
        raise HTTPException(404, "Quotation not found")
    return {"message": "Quotation rejected"}


@app.get("/api/quotations/{quote_id}/pdf", tags=["Quotations"])
def download_quote_pdf(quote_id: int, db: Session = Depends(get_db)):
    q = crud.get_quotation(db, quote_id)
    if not q:
        raise HTTPException(404, "Quotation not found")
    pdf_bytes = generate_quotation_pdf(q)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={q.quote_number}.pdf"}
    )


# ── AI Quote Generation ───────────────────────────────────────────────────────

@app.post("/api/ai/extract-quote", tags=["AI"])
async def ai_extract_quote(data: schemas.AIQuoteRequest, db: Session = Depends(get_db)):
    """Extract a quotation draft from a customer conversation using AI."""
    products = crud.get_products(db)
    business_context = (
        f"{settings.BUSINESS_NAME} - {settings.BUSINESS_ADDRESS}"
    )
    result = await extract_quote_from_conversation(
        conversation_text=data.conversation_text,
        products=products,
        business_context=business_context
    )
    return result


@app.post("/api/ai/generate-quote", tags=["AI"])
async def ai_generate_and_save_quote(data: schemas.AIQuoteRequest, db: Session = Depends(get_db)):
    """Extract from conversation, then create and save a quotation draft."""
    if not data.customer_id:
        raise HTTPException(400, "customer_id required")

    customer = crud.get_customer(db, data.customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")

    products = crud.get_products(db)
    result = await extract_quote_from_conversation(
        conversation_text=data.conversation_text,
        products=products,
        business_context=settings.BUSINESS_NAME
    )

    if not result.get("items"):
        raise HTTPException(422, "Could not extract any items from the conversation")

    items = []
    for item in result["items"]:
        matched_product = None
        for p in products:
            if p.name.lower() in item["description"].lower():
                matched_product = p
                break
        items.append(schemas.QuotationItemCreate(
            description=item["description"],
            quantity=item["quantity"],
            unit=item["unit"],
            unit_price=item.get("unit_price", 0),
            product_id=matched_product.id if matched_product else None,
            hsn_code=item.get("hsn_code") or (matched_product.hsn_code if matched_product else None),
        ))

    quote_data = schemas.QuotationCreate(
        customer_id=data.customer_id,
        items=items,
        payment_terms=result.get("payment_terms", "100% advance"),
        delivery_terms=result.get("delivery_terms", "Ex-works"),
        notes=result.get("notes", ""),
        source_conversation=data.conversation_text,
    )
    quote = crud.create_quotation(db, quote_data, ai_notes=result.get("ai_suggestions", ""))
    return {
        "quote_id": quote.id,
        "quote_number": quote.quote_number,
        "status": quote.status,
        "total": quote.total,
        "ai_suggestions": result.get("ai_suggestions", ""),
        "confidence": result.get("confidence", 0),
    }


# ── Orders ────────────────────────────────────────────────────────────────────

@app.get("/api/orders", tags=["Orders"])
def list_orders(db: Session = Depends(get_db)):
    orders = crud.get_orders(db)
    result = []
    for o in orders:
        result.append({
            "id": o.id,
            "order_number": o.order_number,
            "invoice_number": o.invoice_number,
            "customer_name": o.quotation.customer.name,
            "status": o.status,
            "payment_status": o.payment_status,
            "total": o.quotation.total,
            "created_at": o.created_at.isoformat(),
        })
    return result


@app.post("/api/quotations/{quote_id}/convert-to-order", tags=["Orders"])
def convert_to_order(quote_id: int, db: Session = Depends(get_db)):
    q = crud.get_quotation(db, quote_id)
    if not q:
        raise HTTPException(404, "Quotation not found")
    if q.status != "accepted":
        raise HTTPException(400, "Quotation must be accepted before converting to order")

    payment_link = ""
    if settings.RAZORPAY_KEY_ID:
        payment_link = f"https://rzp.io/pay/{quote_id}"

    order = crud.convert_quote_to_order(db, quote_id, payment_link)
    if not order:
        raise HTTPException(400, "Could not convert quotation to order")
    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "invoice_number": order.invoice_number,
        "payment_link": order.payment_link,
        "status": order.status,
    }


@app.get("/api/orders/{order_id}/invoice-pdf", tags=["Orders"])
def download_invoice_pdf(order_id: int, db: Session = Depends(get_db)):
    order = crud.get_order(db, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    pdf_bytes = generate_invoice_pdf(order)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={order.invoice_number}.pdf"}
    )


@app.put("/api/orders/{order_id}/status", tags=["Orders"])
def update_order_status(order_id: int, status: str, payment_status: str = None, db: Session = Depends(get_db)):
    order = crud.update_order_status(db, order_id, status, payment_status)
    if not order:
        raise HTTPException(404, "Order not found")
    return {"status": order.status, "payment_status": order.payment_status}


# ── Dashboard Stats ───────────────────────────────────────────────────────────

@app.get("/api/stats", tags=["Dashboard"])
def get_stats(db: Session = Depends(get_db)):
    from backend.models import Quotation, Order, Customer
    quotes = db.query(Quotation).all()
    orders = db.query(Order).all()
    customers = db.query(Customer).count()

    status_counts = {}
    for q in quotes:
        status_counts[q.status] = status_counts.get(q.status, 0) + 1

    total_revenue = sum(o.quotation.total for o in orders if o.payment_status == "paid")
    pending_value = sum(q.total for q in quotes if q.status in ("sent", "approved", "pending_approval"))

    return {
        "total_customers": customers,
        "total_quotes": len(quotes),
        "total_orders": len(orders),
        "quote_status_breakdown": status_counts,
        "total_revenue": total_revenue,
        "pending_value": pending_value,
        "pending_approval": status_counts.get("pending_approval", 0),
    }


# ── Telegram Webhook ──────────────────────────────────────────────────────────

@app.post("/api/telegram/webhook", tags=["Telegram"])
async def telegram_webhook(request_data: dict):
    """Handle incoming Telegram updates via webhook."""
    try:
        from bot.telegram_bot import process_update
        await process_update(request_data)
    except Exception as e:
        print(f"Webhook error: {e}")
    return {"ok": True}
