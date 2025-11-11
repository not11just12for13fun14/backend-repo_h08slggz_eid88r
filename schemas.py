"""
Database Schemas for Nexusflow Media WaaS

Each Pydantic model maps to a MongoDB collection (lowercase of class name)
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List

class Plan(BaseModel):
    name: str = Field(..., description="Plan display name")
    slug: str = Field(..., description="URL-safe identifier, e.g., basic, growth, premium")
    price_ngn: int = Field(..., ge=0, description="Monthly price in Naira")
    description: str = Field(..., description="Short plan blurb")
    features: List[str] = Field(default_factory=list)
    popular: bool = Field(False, description="Highlight as popular")

class Subscription(BaseModel):
    email: EmailStr
    business_name: str
    plan_slug: str
    status: str = Field("pending", description="pending, active, canceled, failed")
    paystack_reference: Optional[str] = None
    authorization_url: Optional[str] = None

class Clientrequest(BaseModel):
    email: EmailStr
    business_name: str
    message: str
    plan_slug: Optional[str] = None

class Portfolioitem(BaseModel):
    title: str
    category: str
    thumbnail_url: str
    url: Optional[str] = None

class Testimonial(BaseModel):
    name: str
    role: str
    company: str
    quote: str

class Faq(BaseModel):
    question: str
    answer: str
