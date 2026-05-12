# QuoteFlow — Setup Guide

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure environment
```bash
copy .env.example .env
```
Edit `.env` and fill in:
- `ANTHROPIC_API_KEY` — from https://console.anthropic.com
- `TELEGRAM_BOT_TOKEN` — from Telegram @BotFather
- `OWNER_TELEGRAM_CHAT_ID` — your Telegram chat ID (get from @userinfobot)
- Business details (name, address, GST, etc.)

### 3. Run the app
```bash
# Full stack (API + Telegram Bot)
python run.py

# API only (no Telegram)
python run.py --api-only
```

### 4. Open Dashboard
Visit: http://localhost:8000

API docs: http://localhost:8000/docs

---

## How It Works

### Customer Flow (Telegram)
1. Customer messages your Telegram bot
2. AI (Claude) reads the conversation and extracts product requirements
3. Draft quotation is created and sent to you for approval
4. You approve on the dashboard — PDF is auto-sent to customer
5. Customer replies `ACCEPT QT-26-0001` to accept
6. You convert to order — invoice PDF is generated and sent
7. Customer pays via payment link

### Owner Flow (Dashboard)
- **Dashboard** — Stats, pending approvals, revenue
- **Quotations** — View/approve/reject quotes, download PDFs
- **Orders** — Track orders, mark payments, download invoices
- **Customers** — Manage customer database
- **Products** — Manage product catalog and inventory
- **AI Quote Tool** — Paste any conversation → AI generates quote instantly

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Customer (Telegram)                 │
└──────────────────────┬──────────────────────────────┘
                       │ messages
                       ▼
┌─────────────────────────────────────────────────────┐
│              Telegram Bot (bot/)                     │
│  • Captures conversation                            │
│  • Calls AI Engine                                  │
│  • Sends quote PDFs                                 │
└──────────────────────┬──────────────────────────────┘
                       │ REST API
                       ▼
┌─────────────────────────────────────────────────────┐
│           FastAPI Backend (backend/)                 │
│  ┌──────────────┐  ┌──────────────┐                │
│  │  AI Engine   │  │ PDF Generator│                │
│  │  (Claude)    │  │ (ReportLab)  │                │
│  └──────────────┘  └──────────────┘                │
│  ┌──────────────────────────────────┐               │
│  │     SQLite DB (SQLAlchemy)       │               │
│  │  Customers · Products · Quotes  │               │
│  │  Orders · Conversations          │               │
│  └──────────────────────────────────┘               │
└──────────────────────┬──────────────────────────────┘
                       │ serves
                       ▼
┌─────────────────────────────────────────────────────┐
│          Web Dashboard (frontend/)                   │
│  Bootstrap 5 SPA — Owner's control panel            │
└─────────────────────────────────────────────────────┘
```

---

## Upgrade Path

| Feature | How to Add |
|---------|-----------|
| PostgreSQL | Change `DATABASE_URL` in `.env` |
| Razorpay payments | Add keys in `.env`, implement in `crud.py:convert_quote_to_order` |
| WhatsApp support | Add Twilio/WATI webhook in `backend/main.py` |
| Multi-user (staff) | Add auth middleware + user model |
| Email notifications | Add SMTP config + email templates |
| React frontend | Replace `frontend/` with a Vite/React app |
| Mobile app | Consume existing REST API |
| Analytics | Add Metabase/Grafana on top of SQLite/PostgreSQL |

---

## Project Structure

```
QuoteFlow/
├── backend/
│   ├── config.py        # Settings (env vars)
│   ├── database.py      # SQLAlchemy setup
│   ├── models.py        # DB models
│   ├── schemas.py       # Pydantic schemas
│   ├── crud.py          # DB operations
│   ├── ai_engine.py     # Claude AI integration
│   ├── pdf_generator.py # ReportLab PDFs
│   └── main.py          # FastAPI app + all routes
├── bot/
│   └── telegram_bot.py  # Telegram bot handlers
├── frontend/
│   ├── index.html       # Dashboard SPA
│   ├── styles.css       # Custom styles
│   └── app.js           # Dashboard logic
├── run.py               # Startup script
├── requirements.txt
└── .env.example
```
