from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DECIMAL, Date, Time,
    DateTime, Enum, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()


# ─────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────
class RoleEnum(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    staff = "staff"
    customer = "customer"

class OrderTypeEnum(str, enum.Enum):
    dine_in = "dine-in"
    takeaway = "takeaway"
    online = "online"

class OrderStatusEnum(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    preparing = "preparing"
    ready = "ready"
    delivered = "delivered"
    cancelled = "cancelled"

class PaymentStatusEnum(str, enum.Enum):
    unpaid = "unpaid"
    paid = "paid"
    refunded = "refunded"

class PaymentMethodEnum(str, enum.Enum):
    cash = "cash"
    upi = "upi"
    card = "card"

class TableStatusEnum(str, enum.Enum):
    available = "available"
    occupied = "occupied"
    reserved = "reserved"
    maintenance = "maintenance"

class ReservationStatusEnum(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


# ─────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────
class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(20), nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    phone = Column(String(20))
    password_hash = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), default=4)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    google_id = Column(String(255))
    profile_image = Column(String(255))
    loyalty_points = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    role = relationship("Role", back_populates="users")
    employee = relationship("Employee", back_populates="user", uselist=False)
    orders = relationship("Order", foreign_keys="Order.customer_id", back_populates="customer")
    reservations = relationship("Reservation", back_populates="customer")
    feedback = relationship("Feedback", back_populates="customer")
    loyalty_transactions = relationship("LoyaltyTransaction", back_populates="customer")


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    image_url = Column(String(255))
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    menu_items = relationship("MenuItem", back_populates="category")


class MenuItem(Base):
    __tablename__ = "menu_items"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    description = Column(Text)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    discount_percent = Column(DECIMAL(5, 2), default=0)
    image_url = Column(String(255))
    is_vegetarian = Column(Boolean, default=True)
    is_available = Column(Boolean, default=True)
    preparation_time = Column(Integer, default=10)
    calories = Column(Integer)
    allergens = Column(Text)
    rating = Column(DECIMAL(3, 2), default=0)
    total_ratings = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    category = relationship("Category", back_populates="menu_items")
    order_items = relationship("OrderItem", back_populates="menu_item")


class Table(Base):
    __tablename__ = "tables"
    id = Column(Integer, primary_key=True)
    table_number = Column(String(20), nullable=False, unique=True)
    capacity = Column(Integer, default=2)
    location = Column(String(50))
    status = Column(Enum(TableStatusEnum), default=TableStatusEnum.available)
    qr_code = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    reservations = relationship("Reservation", back_populates="table")
    orders = relationship("Order", back_populates="table")


class Reservation(Base):
    __tablename__ = "reservations"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    customer_name = Column(String(100), nullable=False)
    customer_phone = Column(String(20), nullable=False)
    customer_email = Column(String(150))
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=False)
    reserved_date = Column(Date, nullable=False)
    reserved_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, default=60)
    guests = Column(Integer, default=1)
    status = Column(Enum(ReservationStatusEnum), default=ReservationStatusEnum.pending)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    customer = relationship("User", back_populates="reservations")
    table = relationship("Table", back_populates="reservations")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    order_number = Column(String(20), nullable=False, unique=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    order_type = Column(Enum(OrderTypeEnum), default=OrderTypeEnum.dine_in)
    status = Column(Enum(OrderStatusEnum), default=OrderStatusEnum.pending)
    subtotal = Column(DECIMAL(10, 2), default=0)
    discount_amount = Column(DECIMAL(10, 2), default=0)
    gst_percent = Column(DECIMAL(5, 2), default=5.00)
    gst_amount = Column(DECIMAL(10, 2), default=0)
    total_amount = Column(DECIMAL(10, 2), default=0)
    payment_status = Column(Enum(PaymentStatusEnum), default=PaymentStatusEnum.unpaid)
    payment_method = Column(Enum(PaymentMethodEnum), default=PaymentMethodEnum.cash)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    customer = relationship("User", foreign_keys=[customer_id], back_populates="orders")
    table = relationship("Table", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    invoice = relationship("Invoice", back_populates="order", uselist=False)
    feedback = relationship("Feedback", back_populates="order")
    loyalty_transactions = relationship("LoyaltyTransaction", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    discount_percent = Column(DECIMAL(5, 2), default=0)
    total_price = Column(DECIMAL(10, 2), nullable=False)
    special_instructions = Column(Text)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, server_default=func.now())
    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem", back_populates="order_items")


class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True)
    invoice_number = Column(String(30), nullable=False, unique=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, unique=True)
    customer_name = Column(String(100))
    customer_phone = Column(String(20))
    customer_email = Column(String(150))
    subtotal = Column(DECIMAL(10, 2), nullable=False)
    discount_amount = Column(DECIMAL(10, 2), default=0)
    gst_amount = Column(DECIMAL(10, 2), default=0)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    payment_method = Column(Enum(PaymentMethodEnum), nullable=False)
    payment_reference = Column(String(100))
    paid_at = Column(DateTime)
    issued_at = Column(DateTime, server_default=func.now())
    order = relationship("Order", back_populates="invoice")


class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    contact_person = Column(String(100))
    phone = Column(String(20))
    email = Column(String(150))
    address = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    inventory_items = relationship("InventoryItem", back_populates="supplier")


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    unit = Column(String(30), nullable=False)
    current_stock = Column(DECIMAL(10, 2), default=0)
    minimum_stock = Column(DECIMAL(10, 2), default=0)
    maximum_stock = Column(DECIMAL(10, 2))
    cost_per_unit = Column(DECIMAL(10, 2))
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    category = Column(String(50))
    is_active = Column(Boolean, default=True)
    last_restocked = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    supplier = relationship("Supplier", back_populates="inventory_items")
    transactions = relationship("StockTransaction", back_populates="item")


class StockTransaction(Base):
    __tablename__ = "stock_transactions"
    id = Column(Integer, primary_key=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    transaction_type = Column(String(20), nullable=False)
    quantity = Column(DECIMAL(10, 2), nullable=False)
    unit_cost = Column(DECIMAL(10, 2))
    total_cost = Column(DECIMAL(10, 2))
    reference_id = Column(Integer)
    notes = Column(Text)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    item = relationship("InventoryItem", back_populates="transactions")


class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    employee_code = Column(String(20), unique=True)
    designation = Column(String(100))
    department = Column(String(100))
    date_of_joining = Column(Date)
    salary = Column(DECIMAL(10, 2))
    bank_account = Column(String(30))
    address = Column(Text)
    emergency_contact = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User", back_populates="employee")
    attendance_records = relationship("Attendance", back_populates="employee")
    salary_records = relationship("SalaryRecord", back_populates="employee")


class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    check_in = Column(Time)
    check_out = Column(Time)
    status = Column(String(20), default="present")
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint("employee_id", "date"),)
    employee = relationship("Employee", back_populates="attendance_records")


class SalaryRecord(Base):
    __tablename__ = "salary_records"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    base_salary = Column(DECIMAL(10, 2))
    allowances = Column(DECIMAL(10, 2), default=0)
    deductions = Column(DECIMAL(10, 2), default=0)
    net_salary = Column(DECIMAL(10, 2))
    payment_date = Column(Date)
    payment_status = Column(String(10), default="pending")
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint("employee_id", "month", "year"),)
    employee = relationship("Employee", back_populates="salary_records")


class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    food_rating = Column(Integer)
    service_rating = Column(Integer)
    ambiance_rating = Column(Integer)
    overall_rating = Column(Integer)
    comment = Column(Text)
    status = Column(String(20), default="new")
    admin_response = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    customer = relationship("User", back_populates="feedback")
    order = relationship("Order", back_populates="feedback")


class LoyaltyTransaction(Base):
    __tablename__ = "loyalty_transactions"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    points = Column(Integer, nullable=False)
    transaction_type = Column(String(20), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    customer = relationship("User", back_populates="loyalty_transactions")
    order = relationship("Order", back_populates="loyalty_transactions")

class PasswordReset(Base):
    __tablename__ = "password_resets"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", backref="password_resets")


class OTPVerification(Base):
    __tablename__ = "otp_verifications"
    id = Column(Integer, primary_key=True)
    phone = Column(String(20), nullable=False)
    otp = Column(String(10), nullable=False)
    purpose = Column(String(20), default="register")
    expires_at = Column(DateTime, nullable=False)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())