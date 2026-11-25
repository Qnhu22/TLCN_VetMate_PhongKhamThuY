"""Read-only inventory adapter, pending the inventory owner's final DDL.

Contract: inventory.products(productID, productCode, name, unit, status),
inventory.medicineProfiles(productID). No inventory tables are created here.
"""
from sqlalchemy import inspect

from app.extensions import db

products = db.table("products", db.column("productID"), db.column("productCode"),
                    db.column("name"), db.column("unit"), db.column("status"), schema="inventory")
profiles = db.table("medicineProfiles", db.column("productID"), schema="inventory")


def inventory_catalog_ready():
    inspector = inspect(db.session.connection())
    for name, needed in (("products", {"productID","productCode","name","unit","status"}),
                         ("medicineProfiles", {"productID"})):
        if not inspector.has_table(name, schema="inventory"):
            return False
        if not needed <= {column["name"] for column in inspector.get_columns(name, schema="inventory")}:
            return False
    return True


def inventory_fk_ready():
    inspector = inspect(db.session.connection())
    if not inspector.has_table("prescriptionItems", schema="medical"):
        return False
    return any(fk.get("constrained_columns") == ["productID"]
        and fk.get("referred_schema") == "inventory" and fk.get("referred_table") == "products"
        and fk.get("referred_columns") == ["productID"]
        for fk in inspector.get_foreign_keys("prescriptionItems", schema="medical"))


def catalog_query(active=True):
    query = db.select(products).where(db.exists(db.select(1).select_from(profiles)
        .where(profiles.c.productID == products.c.productID)))
    return query.where(products.c.status == "ACTIVE") if active else query


def medicine_options(keyword="", selected_ids=()):
    query = catalog_query()
    if keyword:
        query = query.where(db.or_(products.c.name.ilike(f"%{keyword}%"), products.c.productCode.ilike(f"%{keyword}%")))
    rows = list(db.session.execute(query.order_by(products.c.name,products.c.productID).limit(100)).mappings())
    if selected_ids:
        rows.extend(db.session.execute(catalog_query().where(products.c.productID.in_(selected_ids))).mappings())
    return list({row["productID"]:row for row in rows}.values())


def product_labels(ids):
    if not ids:
        return {}
    return {row["productID"]:row for row in db.session.execute(db.select(products)
        .where(products.c.productID.in_(ids))).mappings()}


def lock_medicines(ids):
    rows = list(db.session.execute(catalog_query().where(products.c.productID.in_(ids))
        .order_by(products.c.productID).with_for_update(of=products)).mappings())
    # Lock profiles too. The inventory owner must coordinate product/profile writes.
    profile_ids = set(db.session.scalars(db.select(profiles.c.productID)
        .where(profiles.c.productID.in_(ids))
        .order_by(profiles.c.productID).with_for_update()))
    # A profile may have disappeared while the product query waited for a lock.
    return {row["productID"] for row in rows} & profile_ids
