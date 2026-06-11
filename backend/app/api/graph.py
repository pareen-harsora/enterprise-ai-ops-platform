from fastapi import APIRouter, HTTPException
from neo4j import GraphDatabase
from app.config import settings
from app.core.logger import get_logger
from pydantic import BaseModel

router = APIRouter()
logger = get_logger(__name__)

def get_driver():
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )

@router.get("/graph/suppliers")
def get_all_suppliers():
    driver = get_driver()
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (s:Supplier)
                OPTIONAL MATCH (s)-[r:SUPPLIES]->(c:Category)
                RETURN s.id as id, s.name as name,
                       s.contact as contact,
                       s.lead_time_hours as lead_time,
                       collect(c.name) as categories,
                       collect(r.primary) as is_primary
            """)
            suppliers = []
            for record in result:
                suppliers.append({
                    "id": record["id"],
                    "name": record["name"],
                    "contact": record["contact"],
                    "lead_time_hours": record["lead_time"],
                    "categories_supplied": record["categories"],
                })
            return {"suppliers": suppliers, "total": len(suppliers)}
    finally:
        driver.close()

@router.get("/graph/category/{category_name}")
def get_category_supply_chain(category_name: str):
    driver = get_driver()
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (s:Supplier)-[r:SUPPLIES]->(c:Category {name: $category})
                MATCH (l:Location)-[:SERVES]->(c)
                RETURN s.name as supplier,
                       s.lead_time_hours as lead_time,
                       r.primary as is_primary,
                       r.discount_pct as discount,
                       c.reorder_point as reorder_point,
                       c.max_stock as max_stock,
                       collect(DISTINCT l.name) as locations
                ORDER BY r.primary DESC
            """, category=category_name)
            supply_chain = []
            for record in result:
                supply_chain.append({
                    "supplier": record["supplier"],
                    "lead_time_hours": record["lead_time"],
                    "is_primary_supplier": record["is_primary"],
                    "discount_pct": record["discount"],
                    "reorder_point": record["reorder_point"],
                    "max_stock": record["max_stock"],
                    "serves_locations": record["locations"]
                })
            if not supply_chain:
                raise HTTPException(
                    status_code=404,
                    detail=f"Category {category_name} not found in graph"
                )
            return {
                "category": category_name,
                "supply_chain": supply_chain,
                "primary_supplier": next(
                    (s for s in supply_chain if s["is_primary_supplier"]), None
                ),
                "backup_suppliers": [
                    s for s in supply_chain if not s["is_primary_supplier"]
                ]
            }
    finally:
        driver.close()

@router.get("/graph/fastest-supplier/{category_name}")
def get_fastest_supplier(category_name: str):
    driver = get_driver()
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (s:Supplier)-[:SUPPLIES]->(c:Category {name: $category})
                RETURN s.name as supplier,
                       s.contact as contact,
                       s.lead_time_hours as lead_time
                ORDER BY s.lead_time_hours ASC
                LIMIT 1
            """, category=category_name)
            record = result.single()
            if not record:
                raise HTTPException(status_code=404, detail="Category not found")
            return {
                "category": category_name,
                "fastest_supplier": record["supplier"],
                "contact": record["contact"],
                "lead_time_hours": record["lead_time"],
                "message": f"Call {record['supplier']} at {record['contact']} for fastest delivery in {record['lead_time']} hours"
            }
    finally:
        driver.close()

@router.get("/graph/stats")
def get_graph_stats():
    driver = get_driver()
    try:
        with driver.session() as session:
            nodes = session.run(
                "MATCH (n) RETURN count(n) as count"
            ).single()["count"]
            rels = session.run(
                "MATCH ()-[r]->() RETURN count(r) as count"
            ).single()["count"]
            suppliers = session.run(
                "MATCH (s:Supplier) RETURN count(s) as count"
            ).single()["count"]
            categories = session.run(
                "MATCH (c:Category) RETURN count(c) as count"
            ).single()["count"]
            return {
                "total_nodes": nodes,
                "total_relationships": rels,
                "suppliers": suppliers,
                "categories": categories,
            }
    finally:
        driver.close()