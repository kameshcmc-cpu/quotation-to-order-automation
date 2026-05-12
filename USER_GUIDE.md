# QuoteFlow — User Guide
### AI-Powered Quotation-to-Order Automation for Indian Small Businesses

---

## What is QuoteFlow?

QuoteFlow automates your entire sales quotation process. When a customer messages you on Telegram asking for products, QuoteFlow's AI reads the conversation, creates a professional quotation, sends it to the customer as a PDF, and converts it to an invoice once accepted — all without manual data entry.

**What used to take 20 minutes now takes under 60 seconds.**

---

## Who is This For?

- Traders and distributors
- Local manufacturers
- Wholesale suppliers
- Any business that sends quotations before taking orders

---

## Getting Started

### Step 1 — First Time Setup
1. Open the `.env` file in the project folder
2. Fill in your business details:
   ```
   BUSINESS_NAME=Your Business Name
   BUSINESS_ADDRESS=Your Full Address
   BUSINESS_PHONE=+91-XXXXXXXXXX
   BUSINESS_EMAIL=you@yourbusiness.com
   BUSINESS_GST=Your GST Number
   ```
3. Add your API keys:
   ```
   GROQ_API_KEY=your_groq_api_key
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   OWNER_TELEGRAM_CHAT_ID=your_telegram_chat_id
   ```
4. Start the app:
   ```
   python run.py
   ```
5. Open the dashboard at: **http://localhost:8000**

---

## The Dashboard

The dashboard is your control center. Open it at `http://localhost:8000` in any browser.

### Sidebar Menu

| Menu Item | What It Does |
|---|---|
| Dashboard | Overview — stats, pending quotes, recent activity |
| Quotations | View and manage all quotes |
| Orders | View confirmed orders and download invoices |
| Customers | Manage your customer list |
| Products | Manage your product catalog and stock |
| AI Quote Tool | Manually generate a quote by pasting a conversation |

---

## Core Workflow

### How a Quote Becomes an Order

```
Customer messages on Telegram
          ↓
  AI reads and creates quote draft
          ↓
  You get a notification on Telegram
          ↓
  You tap "Approve & Send"
          ↓
  Customer receives PDF quote
          ↓
  Customer replies "ACCEPT QT-26-XXXX"
          ↓
  You tap "Convert to Order"
          ↓
  Invoice PDF sent to customer
          ↓
  Mark payment received → Order complete
```

---

## Using the Telegram Bot

### Customer Side

Your customers interact with your Telegram bot. They can:

**Request a quote** — just describe what they need in plain language:
```
I need 500 kg basmati rice and 200 kg toor dal
```
```
Bhai, 100 litre oil aur 50 kg sugar chahiye, Friday tak delivery?
```

**Check quote status:**
```
/status
```

**View all their quotes:**
```
/myquotes
```

**Accept a quote:**
```
ACCEPT QT-26-0001
```

**Reject a quote:**
```
REJECT QT-26-0001
```

---

### Owner Side (Your Telegram)

When a customer requests a quote, you receive a notification like this:

```
New Quote Request
Customer: Ramesh Trading Co. (+91-9876543210)
Quote: QT-26-0001
Items: 3 item(s)
Total: Rs.42,500.00

[Approve & Send]  [Edit]  [Reject]
```

**Tap "Approve & Send"** — the quote PDF is instantly sent to the customer.

When a customer accepts, you receive:

```
Quote Accepted!
Customer: Ramesh Trading Co.
Quote: QT-26-0001
Amount: Rs.42,500.00

[Convert to Order]
```

**Tap "Convert to Order"** — invoice is generated and sent to the customer automatically.

---

## Managing Products

### Adding a Product
1. Go to **Products** tab on the dashboard
2. Click **"Add Product"**
3. Fill in:
   - **SKU** — unique code (e.g., RICE-001)
   - **Name** — product name
   - **Unit** — kg, litre, piece, box, etc.
   - **Base Price** — your standard selling price in Rs.
   - **Min Price** — lowest price you'll accept
   - **Stock Quantity** — current stock
   - **HSN Code** — for GST compliance
   - **GST %** — applicable GST rate (0%, 5%, 12%, 18%, 28%)
4. Click **Save Product**

### Updating Stock
1. Go to **Products** tab
2. Click the pencil icon next to any product
3. Enter the new stock quantity
4. Click OK

---

## Managing Customers

### Adding a Customer Manually
1. Go to **Customers** tab
2. Click **"Add Customer"**
3. Fill in name, company, phone, email, address, GSTIN
4. Click **Save Customer**

> Customers who message your Telegram bot are added automatically.

---

## Using the AI Quote Tool (Manual)

Use this when you want to generate a quote from a WhatsApp screenshot, email, or phone call notes.

1. Go to **AI Quote Tool** tab
2. Select the customer from the dropdown
3. Paste the conversation or describe the requirement:
   ```
   Customer called and asked for:
   - 1000 kg wheat flour
   - 500 kg sugar
   - Delivery needed by 20th
   - He mentioned budget is around 50,000
   ```
4. Click **"Generate Quote with AI"**
5. Review the extracted items and total
6. Click **"Approve & Send"** or **"Review / Edit"** to adjust before sending

---

## Quotation Statuses Explained

| Status | Meaning |
|---|---|
| Draft | Created but not reviewed yet |
| Pending Approval | Awaiting your approval |
| Approved | You approved it, ready to send |
| Sent | PDF sent to customer |
| Negotiating | Customer asked for changes |
| Accepted | Customer confirmed |
| Converted | Order and invoice created |
| Rejected | Quote was declined |

---

## Downloading PDFs

**Quote PDF:**
- Go to Quotations tab
- Click the PDF icon on any quote row
- Or open a quote and click "Download PDF"

**Invoice PDF:**
- Go to Orders tab
- Click the PDF icon on any order row

---

## Marking Payment as Received

1. Go to **Orders** tab
2. Find the order
3. Click the **Rs. button** (green) to mark as paid
4. Order status changes to "Processing"

---

## Tips for Best Results

- **Be specific in conversations** — the more detail the customer gives, the better the AI quote.
- **Keep your product catalog updated** — AI matches catalog products automatically for accurate pricing.
- **Set Min Price correctly** — this helps you know your floor during negotiation.
- **Update stock regularly** — the system reserves stock when an order is confirmed.

---

## Frequently Asked Questions

**Q: What languages does the bot understand?**
A: English, Hindi, and a mix of both (Hinglish). Regional language transliterations also work.

**Q: Can I edit a quote before sending?**
A: Yes — open the quote on the dashboard and click "Review / Edit" before approving.

**Q: What if the AI gets the price wrong?**
A: Open the quote, edit the item prices, then approve. Always review before sending.

**Q: Can multiple customers use the bot at the same time?**
A: Yes, the bot handles multiple conversations simultaneously.

**Q: Is my customer data safe?**
A: All data is stored locally on your computer in a database file (`quotation_app.db`). Nothing is sent to external servers except the conversation text to the AI for processing.

---

## Support

For issues or questions, refer to the **Developer Guide** or contact your system administrator.
