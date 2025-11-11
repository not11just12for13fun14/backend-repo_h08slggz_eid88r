import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
import requests

from database import db, create_document, get_documents

app = FastAPI(title="Nexusflow Media WaaS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
PAYSTACK_BASE = "https://api.paystack.co"


class SubscribePayload(BaseModel):
    email: EmailStr
    business_name: str
    plan_slug: str

class ClientRequestPayload(BaseModel):
    email: EmailStr
    business_name: str
    message: str
    plan_slug: Optional[str] = None


PLANS = [
    {
        "name": "Basic",
        "slug": "basic",
        "price_ngn": 15000,
        "description": "Great for simple one-page sites.",
        "features": [
            "Custom 1-3 pages",
            "Free .com.ng domain",
            "Managed hosting",
            "Mobile friendly",
            "Monthly updates",
            "Email & WhatsApp support",
        ],
        "popular": False,
    },
    {
        "name": "Growth",
        "slug": "growth",
        "price_ngn": 35000,
        "description": "For growing businesses that need more.",
        "features": [
            "Up to 10 pages",
            "Blog or portfolio",
            "Basic SEO setup",
            "Analytics & tracking",
            "Priority support",
            "Speed optimization",
        ],
        "popular": True,
    },
    {
        "name": "Premium",
        "slug": "premium",
        "price_ngn": 65000,
        "description": "Advanced features and e‑commerce.",
        "features": [
            "Unlimited pages",
            "E‑commerce or bookings",
            "Advanced SEO",
            "Automations & integrations",
            "Dedicated success manager",
            "Uptime monitoring",
        ],
        "popular": False,
    },
]

PORTFOLIO = [
    {
        "title": "Lagos Fashion Hub",
        "category": "E‑commerce",
        "thumbnail_url": "https://images.unsplash.com/photo-1520975922215-230cd77abf53?q=80&w=1200&auto=format&fit=crop",
        "url": "#",
    },
    {
        "title": "Abuja Fitness Studio",
        "category": "Services",
        "thumbnail_url": "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?q=80&w=1200&auto=format&fit=crop",
        "url": "#",
    },
    {
        "title": "Kano Fresh Foods",
        "category": "Retail",
        "thumbnail_url": "https://images.unsplash.com/photo-1511690078903-71dc5a49f5e3?q=80&w=1200&auto=format&fit=crop",
        "url": "#",
    },
]

TESTIMONIALS = [
    {
        "name": "Amaka I.",
        "role": "Founder",
        "company": "Glow Skincare",
        "quote": "We launched in a week and started getting WhatsApp orders immediately. The monthly plan made it a no‑brainer.",
    },
    {
        "name": "Seyi O.",
        "role": "Director",
        "company": "Prime Logistics",
        "quote": "Professional, fast and supportive. They handle everything while we focus on the business.",
    },
    {
        "name": "Hauwa B.",
        "role": "Owner",
        "company": "Taste of Arewa",
        "quote": "Affordable and reliable. Updating our menu is as simple as sending a message.",
    },
]

FAQS = [
    {
        "question": "How do payments work?",
        "answer": "You pay a monthly subscription via Paystack. Cancel anytime. No hidden fees.",
    },
    {
        "question": "Can I upgrade plans?",
        "answer": "Yes. You can switch plans at any time. We’ll adjust your next billing cycle.",
    },
    {
        "question": "Do I own my site?",
        "answer": "Yes. Your content, domain and branding are yours. We manage hosting, updates and support.",
    },
    {
        "question": "How fast can you launch?",
        "answer": "Most sites go live in 7–14 days depending on content and features.",
    },
]


@app.get("/")
def root():
    return {"service": "Nexusflow Media WaaS API", "status": "ok"}


@app.get("/plans")
def get_plans():
    return {"plans": PLANS}


@app.get("/portfolio")
def get_portfolio():
    return {"items": PORTFOLIO}


@app.get("/testimonials")
def get_testimonials():
    return {"items": TESTIMONIALS}


@app.get("/faqs")
def get_faqs():
    return {"items": FAQS}


def find_plan(slug: str) -> Optional[Dict[str, Any]]:
    for p in PLANS:
        if p["slug"] == slug:
            return p
    return None


@app.post("/subscribe")
def subscribe(payload: SubscribePayload):
    plan = find_plan(payload.plan_slug)
    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan")

    amount_kobo = plan["price_ngn"] * 100

    # Create a subscription record with pending status
    sub_data = {
        "email": payload.email,
        "business_name": payload.business_name,
        "plan_slug": payload.plan_slug,
        "status": "pending",
    }
    try:
        sub_id = create_document("subscription", sub_data)
    except Exception:
        sub_id = None

    # If no Paystack key, return a mock URL to allow flow in demo
    if not PAYSTACK_SECRET_KEY:
        mock_url = f"https://paystack.mock/checkout/{payload.plan_slug}?email={payload.email}"
        if sub_id:
            try:
                db["subscription"].update_one({"_id": db["subscription"].find_one({"_id": db["subscription"].find_one({})["_id"]})}, {"$set": {}})
            except Exception:
                pass
        return {
            "authorization_url": mock_url,
            "reference": "demo-ref-12345",
            "provider": "mock",
        }

    # Initialize Paystack transaction
    init_url = f"{PAYSTACK_BASE}/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "email": payload.email,
        "amount": amount_kobo,
        "metadata": {
            "business_name": payload.business_name,
            "plan_slug": payload.plan_slug,
            "subscription_id": sub_id,
        },
        # Optional: currency NGN by default
    }
    try:
        r = requests.post(init_url, json=body, headers=headers, timeout=20)
        data = r.json()
        if r.status_code >= 400 or not data.get("status"):
            raise HTTPException(status_code=500, detail=data.get("message", "Payment init failed"))
        auth_url = data["data"]["authorization_url"]
        ref = data["data"]["reference"]

        if sub_id:
            try:
                db["subscription"].update_one(
                    {"_id": db["subscription"].find_one({"_id": db["subscription"].find_one({})["_id"]})},
                    {"$set": {"authorization_url": auth_url, "paystack_reference": ref}},
                )
            except Exception:
                pass

        return {"authorization_url": auth_url, "reference": ref, "provider": "paystack"}
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Payment init error: {str(e)}")


@app.post("/webhook/paystack")
async def paystack_webhook(request: Request):
    # In production, verify signature in headers 'x-paystack-signature'
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event = payload.get("event")
    data = payload.get("data", {})
    ref = data.get("reference")
    status = data.get("status")
    metadata = data.get("metadata", {}) or {}
    sub_id = metadata.get("subscription_id")

    try:
        if sub_id:
            db["subscription"].update_one(
                {"_id": db["subscription"].find_one({"_id": db["subscription"].find_one({})["_id"]})},
                {"$set": {"status": status or event, "paystack_reference": ref}},
            )
    except Exception:
        pass

    return {"received": True}


@app.post("/client-request")
def client_request(payload: ClientRequestPayload):
    try:
        doc_id = create_document("clientrequest", payload.model_dump())
        return {"ok": True, "id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = os.getenv("DATABASE_NAME") or ""
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
