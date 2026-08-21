"""
DataLens - Database Seed Script
Creates a SQLite database with a realistic sample business schema:
departments, employees, customers, deals.

Run this once to create/reset datalens.db
"""

import sqlite3
import random
from datetime import datetime, timedelta

random.seed(42)  # deterministic data so eval expectations don't drift on reseed

DB_PATH = "datalens.db"

# ---- Sample data pools (for generating realistic-looking rows) ----
DEPARTMENTS = ["Sales", "Engineering", "Marketing", "Customer Success", "Data & Analytics"]
FIRST_NAMES = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Sam", "Jamie", "Drew", "Avery"]
LAST_NAMES = ["Smith", "Johnson", "Lee", "Patel", "Garcia", "Chen", "Brown", "Davis", "Kim", "Nguyen"]
COMPANIES = ["Acme Corp", "Globex", "Initech", "Umbrella Co", "Stark Industries",
             "Wayne Enterprises", "Hooli", "Soylent", "Massive Dynamic", "Cyberdyne"]
DEAL_STAGES = ["prospecting", "negotiation", "closed_won", "closed_lost"]


def create_schema(conn):
    cur = conn.cursor()

    cur.executescript("""
    DROP TABLE IF EXISTS deals;
    DROP TABLE IF EXISTS customers;
    DROP TABLE IF EXISTS employees;
    DROP TABLE IF EXISTS departments;

    CREATE TABLE departments (
        department_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL
    );

    CREATE TABLE employees (
        employee_id INTEGER PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        department_id INTEGER NOT NULL,
        hire_date TEXT NOT NULL,
        salary INTEGER NOT NULL,
        FOREIGN KEY (department_id) REFERENCES departments(department_id)
    );

    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        company_name TEXT NOT NULL,
        industry TEXT NOT NULL,
        signup_date TEXT NOT NULL
    );

    CREATE TABLE deals (
        deal_id INTEGER PRIMARY KEY,
        customer_id INTEGER NOT NULL,
        owner_employee_id INTEGER NOT NULL,
        deal_value INTEGER NOT NULL,
        stage TEXT NOT NULL,
        created_date TEXT NOT NULL,
        closed_date TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
        FOREIGN KEY (owner_employee_id) REFERENCES employees(employee_id)
    );
    """)
    conn.commit()


def random_date(start_days_ago=730, end_days_ago=0):
    days = random.randint(end_days_ago, start_days_ago)
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")


def seed_data(conn):
    cur = conn.cursor()

    # Departments
    for i, name in enumerate(DEPARTMENTS, start=1):
        cur.execute("INSERT INTO departments (department_id, name) VALUES (?, ?)", (i, name))

    # Employees (30 employees across departments)
    for i in range(1, 31):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        dept_id = random.randint(1, len(DEPARTMENTS))
        hire_date = random_date(1000, 30)
        salary = random.randint(65000, 160000)
        cur.execute(
            "INSERT INTO employees (employee_id, first_name, last_name, department_id, hire_date, salary) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (i, first, last, dept_id, hire_date, salary)
        )

    # Customers (25 customers)
    industries = ["SaaS", "Retail", "Healthcare", "Finance", "Manufacturing", "Media"]
    for i in range(1, 26):
        company = f"{random.choice(COMPANIES)} {i}"
        industry = random.choice(industries)
        signup = random_date(700, 10)
        cur.execute(
            "INSERT INTO customers (customer_id, company_name, industry, signup_date) VALUES (?, ?, ?, ?)",
            (i, company, industry, signup)
        )

    # Deals (120 deals, only owned by Sales dept employees for realism)
    sales_employee_ids = [row[0] for row in cur.execute(
        "SELECT employee_id FROM employees WHERE department_id = "
        "(SELECT department_id FROM departments WHERE name = 'Sales')"
    ).fetchall()]
    if not sales_employee_ids:
        sales_employee_ids = list(range(1, 31))  # fallback

    for i in range(1, 121):
        customer_id = random.randint(1, 25)
        owner_id = random.choice(sales_employee_ids)
        deal_value = random.randint(5000, 500000)
        stage = random.choices(DEAL_STAGES, weights=[0.25, 0.2, 0.4, 0.15])[0]
        created = random_date(400, 5)
        closed = random_date(int(created[8:10]) if False else 200, 0) if stage in ("closed_won", "closed_lost") else None
        cur.execute(
            "INSERT INTO deals (deal_id, customer_id, owner_employee_id, deal_value, stage, created_date, closed_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (i, customer_id, owner_id, deal_value, stage, created, closed)
        )

    conn.commit()


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    create_schema(conn)
    seed_data(conn)

    # Quick sanity check
    cur = conn.cursor()
    for table in ["departments", "employees", "customers", "deals"]:
        count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count} rows")

    conn.close()
    print(f"\n✅ Database created at {DB_PATH}")
