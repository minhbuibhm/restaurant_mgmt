# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IRMS (Intelligent Restaurant Management System) — a university software architecture assignment (HCMUT course 252). The project implements an IoT-based restaurant system with ordering, kitchen queue management, inventory tracking, and dashboards. The backend is a Python/FastAPI application with async PostgreSQL.

**Current state:** Two main modules are implemented end-to-end: **Order Management** and **Kitchen Queue Management**. Models, schemas, routers, and services for these modules are complete and verified. Inventory and dashboard routers remain as stubs.

## Commands

### Run everything with Docker
```bash
docker compose up --build
```

### Run only the database
```bash
docker compose up -d db
```

### Run backend locally (requires DB running)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API available at `http://localhost:8000`. Swagger docs at `/docs`, ReDoc at `/redoc`.

### Database
Tables auto-create on startup via `Base.metadata.create_all` in the lifespan handler. No Alembic migrations are configured yet (alembic is in requirements.txt but unused). Connection string is in `backend/.env`.

## Architecture

Four-layer structure inside `backend/app/`:

- **models/** — SQLAlchemy ORM models (async, mapped_column style). One file per domain: table, menu, order, inventory, user.
- **schemas/** — Pydantic v2 DTOs split by purpose: `*Create`, `*Update`, `*Response`. Includes `kitchen.py` for KDS-specific schemas.
- **routers/** — Thin FastAPI route handlers. All mounted under `/api` prefix in `main.py`. Routers delegate to services, not contain logic directly.
- **services/** — Business logic layer. `order_service.py` and `kitchen_service.py` are implemented. `inventory_service.py` is still a stub.

DB sessions are injected via `Depends(get_db)` from `database.py`. Config uses `pydantic-settings` reading from `backend/.env`.

### Implemented modules
- **Order Management**: `order_service.py` → `orders.py` router. Full CRUD, status state machine with `VALID_ORDER_TRANSITIONS`, input validation, total calculation.
- **Kitchen Queue Management**: `kitchen_service.py` → `kitchen.py` router. Priority scoring algorithm (wait_time, complexity, station_load), item status state machine, auto-sync of order status when all items are done.
- **Menu & Tables**: CRUD routers implemented as supporting modules for the order flow.

### Domain entities and relationships
- **Table** → has many **Orders**
- **Order** → has many **OrderItems**, each referencing a **MenuItem**
- **MenuItem** → belongs to a **Category**
- **Ingredient** / **InventoryLog** — standalone inventory tracking (stub)

### Key enums
- `OrderStatus`: pending → confirmed → preparing → ready → served | cancelled
- `OrderItemStatus`: queued → cooking → done | cancelled
- `TableStatus`: available | occupied | reserved

## Documentation

All project documents are in `docs/`:

- `design.md` — Architecture design: context, requirements, architecture comparison, decision records
- `todo.md` — Implementation plan with analysis and checklist
- `api-interface.md` — API contract for UI integration
- `test-guide.md` — Test cases with curl commands and expected results
- `reflection-report.md` — SOLID principles reflection report

The assignment requirements are in `docs/requirements.md` at the project root.

## Tech Stack

- Python 3.12+, FastAPI 0.115, Pydantic 2.10, SQLAlchemy 2.0 (async with asyncpg)
- PostgreSQL 16 (Docker image: postgres:16-alpine)
- Docker Compose for local orchestration

## Design Constraints

This is a SOLID-principles assignment. When adding new domain modules, follow the existing pattern: create `models/<entity>.py`, `schemas/<entity>.py`, `routers/<entity>.py`, `services/<entity>_service.py`, then register the router in `main.py`.
