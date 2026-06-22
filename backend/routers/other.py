"""
Combined routers for: Tables, Reservations, Inventory,
Employees, Feedback, Reports/Dashboard
"""

from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from backend.models.database import get_db
from backend.models.models import (
    Table, Reservation, InventoryItem, StockTransaction, Supplier,
    Employee, Attendance, SalaryRecord, Feedback, User, Order, OrderItem,
    MenuItem, Invoice, LoyaltyTransaction
)
from backend.schemas.schemas import (
    TableCreate, TableOut, ReservationCreate, ReservationOut,
    InventoryItemCreate, InventoryItemOut, StockAdjustment, SupplierCreate, SupplierOut,
    EmployeeCreate, EmployeeOut, AttendanceCreate, AttendanceOut,
    FeedbackCreate, FeedbackOut, DashboardStats
)
from backend.utils.auth import (
    get_current_user, require_admin_or_manager,
    require_staff_or_above, require_admin
)
from backend.utils.pdf_generator import generate_invoice_pdf


# ══════════════════════════════════════════════
# TABLES
# ══════════════════════════════════════════════
tables_router = APIRouter(prefix="/tables", tags=["Tables"])


@tables_router.get("", response_model=List[TableOut])
def list_tables(db: Session = Depends(get_db)):
    return db.query(Table).all()


@tables_router.post("", response_model=TableOut, status_code=201)
def create_table(
    data: TableCreate, db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_manager)
):
    t = Table(**data.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@tables_router.patch("/{table_id}/status")
def set_table_status(
    table_id: int, status: str, db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above)
):
    t = db.query(Table).filter(Table.id == table_id).first()
    if not t:
        raise HTTPException(404, "Table not found")
    t.status = status
    db.commit()
    return {"message": f"Table status set to {status}"}


# ══════════════════════════════════════════════
# RESERVATIONS
# ══════════════════════════════════════════════
reservations_router = APIRouter(prefix="/reservations", tags=["Reservations"])


@reservations_router.post("", response_model=ReservationOut, status_code=201)
def create_reservation(
    data: ReservationCreate, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check table available on that date/time
    conflict = db.query(Reservation).filter(
        Reservation.table_id == data.table_id,
        Reservation.reserved_date == data.reserved_date,
        Reservation.status.in_(["pending", "confirmed"]),
    ).first()
    if conflict:
        raise HTTPException(400, "Table already reserved at this time")

    r = Reservation(**data.model_dump(), customer_id=current_user.id)
    db.add(r)
    # Mark table reserved
    t = db.query(Table).filter(Table.id == data.table_id).first()
    if t:
        t.status = "reserved"
    db.commit()
    db.refresh(r)
    return r


@reservations_router.get("", response_model=List[ReservationOut])
def list_reservations(
    date_filter: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above)
):
    q = db.query(Reservation)
    if date_filter:
        q = q.filter(Reservation.reserved_date == date_filter)
    if status:
        q = q.filter(Reservation.status == status)
    return q.order_by(Reservation.reserved_date, Reservation.reserved_time).all()


@reservations_router.patch("/{res_id}/status")
def update_reservation_status(
    res_id: int, status: str, db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above)
):
    r = db.query(Reservation).filter(Reservation.id == res_id).first()
    if not r:
        raise HTTPException(404, "Reservation not found")
    r.status = status
    if status in ("cancelled", "completed"):
        t = db.query(Table).filter(Table.id == r.table_id).first()
        if t and t.status == "reserved":
            t.status = "available"
    db.commit()
    return {"message": f"Reservation {status}"}


# ══════════════════════════════════════════════
# INVENTORY
# ══════════════════════════════════════════════
inventory_router = APIRouter(prefix="/inventory", tags=["Inventory"])


@inventory_router.get("/suppliers", response_model=List[SupplierOut])
def list_suppliers(db: Session = Depends(get_db), _=Depends(require_admin_or_manager)):
    return db.query(Supplier).filter(Supplier.is_active == True).all()


@inventory_router.post("/suppliers", response_model=SupplierOut, status_code=201)
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db), _=Depends(require_admin_or_manager)):
    s = Supplier(**data.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@inventory_router.get("/items", response_model=List[InventoryItemOut])
def list_inventory(
    low_stock_only: bool = False, db: Session = Depends(get_db),
    _=Depends(require_admin_or_manager)
):
    q = db.query(InventoryItem).options(joinedload(InventoryItem.supplier)).filter(InventoryItem.is_active == True)
    if low_stock_only:
        q = q.filter(InventoryItem.current_stock <= InventoryItem.minimum_stock)
    return q.all()


@inventory_router.post("/items", response_model=InventoryItemOut, status_code=201)
def create_inventory_item(data: InventoryItemCreate, db: Session = Depends(get_db), _=Depends(require_admin_or_manager)):
    item = InventoryItem(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@inventory_router.post("/items/{item_id}/adjust")
def adjust_stock(
    item_id: int, data: StockAdjustment, db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above)
):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Inventory item not found")

    if data.transaction_type in ("consumption", "waste"):
        if float(item.current_stock) < float(data.quantity):
            raise HTTPException(400, "Insufficient stock")
        item.current_stock = float(item.current_stock) - float(data.quantity)
    else:
        item.current_stock = float(item.current_stock) + float(data.quantity)
        if data.transaction_type == "purchase":
            item.last_restocked = datetime.utcnow()

    tx = StockTransaction(
        inventory_item_id=item_id,
        transaction_type=data.transaction_type,
        quantity=data.quantity,
        unit_cost=data.unit_cost,
        total_cost=float(data.unit_cost or 0) * float(data.quantity),
        notes=data.notes,
        performed_by=current_user.id,
    )
    db.add(tx)
    db.commit()
    return {"message": "Stock adjusted", "current_stock": float(item.current_stock)}


@inventory_router.get("/low-stock")
def get_low_stock(db: Session = Depends(get_db), _=Depends(require_admin_or_manager)):
    items = db.query(InventoryItem).filter(
        InventoryItem.is_active == True,
        InventoryItem.current_stock <= InventoryItem.minimum_stock,
    ).all()
    return [{"id": i.id, "name": i.name, "current_stock": float(i.current_stock),
             "minimum_stock": float(i.minimum_stock), "unit": i.unit} for i in items]


# ══════════════════════════════════════════════
# EMPLOYEES
# ══════════════════════════════════════════════
employees_router = APIRouter(prefix="/employees", tags=["Employees"])


@employees_router.get("", response_model=List[EmployeeOut])
def list_employees(db: Session = Depends(get_db), _=Depends(require_admin_or_manager)):
    return db.query(Employee).options(joinedload(Employee.user)).filter(Employee.is_active == True).all()


@employees_router.post("", response_model=EmployeeOut, status_code=201)
def create_employee(data: EmployeeCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    emp = Employee(**data.model_dump())
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


@employees_router.post("/attendance", response_model=AttendanceOut, status_code=201)
def mark_attendance(data: AttendanceCreate, db: Session = Depends(get_db), _=Depends(require_staff_or_above)):
    existing = db.query(Attendance).filter(
        Attendance.employee_id == data.employee_id,
        Attendance.date == data.date
    ).first()
    if existing:
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(existing, k, v)
        db.commit()
        db.refresh(existing)
        return existing
    a = Attendance(**data.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@employees_router.get("/{emp_id}/attendance")
def get_attendance(
    emp_id: int, month: int, year: int,
    db: Session = Depends(get_db), _=Depends(require_admin_or_manager)
):
    records = db.query(Attendance).filter(
        Attendance.employee_id == emp_id,
        func.month(Attendance.date) == month,
        func.year(Attendance.date) == year,
    ).all()
    return records


# ══════════════════════════════════════════════
# FEEDBACK
# ══════════════════════════════════════════════
feedback_router = APIRouter(prefix="/feedback", tags=["Feedback"])


@feedback_router.post("", response_model=FeedbackOut, status_code=201)
def submit_feedback(
    data: FeedbackCreate, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    fb = Feedback(**data.model_dump(), customer_id=current_user.id)
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


@feedback_router.get("", response_model=List[FeedbackOut])
def list_feedback(
    status: Optional[str] = None, db: Session = Depends(get_db),
    _=Depends(require_admin_or_manager)
):
    q = db.query(Feedback)
    if status:
        q = q.filter(Feedback.status == status)
    return q.order_by(Feedback.created_at.desc()).all()


@feedback_router.patch("/{fb_id}/respond")
def respond_to_feedback(
    fb_id: int, response: str, db: Session = Depends(get_db),
    _=Depends(require_admin_or_manager)
):
    fb = db.query(Feedback).filter(Feedback.id == fb_id).first()
    if not fb:
        raise HTTPException(404, "Feedback not found")
    fb.admin_response = response
    fb.status = "resolved"
    db.commit()
    return {"message": "Response saved"}


# ══════════════════════════════════════════════
# REPORTS & DASHBOARD
# ══════════════════════════════════════════════
reports_router = APIRouter(prefix="/reports", tags=["Reports"])


@reports_router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _=Depends(require_admin_or_manager)):
    today = date.today()
    month_start = today.replace(day=1)

    today_orders = db.query(func.count(Order.id)).filter(
        func.date(Order.created_at) == today,
        Order.status != "cancelled"
    ).scalar() or 0

    today_revenue = db.query(func.sum(Order.total_amount)).filter(
        func.date(Order.created_at) == today,
        Order.payment_status == "paid"
    ).scalar() or 0

    monthly_revenue = db.query(func.sum(Order.total_amount)).filter(
        Order.created_at >= month_start,
        Order.payment_status == "paid"
    ).scalar() or 0

    pending_orders = db.query(func.count(Order.id)).filter(
        Order.status.in_(["pending", "confirmed", "preparing"])
    ).scalar() or 0

    active_tables = db.query(func.count(Table.id)).filter(
        Table.status == "occupied"
    ).scalar() or 0

    low_stock = db.query(func.count(InventoryItem.id)).filter(
        InventoryItem.current_stock <= InventoryItem.minimum_stock,
        InventoryItem.is_active == True
    ).scalar() or 0

    total_customers = db.query(func.count(User.id)).filter(
        User.role_id == 4
    ).scalar() or 0

    top_items = db.query(
        MenuItem.name,
        func.sum(OrderItem.quantity).label("qty")
    ).join(OrderItem).join(Order).filter(
        Order.created_at >= month_start
    ).group_by(MenuItem.id).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()

    return {
        "today_revenue": float(today_revenue),
        "today_orders": today_orders,
        "active_tables": active_tables,
        "pending_orders": pending_orders,
        "low_stock_count": low_stock,
        "total_customers": total_customers,
        "monthly_revenue": float(monthly_revenue),
        "top_items": [{"name": n, "qty": int(q)} for n, q in top_items],
    }


@reports_router.get("/sales")
def sales_report(
    period: str = "daily",  # daily/weekly/monthly
    db: Session = Depends(get_db),
    _=Depends(require_admin_or_manager)
):
    today = date.today()
    if period == "weekly":
        start = today - timedelta(days=7)
    elif period == "monthly":
        start = today.replace(day=1)
    else:
        start = today

    rows = db.query(
        func.date(Order.created_at).label("day"),
        func.count(Order.id).label("orders"),
        func.sum(Order.total_amount).label("revenue"),
    ).filter(
        Order.created_at >= start,
        Order.payment_status == "paid"
    ).group_by(func.date(Order.created_at)).order_by(func.date(Order.created_at)).all()

    return [{"date": str(r.day), "orders": r.orders, "revenue": float(r.revenue or 0)} for r in rows]


@reports_router.get("/invoices/{order_id}/pdf")
def download_invoice_pdf(
    order_id: int, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    invoice = db.query(Invoice).filter(Invoice.order_id == order_id).first()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    order = invoice.order
    if current_user.role.name == "customer" and order.customer_id != current_user.id:
        raise HTTPException(403, "Access denied")

    items = [{
        "name": oi.menu_item.name,
        "qty": oi.quantity,
        "unit_price": float(oi.unit_price),
        "total": float(oi.total_price),
    } for oi in order.items]

    pdf_data = generate_invoice_pdf({
        "invoice_number": invoice.invoice_number,
        "order_number": order.order_number,
        "issued_at": invoice.issued_at.strftime("%d %b %Y %H:%M"),
        "customer_name": invoice.customer_name,
        "customer_phone": invoice.customer_phone,
        "items": items,
        "subtotal": float(invoice.subtotal),
        "discount_amount": float(invoice.discount_amount),
        "gst_amount": float(invoice.gst_amount),
        "total_amount": float(invoice.total_amount),
        "payment_method": invoice.payment_method,
        "payment_reference": invoice.payment_reference,
    })

    return Response(
        content=pdf_data,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={invoice.invoice_number}.pdf"},
    )