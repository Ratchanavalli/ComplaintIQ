"""
Seed the database with realistic sample complaints and demo users.
Run:  python -m src.db.seed
"""

from src.db.models import init_db, SessionLocal, Complaint, User
from src.api.auth import hash_password

DEMO_USERS = [
    # (username, password, role, full_name, email)
    ("admin",    "admin123",    "manager",  "Admin User",      "admin@shopiq.com"),
    ("manager1", "manager123",  "manager",  "Sarah Manager",   "sarah@shopiq.com"),
    ("alice",    "alice123",    "customer", "Alice Johnson",   "alice@example.com"),
    ("bob",      "bob123",      "customer", "Bob Smith",       "bob@example.com"),
    ("carol",    "carol123",    "customer", "Carol White",     "carol@example.com"),
    ("demo",     "demo123",     "customer", "Demo Customer",   "demo@example.com"),
]

SAMPLE_COMPLAINTS = [
    # ── Delivery ──────────────────────────────────────────────────────────────
    {
        "customer_id": "C001", "customer_name": "Alice Johnson",
        "email": "alice@example.com", "channel": "email",
        "product_id": "P101", "order_id": "ORD-2024-001",
        "complaint_text": (
            "My package was supposed to arrive 5 days ago and it still hasn't "
            "shown up. The tracking page just says 'In Transit' and nobody can "
            "tell me where it is. This is completely unacceptable!"
        ),
    },
    {
        "customer_id": "C002", "customer_name": "Bob Smith",
        "email": "bob@example.com", "channel": "chat",
        "product_id": "P205", "order_id": "ORD-2024-002",
        "complaint_text": (
            "Delivery was delayed by two weeks without any notification. I had "
            "to call three times to find out what was happening. Very poor "
            "communication from the delivery team."
        ),
    },
    {
        "customer_id": "C003", "customer_name": "Carol White",
        "email": "carol@example.com", "channel": "web",
        "product_id": "P310", "order_id": "ORD-2024-003",
        "complaint_text": (
            "My order arrived damaged. The box was completely crushed and the "
            "item inside was broken. Clearly the package was mishandled during "
            "shipping. I need a replacement immediately."
        ),
    },
    {
        "customer_id": "C004", "customer_name": "David Lee",
        "email": "david@example.com", "channel": "phone",
        "product_id": "P102", "order_id": "ORD-2024-004",
        "complaint_text": (
            "Wrong item delivered. I ordered a red jacket size L and received "
            "a blue shirt size M. How does this even happen? I need the correct "
            "item sent out today."
        ),
    },
    # ── Refund ────────────────────────────────────────────────────────────────
    {
        "customer_id": "C005", "customer_name": "Emma Davis",
        "email": "emma@example.com", "channel": "email",
        "product_id": "P415", "order_id": "ORD-2024-005",
        "complaint_text": (
            "I returned the product 3 weeks ago and still have not received my "
            "refund. I have the return tracking number that shows it was "
            "delivered. Please process my refund of $89.99 immediately."
        ),
    },
    {
        "customer_id": "C006", "customer_name": "Frank Brown",
        "email": "frank@example.com", "channel": "chat",
        "product_id": "P520", "order_id": "ORD-2024-006",
        "complaint_text": (
            "My refund request has been pending for 30 days. Every time I call "
            "I get a different story. This is beyond frustrating. I want my "
            "money back now."
        ),
    },
    {
        "customer_id": "C007", "customer_name": "Grace Kim",
        "email": "grace@example.com", "channel": "web",
        "product_id": "P621", "order_id": "ORD-2024-007",
        "complaint_text": (
            "I was charged twice for the same order. I can see two identical "
            "charges on my credit card statement. I need one of them reversed "
            "as soon as possible."
        ),
    },
    # ── Product Quality ───────────────────────────────────────────────────────
    {
        "customer_id": "C008", "customer_name": "Henry Wilson",
        "email": "henry@example.com", "channel": "email",
        "product_id": "P725", "order_id": "ORD-2024-008",
        "complaint_text": (
            "The product stopped working after just two weeks of normal use. "
            "The build quality is terrible. I've seen better craftsmanship on "
            "cheap dollar-store items. Completely disappointed."
        ),
    },
    {
        "customer_id": "C009", "customer_name": "Iris Martinez",
        "email": "iris@example.com", "channel": "phone",
        "product_id": "P830", "order_id": "ORD-2024-009",
        "complaint_text": (
            "The laptop battery drains in 2 hours even on battery-saver mode. "
            "The product description said 10-hour battery life. This is false "
            "advertising and the product is defective."
        ),
    },
    {
        "customer_id": "C010", "customer_name": "Jack Thompson",
        "email": "jack@example.com", "channel": "chat",
        "product_id": "P935", "order_id": "ORD-2024-010",
        "complaint_text": (
            "The colour of the shirt I received is nothing like the photo on "
            "your website. It looks completely different in real life. Very "
            "misleading product images."
        ),
    },
    {
        "customer_id": "C011", "customer_name": "Karen Garcia",
        "email": "karen@example.com", "channel": "web",
        "product_id": "P440", "order_id": "ORD-2024-011",
        "complaint_text": (
            "Found a piece of metal inside the food product I purchased. This "
            "is a serious safety hazard! I could have been seriously injured. "
            "This needs to be investigated urgently."
        ),
    },
    # ── Customer Service ──────────────────────────────────────────────────────
    {
        "customer_id": "C012", "customer_name": "Leo Anderson",
        "email": "leo@example.com", "channel": "email",
        "product_id": "P545", "order_id": "ORD-2024-012",
        "complaint_text": (
            "Your customer service representative was extremely rude and "
            "dismissive when I called about my issue. They kept interrupting "
            "me and ultimately hung up without resolving anything."
        ),
    },
    {
        "customer_id": "C013", "customer_name": "Mia Robinson",
        "email": "mia@example.com", "channel": "chat",
        "product_id": "P650", "order_id": "ORD-2024-013",
        "complaint_text": (
            "I have been waiting on hold for over 2 hours. This is the third "
            "time I've tried to reach support this week. No one ever answers "
            "and the chatbot is completely useless."
        ),
    },
    {
        "customer_id": "C014", "customer_name": "Noah Clark",
        "email": "noah@example.com", "channel": "phone",
        "product_id": "P755", "order_id": "ORD-2024-014",
        "complaint_text": (
            "The support agent promised to call me back within 24 hours but "
            "it's been 5 days and I've heard nothing. Every case I open just "
            "seems to disappear into a black hole."
        ),
    },
    # ── Positive feedback (edge case for sentiment) ───────────────────────────
    {
        "customer_id": "C015", "customer_name": "Olivia Harris",
        "email": "olivia@example.com", "channel": "web",
        "product_id": "P860", "order_id": "ORD-2024-015",
        "complaint_text": (
            "I had an issue with my order but the support team resolved it "
            "within an hour. Really impressed by how quickly they handled "
            "everything. Great service overall!"
        ),
    },
    # ── Neutral / Mixed ───────────────────────────────────────────────────────
    {
        "customer_id": "C016", "customer_name": "Paul Walker",
        "email": "paul@example.com", "channel": "email",
        "product_id": "P965", "order_id": "ORD-2024-016",
        "complaint_text": (
            "The delivery took longer than expected but the product itself is "
            "okay. I would appreciate better tracking updates in the future."
        ),
    },
    {
        "customer_id": "C017", "customer_name": "Quinn Scott",
        "email": "quinn@example.com", "channel": "chat",
        "product_id": "P170", "order_id": "ORD-2024-017",
        "complaint_text": (
            "Package arrived late but support explained there was a warehouse "
            "issue. I understand these things happen. The item was fine."
        ),
    },
    # ── Additional high-priority / critical ───────────────────────────────────
    {
        "customer_id": "C018", "customer_name": "Rachel Green",
        "email": "rachel@example.com", "channel": "phone",
        "product_id": "P275", "order_id": "ORD-2024-018",
        "complaint_text": (
            "I am going to escalate this to consumer protection if my refund "
            "is not processed today. I have been waiting 45 days. This is "
            "theft. I will be contacting my lawyer."
        ),
    },
    {
        "customer_id": "C019", "customer_name": "Sam Turner",
        "email": "sam@example.com", "channel": "web",
        "product_id": "P380", "order_id": "ORD-2024-019",
        "complaint_text": (
            "The electric kettle I bought started sparking and smoking after "
            "the first use. There could be a serious electrical fault in this "
            "product. This is a fire hazard and should be recalled immediately."
        ),
    },
    {
        "customer_id": "C020", "customer_name": "Tina Adams",
        "email": "tina@example.com", "channel": "email",
        "product_id": "P485", "order_id": "ORD-2024-020",
        "complaint_text": (
            "My package was marked as delivered but I never received it. "
            "Tracking shows it was left at the doorstep but it was not there "
            "when I got home. Possible theft or delivery to wrong address."
        ),
    },
]


def seed_users():
    """Seed demo users if none exist yet, then link complaints to user ids."""
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            print("Users already seeded. Skipping.")
            return

        users_created = {}
        for username, password, role, full_name, email in DEMO_USERS:
            user = User(
                username=username,
                password_hash=hash_password(password),
                role=role,
                full_name=full_name,
                email=email,
            )
            db.add(user)
            db.flush()  # get user.id before commit
            users_created[email] = user.id

        db.commit()
        print(f"Seeded {len(DEMO_USERS)} demo users.")

        # Link existing complaints whose email matches a demo customer
        for email, user_id in users_created.items():
            complaints = db.query(Complaint).filter_by(email=email).all()
            for c in complaints:
                c.customer_id = str(user_id)
        db.commit()
        print("Linked complaints to demo user IDs.")
    finally:
        db.close()


def seed():
    """Insert sample complaints then seed demo users."""
    init_db()
    db = SessionLocal()
    try:
        existing = db.query(Complaint).count()
        if existing > 0:
            print(f"Database already has {existing} complaints. Skipping seed.")
        else:
            for data in SAMPLE_COMPLAINTS:
                complaint = Complaint(**data)
                db.add(complaint)
            db.commit()
            print(f"Inserted {len(SAMPLE_COMPLAINTS)} sample complaints.")
    finally:
        db.close()

    # Always attempt to seed users (skips automatically if already done)
    seed_users()


if __name__ == "__main__":
    seed()
