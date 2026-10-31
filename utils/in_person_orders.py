from datetime import datetime
from decimal import Decimal
from sqlalchemy import func
from models import Order, OrderFinancialRecord, OrderItem, Product, db
def create_in_person_order(form, actor):
 rows=[]
 for p in Product.query.filter_by(active=True).order_by(Product.name.asc()).with_for_update().all():
  raw=(form.get(f"quantity_{p.id}") or "").strip()
  if not raw: continue
  try: q=Decimal(raw)
  except Exception as ex: raise ValueError(f"Enter a valid quantity for {p.name}.") from ex
  if q<=0 or (not p.allow_fractional_quantity and q!=q.to_integral_value()): raise ValueError(f"Use a positive whole quantity for {p.name}.")
  if q>p.stock: raise ValueError(f"Not enough stock for {p.name}; only {p.stock:g} remains.")
  rows.append((p,q))
 if not rows: raise ValueError("Add at least one product to the in-person order.")
 name=form.get("buyer_name","").strip()[:120];phone=form.get("buyer_phone","").strip()[:40]
 if not name or not phone: name=f"customer{(db.session.query(func.count(Order.id)).filter(Order.order_channel=="in_person").scalar() or 0)+1}"
 total=sum((Decimal(str(p.price))*q for p,q in rows),Decimal("0.00")).quantize(Decimal("0.01"))
 o=Order(customer_name=name,phone=phone,address="In-person sale at farm counter",status="Confirmed",payment_status="Verified",payment_method="cash",payment_provider="in_person",payment_reference=form.get("payment_reference","").strip()[:160],fulfillment_type="pickup",delivery_zone_name="Farm counter",subtotal=total,total=total,order_channel="in_person",recorded_by=actor[:120])
 o.payment_verified_at=datetime.utcnow();o.payment_verified_by_role="owner" if actor=="Owner" else "salesperson";o.payment_verified_by_name=actor[:120];db.session.add(o);db.session.flush()
 db.session.add(OrderFinancialRecord(order=o,event_type="initial_payment",amount=total,status="settled",payment_method="cash",reference=o.payment_reference or "",notes="In-person sale recorded at the farm counter.",recorded_by=actor[:120],settled_at=o.payment_verified_at))
 for p,q in rows:
  o.items.append(OrderItem(product=p,product_name=p.name,quantity=q,unit_price=p.price,unit=p.unit,pricing_type="fixed",subtotal=(Decimal(str(p.price))*q).quantize(Decimal("0.01"))));p.stock-=q
 db.session.commit();return o
