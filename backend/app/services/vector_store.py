import os
from pathlib import Path
from app.core.logger import get_logger
from app.services.rag import get_embeddings, CHROMA_DIR, COLLECTION_NAME
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

logger = get_logger(__name__)

RUNBOOKS = {
    "inventory_management": """
OPERATIONS RUNBOOK: Inventory Management

1. REORDER POLICY
When closing stock falls below the reorder point, place an order immediately.
Standard reorder quantities:
- Beverages: Order 200 units when below 30 units
- Hot Entrees ingredients: Order 120 units when below 20 units  
- Cold Items: Order 80 units when below 15 units
- Snacks: Order 100 units when below 30 units

2. WASTE REDUCTION
Acceptable waste thresholds by category:
- Hot Entrees: Maximum 5% waste rate
- Cold Items: Maximum 3% waste rate
- Beverages: Maximum 2% waste rate
- Snacks: Maximum 2% waste rate

If waste exceeds threshold two consecutive days, reduce order quantity by 15%.

3. EMERGENCY STOCK PROTOCOL
If any item reaches zero stock during operating hours:
- Immediately notify the campus manager
- Check if substitute item is available
- Update menu boards within 15 minutes
- Document the stockout in the daily log

4. SUPPLIER CONTACT PROTOCOL
Primary supplier contact: Monday to Friday 7am to 4pm
Emergency orders: Use backup supplier list posted in kitchen
Lead time for standard orders: 24 hours
Lead time for emergency orders: 4 hours (additional cost applies)
""",

    "demand_forecasting": """
OPERATIONS RUNBOOK: Demand Forecasting and Planning

1. DAILY PLANNING PROCESS
Review AI forecast each morning before 8am.
Adjust staffing based on predicted demand:
- Under 200 units predicted: Minimum staffing (3 staff)
- 200 to 400 units predicted: Standard staffing (5 staff)
- Over 400 units predicted: Full staffing (7 staff)
- Event day over 500 units: Add 2 temporary staff

2. WEATHER ADJUSTMENTS
Apply these manual adjustments to AI forecasts:
- Heavy snow warning: Reduce forecast by 25%
- Rain forecast: Increase hot beverages by 20%
- Extreme cold below -20C: Reduce overall forecast by 30%

3. ACADEMIC CALENDAR IMPACTS
High demand periods requiring advance planning:
- Fall orientation (September): +40% demand
- Midterms (October, February): +15% demand  
- Exam periods (December, April): -20% demand
- Summer semester: -60% demand versus fall baseline

4. FORECAST ACCURACY REVIEW
Review forecast accuracy weekly every Monday.
If accuracy drops below 75% for 3 consecutive days:
- Flag for data team review
- Manually override with manager estimates
- Submit accuracy report to operations director
""",

    "food_safety": """
OPERATIONS RUNBOOK: Food Safety and Compliance

1. TEMPERATURE MONITORING
Hot foods must be held above 60C at all times.
Cold foods must be held below 4C at all times.
Check and log temperatures every 2 hours.

2. EXPIRY AND FRESHNESS
Daily checks required before opening:
- Remove all items past expiry date
- Check freshness of produce and dairy
- Rotate stock using FIFO (first in, first out)
- Document all discarded items with reason

3. ALLERGEN PROTOCOL
Always display current allergen information on menu boards.
Never substitute ingredients without updating allergen labels.
Staff must be trained on the top 14 allergens annually.

4. INCIDENT REPORTING
Any food safety incident must be reported within 1 hour to:
- Campus operations manager
- Health and Safety coordinator
- Document in incident log with full details
""",

    "customer_service": """
OPERATIONS RUNBOOK: Customer Service Standards

1. SERVICE TIME TARGETS
Peak hours (11:30am to 1:30pm):
- Maximum wait time at counter: 3 minutes
- Maximum wait time for hot food: 5 minutes

Off-peak hours:
- Maximum wait time: 2 minutes

If wait times exceed targets, open additional serving stations immediately.

2. COMPLAINT HANDLING
Step 1: Listen fully without interrupting
Step 2: Apologize sincerely regardless of fault
Step 3: Offer immediate resolution (replacement, refund, or discount)
Step 4: Document complaint in daily log
Step 5: Escalate to manager if customer remains unsatisfied

3. FEEDBACK COLLECTION
Encourage digital feedback via QR code at each station.
Review feedback daily during morning standup.
Share positive feedback with team weekly.
Action negative feedback within 48 hours.
""",

    "ai_governance": """
OPERATIONS RUNBOOK: AI System Usage and Governance

1. AI RECOMMENDATIONS POLICY
All AI-generated recommendations must be reviewed by a human manager
before implementation. AI recommendations are advisory only.

Managers have full authority to override any AI recommendation.
Document all overrides with reason in the operations log.

2. DATA PRIVACY
Customer transaction data used for AI training must be anonymized.
No personally identifiable information (PII) may be used in AI models.
Data retention policy: 3 years for aggregated data, 90 days for raw transactions.

3. AI ACCURACY MONITORING
Review AI forecast accuracy weekly.
If accuracy drops below 80% for 2 consecutive weeks:
- Escalate to data team immediately
- Suspend AI ordering recommendations
- Revert to manual planning process

4. ACCEPTABLE USE
AI tools may be used for:
- Demand forecasting and inventory planning
- Operations brief generation
- Anomaly detection and alerting

AI tools must NOT be used for:
- Individual employee performance evaluation
- Customer profiling or targeting
- Any decision that cannot be explained to affected parties
"""
}

def seed_vector_store():
    logger.info("Seeding vector store with operations runbooks")
    embeddings = get_embeddings()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", " "]
    )
    all_docs = []
    for runbook_name, content in RUNBOOKS.items():
        chunks = text_splitter.split_text(content)
        for i, chunk in enumerate(chunks):
            doc = Document(
                page_content=chunk,
                metadata={
                    "source": runbook_name,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
            )
            all_docs.append(doc)
    logger.info(f"Created {len(all_docs)} document chunks from runbooks")
    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR
    )
    vector_store.add_documents(all_docs)
    logger.info(
        f"Vector store seeded with {len(all_docs)} chunks "
        f"saved to {CHROMA_DIR}"
    )
    return len(all_docs)