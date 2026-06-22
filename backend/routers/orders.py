from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from backend.models.database import get_db
from backend.models.models import Order, OrderItem, MenuItem, User, Table, Invoice, LoyaltyTransaction
from backend.schemas.schemas import OrderCreate, OrderOut
from backend.utils.auth import get_current_user, require_staff_or_above
from backend.config import settings

router = APIRouter(prefix="/orders", tags=["Orders"])


def _generate_order_number() -> str:
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    import random
    return f"ORD-{ts}-{random.randint(100, 999)}"


def _generate_invoice_number() -> str:
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    import random
    return f"INV-{ts}-{random.randint(100, 999)}"


@router.post("", response_model=OrderOut, status_code=201)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Build order
    order = Order(
        order_number=_generate_order_number(),
        customer_id=data.customer_id or (current_user.id if current_user.role.name == "customer" else None),
        table_id=data.table_id,
        staff_id=current_user.id if current_user.role.name in ("staff", "manager", "admin") else None,
        order_type=data.order_type,
        payment_method=data.payment_method,
        notes=data.notes,
        gst_percent=settings.DEFAULT_GST_PERCENT,
    )
    db.add(order)
    db.flush()  # get order.id

    subtotal = 0
    discount_total = 0
    for oi in data.items:
        menu_item = db.query(MenuItem).filter(MenuItem.id == oi.menu_item_id, MenuItem.is_available == True).first()
        if not menu_item:
            raise HTTPException(400, f"Menu item {oi.menu_item_id} not found or unavailable")

        unit_price = float(menu_item.price)
        disc_pct = float(menu_item.discount_percent)
        disc_amt = unit_price * disc_pct / 100
        effective_price = unit_price - disc_amt
        line_total = effective_price * oi.quantity
        discount_total += disc_amt * oi.quantity
        subtotal += unit_price * oi.quantity

        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=oi.menu_item_id,
            quantity=oi.quantity,
            unit_price=unit_price,
            discount_percent=disc_pct,
            total_price=line_total,
            special_instructions=oi.special_instructions,
        )
        db.add(order_item)

    gst_amount = (subtotal - discount_total) * settings.DEFAULT_GST_PERCENT / 100
    total_amount = subtotal - discount_total + gst_amount

    order.subtotal = subtotal
    order.discount_amount = discount_total
    order.gst_amount = gst_amount
    order.total_amount = total_amount
    order.status = "confirmed"

    # Mark table occupied
    if data.table_id and data.order_type == "dine-in":
        table = db.query(Table).filter(Table.id == data.table_id).first()
        if table:
            table.status = "occupied"

    db.commit()
    db.refresh(order)
    return order


@router.get("", response_model=List[OrderOut])
def list_orders(
    status: Optional[str] = None,
    order_type: Optional[str] = None,
    date: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.menu_item)
    )
    # Customers see only their own orders
    if current_user.role.name == "customer":
        q = q.filter(Order.customer_id == current_user.id)
    if status:
        q = q.filter(Order.status == status)
    if order_type:
        q = q.filter(Order.order_type == order_type)
    if date:
        q = q.filter(Order.created_at.like(f"{date}%"))
    return q.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.query(Order).options(
        joinedload(Order.items).joinedload(OrderItem.menu_item)
    ).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if current_user.role.name == "customer" and order.customer_id != current_user.id:
        raise HTTPException(403, "Access denied")
    return order


@router.patch("/{order_id}/status")
def update_order_status(
    order_id: int,
    new_status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    valid = ["pending", "confirmed", "preparing", "ready", "delivered", "cancelled"]
    if new_status not in valid:
        raise HTTPException(400, f"Status must be one of: {valid}")

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")

    order.status = new_status

    # Free table when delivered/cancelled
    if new_status in ("delivered", "cancelled") and order.table_id:
        table = db.query(Table).filter(Table.id == order.table_id).first()
        if table:
            table.status = "available"

    db.commit()
    return {"message": f"Order status updated to {new_status}"}


@router.post("/{order_id}/pay")
def process_payment(
    order_id: int,
    payment_method: str = "cash",
    payment_reference: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_above),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.payment_status == "paid":
        raise HTTPException(400, "Order already paid")

    order.payment_status = "paid"
    order.payment_method = payment_method
    order.status = "delivered"

    # Generate invoice
    invoice = Invoice(
        invoice_number=_generate_invoice_number(),
        order_id=order.id,
        subtotal=order.subtotal,
        discount_amount=order.discount_amount,
        gst_amount=order.gst_amount,
        total_amount=order.total_amount,
        payment_method=payment_method,
        payment_reference=payment_reference,
        paid_at=datetime.utcnow(),
    )
    if order.customer:
        invoice.customer_name = order.customer.name
        invoice.customer_phone = order.customer.phone
        invoice.customer_email = order.customer.email
    db.add(invoice)

    # Award loyalty points
    if order.customer_id:
        pts = int(float(order.total_amount) * settings.POINTS_PER_RUPEE)
        customer = db.query(User).filter(User.id == order.customer_id).first()
        customer.loyalty_points += pts
        lt = LoyaltyTransaction(
            customer_id=order.customer_id,
            order_id=order.id,
            points=pts,
            transaction_type="earned",
            description=f"Earned for order {order.order_number}",
        )
        db.add(lt)

    # Free table
    if order.table_id:
        table = db.query(Table).filter(Table.id == order.table_id).first()
        if table:
            table.status = "available"

    db.commit()
    db.refresh(invoice)
    return {"message": "Payment processed", "invoice_number": invoice.invoice_number}


@router.delete("/{order_id}", status_code=204)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.status in ("delivered", "cancelled"):
        raise HTTPException(400, "Cannot cancel this order")
    if current_user.role.name == "customer" and order.customer_id != current_user.id:
        raise HTTPException(403, "Access denied")
    order.status = "cancelled"
    db.commit()