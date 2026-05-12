import json
from groq import Groq
from backend.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)
MODEL = "llama-3.3-70b-versatile"

EXTRACT_QUOTE_TOOL = {
    "type": "function",
    "function": {
        "name": "create_quotation_draft",
        "description": "Extract and structure a quotation from customer conversation for Indian SMB context",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_name": {
                    "type": "string",
                    "description": "Customer name if mentioned"
                },
                "items": {
                    "type": "array",
                    "description": "List of items/products requested",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "quantity": {"type": "number"},
                            "unit": {"type": "string", "description": "kg, piece, box, litre, meter, etc."},
                            "unit_price": {"type": "number", "description": "Suggested unit price in INR"},
                            "hsn_code": {"type": "string"}
                        },
                        "required": ["description", "quantity", "unit", "unit_price"]
                    }
                },
                "payment_terms": {"type": "string"},
                "delivery_terms": {"type": "string"},
                "notes": {"type": "string"},
                "ai_suggestions": {
                    "type": "string",
                    "description": "Pricing strategy, negotiation tips, upsell opportunities"
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence score 0-1 for extraction quality"
                }
            },
            "required": ["items", "payment_terms", "delivery_terms", "notes", "ai_suggestions", "confidence"]
        }
    }
}


def build_product_catalog_text(products: list) -> str:
    if not products:
        return "No products in catalog yet."
    lines = ["Available products in catalog:"]
    for p in products:
        lines.append(
            f"- {p.name} (SKU: {p.sku}) | Unit: {p.unit} | Price: Rs.{p.base_price:.2f} "
            f"| Min: Rs.{p.min_price or p.base_price:.2f} | Stock: {p.available_quantity} {p.unit}"
        )
    return "\n".join(lines)


async def extract_quote_from_conversation(
    conversation_text: str,
    products: list = None,
    business_context: str = ""
) -> dict:
    products = products or []
    catalog_text = build_product_catalog_text(products)

    system_prompt = f"""You are an AI assistant for an Indian small business owner helping automate quotation generation.

Business Context: {business_context or "Indian SMB - trader/distributor"}
{catalog_text}

Your job is to:
1. Read customer conversations (often a mix of Hindi/English/regional language)
2. Extract product requirements, quantities, and pricing expectations
3. Suggest competitive market-rate pricing in INR (Indian Rupees)
4. Identify the best matching products from the catalog if available
5. Note any special requirements, delivery timelines, or negotiation signals
6. Provide strategic suggestions for the business owner

Keep in mind Indian business norms: GST compliance, common payment terms like "50% advance + 50% on delivery",
common units (kg, litre, piece, dozen, carton, bundle), and typical Indian B2B negotiation patterns.
Always use the create_quotation_draft function to return structured data."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this customer conversation and generate a quotation draft:\n\n{conversation_text}"}
        ],
        tools=[EXTRACT_QUOTE_TOOL],
        tool_choice={"type": "function", "function": {"name": "create_quotation_draft"}},
        max_tokens=2000,
        temperature=0.3,
    )

    message = response.choices[0].message
    if message.tool_calls:
        return json.loads(message.tool_calls[0].function.arguments)

    return {
        "items": [],
        "payment_terms": "100% advance",
        "delivery_terms": "Ex-works",
        "notes": "Could not parse conversation",
        "ai_suggestions": "Please review the conversation manually",
        "confidence": 0.0
    }


async def generate_negotiation_response(
    original_quote: dict,
    customer_message: str,
    negotiation_history: str = ""
) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=300,
        messages=[
            {
                "role": "system",
                "content": "You help Indian business owners respond professionally to customer negotiations. Be brief, friendly, and use Indian business communication style."
            },
            {
                "role": "user",
                "content": f"""Original quote total: Rs.{original_quote.get('total', 0):,.2f}
Current discount: {original_quote.get('discount_percent', 0)}%
{f"Previous negotiation: {negotiation_history}" if negotiation_history else ""}

Customer message: "{customer_message}"

Write a professional 2-3 sentence response. If asking for discount, suggest a counter-offer."""
            }
        ]
    )
    return response.choices[0].message.content


async def suggest_pricing(
    product_name: str,
    quantity: float,
    unit: str,
    catalog_price: float = None
) -> dict:
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=200,
        messages=[
            {
                "role": "user",
                "content": f"""For an Indian SMB, suggest pricing for:
Product: {product_name}
Quantity: {quantity} {unit}
{f"Catalog price: Rs.{catalog_price}" if catalog_price else ""}

Respond ONLY with valid JSON: {{"unit_price": 0, "bulk_discount_percent": 0, "insight": ""}}"""
            }
        ]
    )
    try:
        text = response.choices[0].message.content
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception:
        return {"unit_price": catalog_price or 0, "bulk_discount_percent": 0, "insight": ""}


async def generate_followup_message(quote_data: dict, customer_name: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=150,
        messages=[
            {
                "role": "user",
                "content": f"""Write a short 2-3 line follow-up message for sending a quotation to an Indian customer.
Customer: {customer_name}
Quote total: Rs.{quote_data.get('total', 0):,.2f}
Valid until: {quote_data.get('valid_until', '7 days')}
Professional, friendly, Indian business style. No emojis."""
            }
        ]
    )
    return response.choices[0].message.content
