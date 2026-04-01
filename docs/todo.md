# IRMS Backend Implementation — TODO

## Abstract

This document outlines the implementation plan for 2 main modules of the IRMS backend: **Order Management** and **Kitchen Queue Management**. These two modules form the core business flow of the system — from order placement to kitchen fulfillment — and together they exercise the most architecturally significant qualities: real-time responsiveness, fault tolerance, and inter-service communication via events.

The current codebase has completed the **infrastructure layer** (FastAPI app, async DB, Docker), **model layer** (all ORM entities), and **schema layer** (all Pydantic DTOs). What remains is implementing the **service layer** (business logic) and **router layer** (API endpoints) for the chosen modules.

**Goal:** Deliver a working Order-to-Kitchen pipeline that demonstrates SOLID principles, event-driven decoupling, and priority-based queue management as described in the architecture design.

---

## Analysis

### Why Order + Kitchen?

The design document (docs/design.md §6.2) defines two primary business workflows:

1. **Order Flow:** Browse Menu → Place Order → Verify Stock → Route to Station → Rank Priority → Display on KDS → Complete → Serve
2. **Monitoring Flow:** Read Sensors → Filter → Update Inventory → Check Thresholds → Alert

Implementing modules (1) Order Management and (2) Kitchen Queue Management covers the **entire main business flow** end-to-end. This is more valuable than, say, Order + Inventory, because:

- The Order→Kitchen handoff is the **central event-driven interaction** in the system (docs/design.md §7.4: `order.created` → Kitchen consumes → `dish.ready`)
- Kitchen Queue requires a **priority scoring algorithm** (docs/design.md §8.4), which is the most architecturally interesting logic
- Together they touch all key SOLID principles: SRP (separate services), OCP (extensible priority scoring), DIP (services depend on abstractions, routers delegate to services)

### Current State

| Layer | Status |
|-------|--------|
| Models (Table, Order, OrderItem, MenuItem, Category, Ingredient, User) | Done |
| Schemas (Create/Update/Response DTOs for all entities) | Done |
| Routers (5 files: tables, menu, orders, inventory, dashboard) | Stub only |
| Services (order_service, kitchen_service, inventory_service) | Stub only |
| Infrastructure (main.py, database.py, config.py, Docker) | Done |

### SOLID Mapping

| Principle | How it applies |
|-----------|---------------|
| **SRP** | `OrderService` handles order lifecycle only. `KitchenService` handles queue ranking only. Routers only do HTTP — no business logic. |
| **OCP** | Priority scoring strategy is extensible — new factors (VIP table, rush order) can be added without modifying existing scoring logic. |
| **LSP** | Status transitions follow a state machine — any valid status can be substituted where the enum is expected. |
| **ISP** | Service interfaces expose only what each router needs. Kitchen doesn't need order creation; Orders don't need priority ranking. |
| **DIP** | Routers depend on service functions (abstractions), not on raw DB queries. Services depend on the DB session interface, not concrete engine. |

---

## TODO

### Phase 0 — Shared Foundations

- [x] Implement `menu` router CRUD (required: orders reference menu items, need seed data)
- [x] Implement `tables` router CRUD (required: orders reference tables)

### Phase 1 — Order Management Module

**Service: `order_service.py`**
- [x] `create_order()` — validate table exists, validate all menu_item_ids exist, calculate total_amount, persist Order + OrderItems
- [x] `get_order()` / `list_orders()` — query with eager-load items + menu_item details
- [x] `update_order_status()` — enforce status state machine (pending→confirmed→preparing→ready→served; any→cancelled)
- [x] `cancel_order()` — only if status is pending or confirmed

**Router: `orders.py`**
- [x] `POST /api/orders/` — accept OrderCreate, delegate to service, return OrderResponse
- [x] `GET /api/orders/{id}` — return single order with items
- [x] `GET /api/orders/` — list orders, optionally filter by table_id or status
- [x] `PATCH /api/orders/{id}/status` — accept new status, delegate state transition to service
- [x] `POST /api/orders/{id}/cancel` — cancel order

### Phase 2 — Kitchen Queue Management Module

**Service: `kitchen_service.py`**
- [x] `get_kitchen_queue()` — return all order items with status in (queued, cooking), sorted by priority score
- [x] `calculate_priority_score()` — score = f(wait_time, prep_complexity, station_load) per docs/design.md §8.4
- [x] `advance_item_status()` — queued→cooking→done, enforce valid transitions
- [x] `get_station_load()` — count active (cooking) items grouped by category (category ≈ station)
- [x] `route_to_station()` — routing is implicit via category→station mapping in get_kitchen_queue()

**Schemas: `kitchen.py`** (new file)
- [x] `KitchenQueueItem` — rich KDS view with priority_score, table_number, dish_name, wait_time
- [x] `KitchenItemStatusUpdate` — status update DTO
- [x] `StationLoad` — station name + active/queued counts

**Router: `kitchen.py`** (new file — KDS-facing endpoints)
- [x] `GET /api/kitchen/queue` — return prioritized queue for KDS display
- [x] `PATCH /api/kitchen/items/{id}/status` — chef updates item status (cooking, done)
- [x] `GET /api/kitchen/stations/load` — return current load per station

**Integration: Order → Kitchen**
- [x] Items with status `queued` auto-appear in kitchen queue when order is `confirmed` (query-based, not explicit enqueue)
- [x] `_sync_order_status()` auto-advances order: any item cooking → `preparing`, all done → `ready`

### Phase 3 — Wiring & Validation

- [x] Register new `kitchen` router in `main.py`
- [x] End-to-end test: create order → confirm → items appear in kitchen queue → cook → done → order ready
- [x] Verify Swagger docs at `/docs` reflect all new endpoints
