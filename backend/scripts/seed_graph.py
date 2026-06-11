import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neo4j import GraphDatabase
from app.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

SUPPLIERS = [
    {"id": "SUP001", "name": "Fresh Foods Ontario", "contact": "416-555-0101", "lead_time_hours": 24},
    {"id": "SUP002", "name": "Metro Food Distributors", "contact": "416-555-0102", "lead_time_hours": 12},
    {"id": "SUP003", "name": "Campus Beverage Supply", "contact": "416-555-0103", "lead_time_hours": 8},
    {"id": "SUP004", "name": "GTA Snack Wholesale", "contact": "416-555-0104", "lead_time_hours": 24},
    {"id": "SUP005", "name": "Emergency Foods Inc", "contact": "416-555-0199", "lead_time_hours": 4},
]

CATEGORIES = [
    {"name": "Hot Entrees", "reorder_point": 20, "max_stock": 120, "waste_threshold_pct": 5},
    {"name": "Beverages", "reorder_point": 30, "max_stock": 200, "waste_threshold_pct": 2},
    {"name": "Cold Items", "reorder_point": 15, "max_stock": 80, "waste_threshold_pct": 3},
    {"name": "Snacks", "reorder_point": 30, "max_stock": 100, "waste_threshold_pct": 2},
    {"name": "Breakfast", "reorder_point": 15, "max_stock": 80, "waste_threshold_pct": 3},
]

SUPPLIER_CATEGORY_RELATIONSHIPS = [
    ("SUP001", "Hot Entrees", {"primary": True, "discount_pct": 5}),
    ("SUP001", "Cold Items", {"primary": True, "discount_pct": 3}),
    ("SUP001", "Breakfast", {"primary": True, "discount_pct": 4}),
    ("SUP002", "Hot Entrees", {"primary": False, "discount_pct": 0}),
    ("SUP002", "Cold Items", {"primary": False, "discount_pct": 0}),
    ("SUP003", "Beverages", {"primary": True, "discount_pct": 8}),
    ("SUP004", "Snacks", {"primary": True, "discount_pct": 6}),
    ("SUP004", "Beverages", {"primary": False, "discount_pct": 2}),
    ("SUP005", "Hot Entrees", {"primary": False, "discount_pct": 0}),
    ("SUP005", "Beverages", {"primary": False, "discount_pct": 0}),
    ("SUP005", "Cold Items", {"primary": False, "discount_pct": 0}),
]

LOCATIONS = [
    {"name": "Seneca King Campus", "capacity": 500, "peak_hours": "11:30-13:30"},
    {"name": "Seneca Newnham Campus", "capacity": 350, "peak_hours": "12:00-14:00"},
    {"name": "Seneca Markham Campus", "capacity": 250, "peak_hours": "11:00-13:00"},
]

def seed_graph():
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )
    logger.info("Connected to Neo4j")
    with driver.session() as session:
        logger.info("Clearing existing graph data")
        session.run("MATCH (n) DETACH DELETE n")
        logger.info("Creating supplier nodes")
        for supplier in SUPPLIERS:
            session.run("""
                CREATE (s:Supplier {
                    id: $id,
                    name: $name,
                    contact: $contact,
                    lead_time_hours: $lead_time_hours
                })
            """, **supplier)
        logger.info("Creating category nodes")
        for category in CATEGORIES:
            session.run("""
                CREATE (c:Category {
                    name: $name,
                    reorder_point: $reorder_point,
                    max_stock: $max_stock,
                    waste_threshold_pct: $waste_threshold_pct
                })
            """, **category)
        logger.info("Creating location nodes")
        for location in LOCATIONS:
            session.run("""
                CREATE (l:Location {
                    name: $name,
                    capacity: $capacity,
                    peak_hours: $peak_hours
                })
            """, **location)
        logger.info("Creating supplier-category relationships")
        for sup_id, cat_name, props in SUPPLIER_CATEGORY_RELATIONSHIPS:
            session.run("""
                MATCH (s:Supplier {id: $sup_id})
                MATCH (c:Category {name: $cat_name})
                CREATE (s)-[:SUPPLIES {
                    primary: $primary,
                    discount_pct: $discount_pct
                }]->(c)
            """, sup_id=sup_id, cat_name=cat_name, **props)
        logger.info("Creating location-category relationships")
        for location in LOCATIONS:
            for category in CATEGORIES:
                session.run("""
                    MATCH (l:Location {name: $loc_name})
                    MATCH (c:Category {name: $cat_name})
                    CREATE (l)-[:SERVES]->(c)
                """, loc_name=location["name"], cat_name=category["name"])
        result = session.run("MATCH (n) RETURN count(n) as count")
        node_count = result.single()["count"]
        result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
        rel_count = result.single()["count"]
        logger.info(f"Graph seeded: {node_count} nodes, {rel_count} relationships")
    driver.close()
    return {"nodes": node_count, "relationships": rel_count}

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Seeding Neo4j Graph Database")
    logger.info("=" * 50)
    result = seed_graph()
    logger.info(f"Nodes created: {result['nodes']}")
    logger.info(f"Relationships created: {result['relationships']}")
    logger.info("=" * 50)