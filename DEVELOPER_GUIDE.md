# QuoteFlow — Developer Guide
### Technical Reference for Maintaining and Extending the Application

---

## Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Language | Python | 3.12+ |
| Web Framework | FastAPI | 0.115 |
| ASGI Server | Uvicorn | 0.30 |
| Database ORM | SQLAlchemy | 2.0 |
| Database | SQLite (upgradeable to PostgreSQL) | — |
| AI Provider | Groq (Llama 3.3 70B) | — |
| Telegram Bot | python-telegram-bot | 21.5 |
| PDF Generation | ReportLab | 4.2 |
| Data Validation | Pydantic | 2.7 |
| Frontend | Bootstrap 5 + Vanilla JS | 5.3 |

---

## Project Structure

```
quotation-to-order-automation/
│
├── backend/                    # FastAPI application
│   ├── __init__.py
│   ├── config.py               # All settings via .env
│   ├── database.py             # SQLAlchemy engine + session
│   ├── models.py               # Database table definitions
│   ├── schemas.py              # Pydantic request/response models
│   ├── crud.py                 # All database operations
│   ├── ai_engine.py            # Groq AI integration
│   ├── pdf_generator.py        # ReportLab PDF generation
│   └── main.py                 # FastAPI app, all API routes
│
├── bot/                        # Telegram bot
│   ├── __init__.py
│   └── telegram_bot.py         # All bot handlers
│
├── frontend/                   # Web dashboard (static SPA)
│   ├── index.html              # Single HTML page
│   ├── styles.css              # Custom CSS
│   └── app.js                  # All JS logic, API calls
│
├── pdfs/                       # Generated PDFs (gitignored)
├── run.py                      # Application entry point
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
├── .gitignore
├── SETUP.md                    # Quick start guide
├── USER_GUIDE.md               # End user documentation
└── DEVELOPER_GUIDE.md          # This file
```

---

## Local Development Setup

### Prerequisites
- Python 3.12+
- Git

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/kameshcmc-cpu/quotation-to-order-automation.git
cd quotation-to-order-automation

# 2. Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env
# Edit .env with your API keys and business details

# 5. Start the application
python run.py              # Full stack (API + Telegram bot)
python run.py --api-only   # API only (no bot)
python run.py --bot-only   # Bot only
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | Groq API key for AI features |
| `ANTHROPIC_API_KEY` | No | Alternative to Groq (Claude AI) |
| `TELEGRAM_BOT_TOKEN` | Yes (for bot) | From @BotFather on Telegram |
| `OWNER_TELEGRAM_CHAT_ID` | Yes (for bot) | Owner's Telegram chat ID |
| `BUSINESS_NAME` | Yes | Shown on all PDFs |
| `BUSINESS_ADDRESS` | Yes | Shown on all PDFs |
| `BUSINESS_PHONE` | Yes | Shown on all PDFs |
| `BUSINESS_EMAIL` | Yes | Shown on all PDFs |
| `BUSINESS_GST` | Yes | GSTIN shown on PDFs |
| `DATABASE_URL` | No | Default: `sqlite:///./quotation_app.db` |
| `API_BASE_URL` | No | Default: `http://localhost:8000` |
| `DEFAULT_GST_PERCENT` | No | Default: `18.0` |
| `RAZORPAY_KEY_ID` | No | For payment link generation |
| `RAZORPAY_KEY_SECRET` | No | For payment link generation |

---

## Database Models

### Entity Relationship

```
Customer (1) ──── (N) Quotation (1) ──── (1) Order
                         |
                         └── (N) QuotationItem ──── (1) Product
                         
Customer (1) ──── (N) Conversation
```

### Models (`backend/models.py`)

**Customer**
- `id`, `name`, `telegram_id`, `phone`, `email`, `address`, `company`, `gstin`

**Product**
- `id`, `sku`, `name`, `unit`, `base_price`, `min_price`, `stock_quantity`, `reserved_quantity`, `hsn_code`, `gst_percent`
- Property: `available_quantity = stock_quantity - reserved_quantity`

**Quotation**
- `id`, `quote_number`, `customer_id`, `status`, `discount_percent`, `tax_percent`, `payment_terms`, `delivery_terms`, `notes`, `ai_notes`, `source_conversation`
- Statuses: `draft` → `pending_approval` → `approved` → `sent` → `negotiating` → `accepted` → `converted`
- Computed properties: `subtotal`, `discount_amount`, `taxable_amount`, `tax_amount`, `total`

**QuotationItem**
- `id`, `quotation_id`, `product_id`, `description`, `quantity`, `unit`, `unit_price`, `hsn_code`
- Property: `line_total = quantity * unit_price`

**Order**
- `id`, `order_number`, `invoice_number`, `quotation_id`, `status`, `payment_status`, `payment_link`

**Conversation**
- `id`, `customer_id`, `telegram_chat_id`, `message`, `is_from_customer`, `timestamp`

---

## API Reference

Base URL: `http://localhost:8000`

Interactive docs: `http://localhost:8000/docs`

### Customers
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/customers` | List all customers |
| POST | `/api/customers` | Create customer |
| GET | `/api/customers/{id}` | Get customer |
| GET | `/api/customers/{id}/conversations` | Get chat history |

### Products
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/products` | List all products |
| POST | `/api/products` | Create product |
| PUT | `/api/products/{id}` | Update product / stock |

### Quotations
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/quotations` | List quotes (filter by status/customer) |
| POST | `/api/quotations` | Create quote manually |
| GET | `/api/quotations/{id}` | Get quote detail |
| PUT | `/api/quotations/{id}` | Update quote |
| POST | `/api/quotations/{id}/approve` | Approve quote |
| POST | `/api/quotations/{id}/send` | Send to customer |
| POST | `/api/quotations/{id}/reject` | Reject quote |
| GET | `/api/quotations/{id}/pdf` | Download quote PDF |
| POST | `/api/quotations/{id}/convert-to-order` | Convert to order |

### AI
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/ai/extract-quote` | Extract quote from text (no save) |
| POST | `/api/ai/generate-quote` | Extract + save quote draft |

### Orders
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/orders` | List all orders |
| GET | `/api/orders/{id}/invoice-pdf` | Download invoice PDF |
| PUT | `/api/orders/{id}/status` | Update order/payment status |

### Dashboard
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/stats` | Dashboard statistics |

---

## AI Engine (`backend/ai_engine.py`)

Uses **Groq API** with **Llama 3.3 70B** model and function calling (tool use) to extract structured quote data from unstructured conversation text.

### Key Functions

```python
async def extract_quote_from_conversation(
    conversation_text: str,
    products: list,
    business_context: str
) -> dict
```
Returns structured dict with `items`, `payment_terms`, `delivery_terms`, `notes`, `ai_suggestions`, `confidence`.

```python
async def generate_negotiation_response(
    original_quote: dict,
    customer_message: str
) -> str
```
Returns a suggested reply when customer negotiates.

```python
async def generate_followup_message(
    quote_data: dict,
    customer_name: str
) -> str
```
Returns a friendly message to accompany the quote PDF.

### Switching AI Provider

To switch from Groq to Anthropic Claude:
1. Set `ANTHROPIC_API_KEY` in `.env`
2. Replace `from groq import Groq` with `import anthropic`
3. Update the tool format from OpenAI-style to Anthropic tool-use format
4. Change model to `claude-sonnet-4-6`

---

## PDF Generation (`backend/pdf_generator.py`)

Uses **ReportLab** to generate A4 PDFs in Indian business format.

### Functions

```python
def generate_quotation_pdf(quotation) -> bytes
def generate_invoice_pdf(order) -> bytes
```

Both return raw PDF bytes which are streamed to the browser or sent via Telegram.

### Customizing PDF Layout
- Colors defined at the top: `PRIMARY`, `DARK`, `LIGHT_GRAY`, etc.
- Page margins: `15mm` on all sides
- To add a logo: set `BUSINESS_LOGO_PATH` in `.env` and add an `Image` flowable in the header section

---

## Telegram Bot (`bot/telegram_bot.py`)

Runs in **polling mode** (development). For production, switch to **webhook mode**.

### Command Handlers
| Command | Handler | Description |
|---|---|---|
| `/start` | `start_command` | Welcome + register customer |
| `/status` | `status_command` | Show recent quotes |
| `/myquotes` | `myquotes_command` | Same as /status |
| Any text | `handle_message` | AI quote extraction flow |
| Callback | `handle_callback` | Owner inline button actions |

### Bot Flow Logic (`handle_message`)
1. Save message to `Conversation` table
2. Check if message starts with `ACCEPT` or `REJECT`
3. Check if customer has an active `sent` quote → negotiation mode
4. Otherwise → extract quote with AI → notify owner

### Owner Callback Actions
| Callback Data | Action |
|---|---|
| `approve_{id}` | Approve quote + send PDF to customer |
| `reject_{id}` | Reject quote |
| `convert_{id}` | Convert accepted quote to order + send invoice |
| `view_quote_{id}` | Show quote summary |

### Switching to Webhook Mode (Production)
```python
# In telegram_bot.py, replace run_polling with:
app.run_webhook(
    listen="0.0.0.0",
    port=8443,
    webhook_url="https://yourdomain.com/api/telegram/webhook"
)
```

---

## Adding a New Feature

### Example: Add a Discount Approval Threshold
If a quote has more than 10% discount, require a second approval.

**1. Update the model** (`backend/models.py`):
```python
# No model change needed — discount_percent already exists
```

**2. Add business logic** (`backend/crud.py`):
```python
def create_quotation(db, data, ai_notes=""):
    status = "pending_approval"
    if data.discount_percent > 10:
        status = "pending_senior_approval"
    quote = Quotation(..., status=status)
```

**3. Add API endpoint** (`backend/main.py`):
```python
@app.post("/api/quotations/{quote_id}/senior-approve")
def senior_approve(quote_id: int, db: Session = Depends(get_db)):
    return crud.set_quote_status(db, quote_id, "approved")
```

**4. Update the frontend** (`frontend/app.js`):
```javascript
// Add button in viewQuote() for the new status
if (q.status === 'pending_senior_approval') {
    footerBtns.push(`<button onclick="seniorApprove(${q.id})">Senior Approve</button>`);
}
```

---

## Database Migrations

The app uses SQLAlchemy with `create_all()` on startup — suitable for development. For production schema changes:

### Adding a New Column
```python
# 1. Add field to model in models.py
new_field = Column(String(200), nullable=True)

# 2. For SQLite, recreate the DB (dev only):
#    Delete quotation_app.db and restart

# 3. For production, use Alembic:
pip install alembic
alembic init alembic
alembic revision --autogenerate -m "add new_field"
alembic upgrade head
```

---

## Switching to PostgreSQL

1. Install driver:
   ```bash
   pip install psycopg2-binary
   ```
2. Update `.env`:
   ```
   DATABASE_URL=postgresql://user:password@localhost:5432/quoteflow
   ```
3. Remove `check_same_thread` arg in `database.py` (already handled by the conditional).
4. Restart — SQLAlchemy handles the rest.

---

## Adding Razorpay Payment Links

1. Create account at **razorpay.com** and get API keys
2. Add to `.env`:
   ```
   RAZORPAY_KEY_ID=rzp_live_xxx
   RAZORPAY_KEY_SECRET=xxx
   ```
3. Install SDK: `pip install razorpay`
4. Update `crud.py → convert_quote_to_order()`:
   ```python
   import razorpay
   rz_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
   payment_link = rz_client.payment_link.create({
       "amount": int(quote.total * 100),  # paise
       "currency": "INR",
       "description": f"Payment for {quote.quote_number}",
   })["short_url"]
   ```

---

## Deployment (Production)

### Option 1 — Single VPS (Recommended for small scale)
```bash
# Install on Ubuntu server
pip install -r requirements.txt
pip install gunicorn

# Run with gunicorn
gunicorn backend.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Run bot as separate systemd service
```

### Option 2 — Docker
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "run.py"]
```

### Option 3 — Railway / Render (Easiest)
- Connect GitHub repo
- Set environment variables in dashboard
- Deploy — zero server management

---

## Common Issues & Fixes

| Error | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: uvicorn` | Wrong Python env | Activate venv or use full Python path |
| `Port 10048 already in use` | Server already running | `taskkill /F /IM python.exe` |
| `No event loop in thread` | Bot threading issue | Fixed in `run.py` with `asyncio.new_event_loop()` |
| `400 credit balance too low` | Groq/Anthropic credits | Top up account or switch provider |
| `404 on styles.css` | Static path mismatch | Use `/app/styles.css` not `styles.css` |
| PDF shows garbled text | Font encoding | Use standard ReportLab fonts (Helvetica) |

---

## Running Tests

No automated tests included in v1. To add:

```bash
pip install pytest pytest-asyncio httpx

# Create tests/test_api.py
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_get_products():
    response = client.get("/api/products")
    assert response.status_code == 200
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m "Add your feature"`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

---

## Version History

| Version | Date | Changes |
|---|---|---|
| 1.0.0 | May 2026 | Initial release — full MVP with AI, Telegram bot, dashboard, PDF generation |

---

## License

MIT License — free to use, modify, and distribute.
