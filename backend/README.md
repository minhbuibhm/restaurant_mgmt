# IRMS Backend — Intelligent Restaurant Management System

A FastAPI-based backend for managing restaurant operations including IoT-based ordering, kitchen queue management, inventory tracking, and staff dashboards. Two core modules are fully implemented: **Order Management** and **Kitchen Queue Management**, covering the end-to-end flow from order placement to kitchen fulfillment.

## Project Structure

```
backend/
├── Dockerfile
├── .env                        # Environment variables (DB connection)
├── .gitignore
├── requirements.txt
└── app/
    ├── main.py                 # FastAPI app entry point, router registration
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
    │   ├── order.py            # OrderCreate, OrderStatusUpdate, OrderResponse
    │   ├── kitchen.py          # KitchenQueueItem, KitchenItemStatusUpdate, StationLoad
    │   └── inventory.py        # IngredientCreate/Update/Response, InventoryLogResponse
    ├── routers/                # API route handlers — thin controllers
    │   ├── tables.py           # /api/tables — CRUD
    │   ├── menu.py             # /api/menu — categories + items CRUD
    │   ├── orders.py           # /api/orders — placement, status, cancel
    │   ├── kitchen.py          # /api/kitchen — queue, item status, station load
    │   ├── inventory.py        # /api/inventory (stub)
    │   └── dashboard.py        # /api/dashboard (stub)
    └── services/               # Business logic layer
        ├── order_service.py    # Order validation, total calc, status state machine
        ├── kitchen_service.py  # Priority scoring, item transitions, order auto-sync
        └── inventory_service.py# Stock management (stub)
```

## Documentation

All project documents are in `docs/`, ordered by reading flow:

| # | Document | Purpose |
|---|----------|---------|
| 1 | `requirements.md` | Assignment objectives, context, scope, and tasks |
| 2 | `design.md` | Architecture design: context, functional/non-functional requirements, architecture comparison (Event-Driven + Microservices), decision records, design principles |
| 3 | `todo.md` | Implementation plan: analysis of module choice (Order + Kitchen), SOLID mapping, phased task checklist |
| 4 | `api-interface.md` | API contract for UI integration: endpoint definitions, request/response shapes, WebSocket events, end-to-end flow diagram |
| 5 | `test-guide.md` | Test cases with curl commands and expected results, covering seed data, order flow, kitchen flow, cancel flow, and a quick smoke test script |
| 6 | `reflection-report.md` | SOLID principles reflection: how each principle shaped the design, challenges faced, and conclusions |

## SOLID Principles

### Single Responsibility Principle (SRP)

Each layer and each file has one clear responsibility:

- **models/**: Only defines database schema and column mappings. No business logic.
- **schemas/**: Only defines data validation and serialization shapes. No DB access.
- **routers/**: Only handles HTTP concerns (request parsing, response formatting). Delegates all logic to services.
- **services/**: Only contains business rules and orchestration. No HTTP or ORM coupling.

Within each layer, files are split by domain entity, so each file owns a single domain concept. `order_service.py` handles order lifecycle only. `kitchen_service.py` handles queue ranking only.

### Open/Closed Principle (OCP)

- Adding a new domain module (e.g., `payments`) requires creating new files and registering the router in `main.py` — no existing code needs modification.
- The priority scoring algorithm in `kitchen_service.py` uses weighted factors (`WEIGHT_WAIT_TIME`, `WEIGHT_COMPLEXITY`, `WEIGHT_STATION_LOAD`). Adding a new factor (e.g., VIP table) means adding a new weight and scoring term — existing terms stay untouched.
- Status state machines (`VALID_ORDER_TRANSITIONS`, `VALID_ITEM_TRANSITIONS`) are dict-based. Adding a new status means adding an entry, not modifying existing branches.

### Liskov Substitution Principle (LSP)

- All models inherit from `Base` (SQLAlchemy DeclarativeBase) and can be used interchangeably wherever a Base-derived model is expected (e.g., `Base.metadata.create_all` creates all tables regardless of type).
- All schemas inherit from `pydantic.BaseModel`, ensuring consistent validation and serialization behavior.
- Status enums are processed uniformly through dict lookup, not special-case branches — any valid status can be substituted.

### Interface Segregation Principle (ISP)

- Schemas are split into purpose-specific classes rather than a single monolithic DTO:
  - `OrderCreate` — only fields needed to create an order.
  - `OrderStatusUpdate` — only the new status field.
  - `OrderResponse` — only fields returned to the client.
- Kitchen router only depends on `kitchen_service` functions. Orders router only depends on `order_service`. Neither is forced to depend on methods it doesn't use.

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

### Applying Code Changes

The Dockerfile uses `COPY . .` at build time — source code is baked into the image. After modifying any Python file, **rebuild** the backend image, not just restart:

```bash
docker compose up -d --build backend
```

A plain `docker compose restart backend` will reuse the stale image and your changes won't take effect.

### Database Initialization

The database tables are **automatically created** on application startup via SQLAlchemy's `Base.metadata.create_all` in the `lifespan` handler (`app/main.py`). No manual migration step is needed for the initial setup.

### Seed Data

Sample seed data is **automatically loaded** on first startup (when the database is empty) by `app/seed.py`, called from the lifespan handler. The seeder is idempotent — if any data already exists, it skips and leaves the DB untouched.

Seeded content:
- 3 categories: `main`, `drink`, `dessert`
- 6 menu items with `image_url` populated (see below)
- 5 tables (numbers 1–5)
- 3 staff users (for testing role-based access):

  | Username | Password | Role | Can do |
  |----------|----------|------|--------|
  | `manager` | `manager` | MANAGER | Everything (menu/table CRUD, order/kitchen ops, cancel) |
  | `chef` | `chef` | CHEF | View kitchen queue, update item cooking status |
  | `waiter` | `waiter` | WAITER | Confirm/serve orders, update table status |

  Passwords match usernames for easy local testing — change in `app/seed.py` before production.

#### Menu Item Image URLs

Images are hosted externally on [TheMealDB](https://www.themealdb.com) and [TheCocktailDB](https://www.thecocktaildb.com) — free public food/drink image databases, no API key needed. If any URL breaks, replace it in `app/seed.py`.

| Menu Item | Source Dish (TheMealDB/CocktailDB) | URL |
|-----------|-----------------------------------|-----|
| Grilled Salmon | Baked salmon with fennel & tomatoes | https://www.themealdb.com/images/media/meals/1548772327.jpg |
| Beef Steak | Steak Diane | https://www.themealdb.com/images/media/meals/vussxq1511882648.jpg |
| Caesar Salad | Chicken Quinoa Greek Salad (closest match) | https://www.themealdb.com/images/media/meals/k29viq1585565980.jpg |
| Lemonade | New York Lemonade | https://www.thecocktaildb.com/images/media/drink/b3n0ge1503565473.jpg |
| Iced Coffee | Iced Coffee | https://www.thecocktaildb.com/images/media/drink/ytprxy1454513855.jpg |
| Tiramisu | Budino Di Ricotta (Italian dessert substitute) | https://www.themealdb.com/images/media/meals/1549542877.jpg |

To re-seed from scratch, wipe the DB volume and restart:

```bash
docker compose down -v
docker compose up --build
```


Database connection is configured in `.env`:

```
DATABASE_URL=postgresql+asyncpg://irms_user:irms_password@localhost:5432/irms_db
```

When running via Docker Compose, the backend container uses `db` as the hostname instead of `localhost`.

### Verify It Works

After startup (seed data already loaded), run a quick smoke test covering auth and the full Order→Kitchen flow:

```bash
BASE=http://localhost:8000/api

# 1. Login (waiter confirms orders, chef cooks)
WAITER=$(curl -s -X POST $BASE/auth/login -d "username=waiter&password=waiter" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
CHEF=$(curl -s -X POST $BASE/auth/login -d "username=chef&password=chef" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 2. Customer places order (public endpoint, no auth)
curl -s -X POST $BASE/orders/ -H 'Content-Type: application/json' \
  -d '{"table_id":1,"items":[{"menu_item_id":1,"quantity":2}]}'

# 3. Waiter confirms order
curl -s -X PATCH $BASE/orders/1/status -H "Authorization: Bearer $WAITER" \
  -H 'Content-Type: application/json' -d '{"status":"confirmed"}'

# 4. Chef views kitchen queue, cooks & finishes
curl -s $BASE/kitchen/queue -H "Authorization: Bearer $CHEF"
curl -s -X PATCH $BASE/kitchen/items/1/status -H "Authorization: Bearer $CHEF" \
  -H 'Content-Type: application/json' -d '{"status":"cooking"}'
curl -s -X PATCH $BASE/kitchen/items/1/status -H "Authorization: Bearer $CHEF" \
  -H 'Content-Type: application/json' -d '{"status":"done"}'

# 5. Verify order auto-advanced to "ready"
curl -s $BASE/orders/1
```

For the full test suite with all test cases and expected results, see `docs/test-guide.md`.

### API Documentation

Once the server is running, interactive docs are available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health check: `GET http://localhost:8000/health`
