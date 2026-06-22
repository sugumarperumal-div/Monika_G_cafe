from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import date, time, datetime
from decimal import Decimal


# ─────────────────────────────────────────────
# AUTH SCHEMAS
# ─────────────────────────────────────────────
class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)

class OTPRequest(BaseModel):
    phone: str
    purpose: str = "register"

class OTPVerify(BaseModel):
    phone: str
    otp: str


# ─────────────────────────────────────────────
# USER SCHEMAS
# ─────────────────────────────────────────────
class UserOut(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str]
    role_id: int
    is_active: bool
    loyalty_points: int
    profile_image: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    profile_image: Optional[str] = None


# ─────────────────────────────────────────────
# CATEGORY SCHEMAS
# ─────────────────────────────────────────────
class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    display_order: int = 0

class CategoryOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    image_url: Optional[str]
    is_active: bool
    display_order: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# MENU ITEM SCHEMAS
# ─────────────────────────────────────────────
class MenuItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category_id: int
    price: Decimal = Field(..., gt=0)
    discount_percent: Decimal = 0
    is_vegetarian: bool = True
    is_available: bool = True
    preparation_time: int = 10
    calories: Optional[int] = None
    allergens: Optional[str] = None

class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    price: Optional[Decimal] = None
    discount_percent: Optional[Decimal] = None
    is_vegetarian: Optional[bool] = None
    is_available: Optional[bool] = None
    preparation_time: Optional[int] = None
    calories: Optional[int] = None
    allergens: Optional[str] = None

class MenuItemOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category_id: int
    category: Optional[CategoryOut]
    price: float
    discount_percent: float
    image_url: Optional[str]
    is_vegetarian: bool
    is_available: bool
    preparation_time: int
    calories: Optional[int]
    allergens: Optional[str]
    rating: float
    total_ratings: int

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# TABLE SCHEMAS
# ─────────────────────────────────────────────
class TableCreate(BaseModel):
    table_number: str
    capacity: int = 2
    location: Optional[str] = None

class TableOut(BaseModel):
    id: int
    table_number: str
    capacity: int
    location: Optional[str]
    status: str

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# RESERVATION SCHEMAS
# ─────────────────────────────────────────────
class ReservationCreate(BaseModel):
    customer_name: str
    customer_phone: str
    customer_email: Optional[EmailStr] = None
    table_id: int
    reserved_date: date
    reserved_time: time
    duration_minutes: int = 60
    guests: int = 1
    notes: Optional[str] = None

class ReservationOut(BaseModel):
    id: int
    customer_name: str
    customer_phone: str
    table_id: int
    reserved_date: date
    reserved_time: time
    guests: int
    status: str
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# ORDER SCHEMAS
# ─────────────────────────────────────────────
class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = Field(..., gt=0)
    special_instructions: Optional[str] = None

class OrderCreate(BaseModel):
    order_type: str = "dine-in"
    table_id: Optional[int] = None
    customer_id: Optional[int] = None
    items: List[OrderItemCreate]
    notes: Optional[str] = None
    payment_method: str = "cash"

class OrderItemOut(BaseModel):
    id: int
    menu_item_id: int
    menu_item: Optional[MenuItemOut]
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    special_instructions: Optional[str]
    status: str

    class Config:
        from_attributes = True

class OrderOut(BaseModel):
    id: int
    order_number: str
    order_type: str
    status: str
    subtotal: Decimal
    discount_amount: Decimal
    gst_amount: Decimal
    total_amount: Decimal
    payment_status: str
    payment_method: str
    items: List[OrderItemOut] = []
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# INVOICE SCHEMAS
# ─────────────────────────────────────────────
class InvoiceOut(BaseModel):
    id: int
    invoice_number: str
    order_id: int
    customer_name: Optional[str]
    subtotal: Decimal
    discount_amount: Decimal
    gst_amount: Decimal
    total_amount: Decimal
    payment_method: str
    issued_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# INVENTORY SCHEMAS
# ─────────────────────────────────────────────
class SupplierCreate(BaseModel):
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None

class SupplierOut(BaseModel):
    id: int
    name: str
    contact_person: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True

class InventoryItemCreate(BaseModel):
    name: str
    unit: str
    current_stock: Decimal = 0
    minimum_stock: Decimal = 0
    maximum_stock: Optional[Decimal] = None
    cost_per_unit: Optional[Decimal] = None
    supplier_id: Optional[int] = None
    category: Optional[str] = None

class InventoryItemOut(BaseModel):
    id: int
    name: str
    unit: str
    current_stock: Decimal
    minimum_stock: Decimal
    cost_per_unit: Optional[Decimal]
    category: Optional[str]
    is_active: bool
    supplier: Optional[SupplierOut]

    @property
    def is_low_stock(self) -> bool:
        return self.current_stock <= self.minimum_stock

    class Config:
        from_attributes = True

class StockAdjustment(BaseModel):
    transaction_type: str  # purchase/consumption/adjustment/waste
    quantity: Decimal
    unit_cost: Optional[Decimal] = None
    notes: Optional[str] = None


# ─────────────────────────────────────────────
# EMPLOYEE SCHEMAS
# ─────────────────────────────────────────────
class EmployeeCreate(BaseModel):
    user_id: int
    employee_code: Optional[str] = None
    designation: Optional[str] = None
    department: Optional[str] = None
    date_of_joining: Optional[date] = None
    salary: Optional[Decimal] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None

class EmployeeOut(BaseModel):
    id: int
    employee_code: Optional[str]
    designation: Optional[str]
    department: Optional[str]
    date_of_joining: Optional[date]
    salary: Optional[Decimal]
    is_active: bool
    user: Optional[UserOut]

    class Config:
        from_attributes = True

class AttendanceCreate(BaseModel):
    employee_id: int
    date: date
    check_in: Optional[time] = None
    check_out: Optional[time] = None
    status: str = "present"
    notes: Optional[str] = None

class AttendanceOut(BaseModel):
    id: int
    employee_id: int
    date: date
    check_in: Optional[time]
    check_out: Optional[time]
    status: str

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# FEEDBACK SCHEMAS
# ─────────────────────────────────────────────
class FeedbackCreate(BaseModel):
    order_id: Optional[int] = None
    food_rating: int = Field(..., ge=1, le=5)
    service_rating: int = Field(..., ge=1, le=5)
    ambiance_rating: int = Field(..., ge=1, le=5)
    overall_rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

class FeedbackOut(BaseModel):
    id: int
    food_rating: int
    service_rating: int
    ambiance_rating: int
    overall_rating: int
    comment: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# DASHBOARD / REPORT SCHEMAS
# ─────────────────────────────────────────────
class DashboardStats(BaseModel):
    today_revenue: float
    today_orders: int
    active_tables: int
    pending_orders: int
    low_stock_count: int
    total_customers: int
    monthly_revenue: float
    top_items: List[dict]