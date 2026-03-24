# IRMS Backend - Intelligent Restaurant Management System

A FastAPI-based backend for managing restaurant operations including IoT-based ordering, kitchen queue management, inventory tracking, and staff dashboards.

## Project Structure

```
backend/
├── Dockerfile
├── .env                        # Environment variables (DB connection)
├── .gitignore
├── requirements.txt
└── app/
    ├── main.py                 # FastAPI application entry point, router registration
    ├── config.py               # Application settings (pydantic-settings)
    ├── database.py             # Async SQLAlchemy engine, session factory, Base class
    ├── models/                 # ORM layer — one file per domain entity
    │   ├── table.py            # Table, TableStatus
    │   ├── menu.py             # Category, MenuItem
    │   ├── order.py            # Order, OrderItem, OrderStatus, OrderItemStatus
    │   ├── inventory.py        # Ingredient, InventoryLog
    │   └── user.py             # User, UserRole
    ├── schemas/                # Pydantic DTOs — request/response validation
    │   ├── table.py            # TableCreate, TableUpdate, TableResponse
    │   ├── menu.py             # CategoryCreate/Response, MenuItemCreate/Update/Response
    │   ├── order.py            # OrderCreate, OrderItemCreate, OrderResponse
    │   └── inventory.py        # IngredientCreate/Update/Response, InventoryLogResponse
    ├── routers/                # API route handlers — thin controllers
    │   ├── tables.py           # /api/tables
    │   ├── menu.py             # /api/menu
    │   ├── orders.py           # /api/orders
    │   ├── inventory.py        # /api/inventory
    │   └── dashboard.py        # /api/dashboard
    └── services/               # Business logic layer
        ├── order_service.py    # Order processing, validation, queue prioritization
        ├── inventory_service.py# Stock management, threshold alerts
        └── kitchen_service.py  # Kitchen display system, station load balancing
```

## SOLID Principles

### Single Responsibility Principle (SRP)

Each layer and each file has one clear responsibility:

- **models/**: Only defines database schema and column mappings. No business logic.
- **schemas/**: Only defines data validation and serialization shapes. No DB access.
- **routers/**: Only handles HTTP concerns (request parsing, response formatting). Delegates logic to services.
- **services/**: Only contains business rules and orchestration. No HTTP or ORM coupling.

Within each layer, files are split by domain entity (table, menu, order, inventory, user), so each file owns a single domain concept.

### Open/Closed Principle (OCP)

- Adding a new domain module (e.g., `payments`) requires creating new files (`models/payment.py`, `schemas/payment.py`, `routers/payments.py`, `services/payment_service.py`) and registering the router in `main.py` — no existing code needs modification.
- Enum-based statuses (`OrderStatus`, `TableStatus`) can be extended with new values without changing the logic that reads them.

### Liskov Substitution Principle (LSP)

- All models inherit from `Base` (SQLAlchemy DeclarativeBase) and can be used interchangeably wherever a Base-derived model is expected (e.g., `Base.metadata.create_all` creates all tables regardless of type).
- All schemas inherit from `pydantic.BaseModel`, ensuring consistent validation and serialization behavior.

### Interface Segregation Principle (ISP)

- Schemas are split into purpose-specific classes rather than a single monolithic DTO:
  - `TableCreate` — only fields needed to create a table.
  - `TableUpdate` — only fields that can be modified (all optional).
  - `TableResponse` — only fields returned to the client.
- Clients never need to provide fields they don't use.

### Dependency Inversion Principle (DIP)

- Routers depend on the **services layer** (abstraction), not directly on SQLAlchemy models or raw queries.
- Database sessions are injected via FastAPI's `Depends(get_db)`, so routers and services don't create or manage their own connections.
- `config.py` uses `pydantic-settings` to abstract environment variable access — the application depends on the `Settings` interface, not on `os.environ` directly.

## Getting Started

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- PostgreSQL 16 (provided via Docker)

### Option 1: Run with Docker (recommended)

Start both the database and backend:

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

To start only the database:

```bash
docker compose up -d db
```

### Option 2: Run locally via terminal

1. Start the database container:

```bash
docker compose up -d db
```

2. Create and activate a virtual environment:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the server:

```bash
uvicorn app.main:app --reload
```

### Database Initialization

The database tables are **automatically created** on application startup via SQLAlchemy's `Base.metadata.create_all` in the `lifespan` handler (`app/main.py`). No manual migration step is needed for the initial setup.

Database connection is configured in `.env`:

```
DATABASE_URL=postgresql+asyncpg://irms_user:irms_password@localhost:5432/irms_db
```

When running via Docker Compose, the backend container uses `db` as the hostname instead of `localhost`.

### API Documentation

Once the server is running, interactive docs are available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health check: `GET http://localhost:8000/health`
