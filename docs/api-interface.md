# API Interface Contract — For UI Integration

## Abstract

This document defines the backend API interface that the frontend will consume. It covers the **two implemented modules** — Order Management (Sales API) and Kitchen Queue Management (Kitchen API) — plus the supporting endpoints (Menu, Tables) required for the end-to-end flow.

The end-to-end flow is: **Customer browses menu → Places order → Order validated & routed to kitchen → Kitchen queue ranked by priority → Chef updates cooking status → Dish ready → Staff notified → Table served.** Every endpoint below maps to a step in this flow.

The architecture (docs/design.md §7.4) defines 4 UI contexts connecting through corresponding API groups. We implement 2 of them:

| UI Context | API Group | Purpose |
|------------|-----------|---------|
| **Ordering UI** (Tablet/QR) | Sales API | Browse menu, place orders, track order status |
| **Kitchen UI** (KDS Screen) | Kitchen API | View prioritized queue, update cooking status |

Real-time updates (KDS refresh, order status changes) are delivered via **WebSocket**, not polling.

---

## Authentication & Authorization

Staff endpoints require a JWT obtained via `POST /api/auth/login`. Customer endpoints (browsing menu, placing orders) are public because customers order via QR code without accounts.

### Login

`POST /api/auth/login` — form-encoded body (OAuth2 password flow)

Request: `username=<u>&password=<p>` (Content-Type: `application/x-www-form-urlencoded`)

Response:
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": { "id": 2, "username": "chef", "full_name": "Bob Chef", "role": "chef" }
}
```

### Using the token

All protected endpoints expect: `Authorization: Bearer <access_token>`

- `401 Unauthorized` — missing/invalid/expired token
- `403 Forbidden` — valid token but role not allowed

`GET /api/auth/me` — returns the current user (useful for frontend to verify session on load).

### Role → Endpoint matrix

| Endpoint group | Public | Waiter | Chef | Manager |
|----------------|:------:|:------:|:----:|:-------:|
| `GET /menu/*`, `GET /tables/*` | ✓ | ✓ | ✓ | ✓ |
| `POST /orders/`, `GET /orders/*` | ✓ | ✓ | ✓ | ✓ |
| `PATCH /orders/{id}/status` | — | ✓ | — | ✓ |
| `POST /orders/{id}/cancel` | — | — | — | ✓ |
| `PATCH /tables/{id}` | — | ✓ | — | ✓ |
| `GET /kitchen/*`, `PATCH /kitchen/items/*/status` | — | — | ✓ | ✓ |
| `POST /menu/*`, `PATCH /menu/*`, `POST /tables/` | — | — | — | ✓ |

---

## End-to-End Flow & API Mapping

```
[Ordering UI]                          [Kitchen UI / KDS]
     |                                        |
     |  1. GET /api/menu/items                |
     |  2. GET /api/tables/{id}               |
     |  3. POST /api/orders/                  |
     |         |                              |
     |    order.created event ----------->    |
     |                                4. GET  /api/kitchen/queue
     |                                5. PATCH /api/kitchen/items/{id}/status
     |                                        |
     |                                   dish.ready event
     |  6. GET /api/orders/{id}               |
     |         (status: ready)                |
     |  7. PATCH /api/orders/{id}/status      |
     |         (status: served)               |
```

---

## Sales API — Ordering UI Endpoints

### Menu (read-only for customers)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/menu/categories` | List all categories (drink, appetizer, main, dessert) |
| GET | `/api/menu/items` | List menu items, filter by `?category_id=` and `?available=true` |
| GET | `/api/menu/items/{id}` | Single item detail |

**MenuItemResponse**: `{ id, name, description, price, category_id, is_available, prep_time_minutes, image_url }`

### Tables

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/tables/` | List all tables |
| GET | `/api/tables/{id}` | Get table info (status, capacity) |

**TableResponse**: `{ id, number, capacity, status, qr_code }`

**TableStatus** enum: `available` | `occupied` | `reserved`

### Orders

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/orders/` | Place a new order |
| GET | `/api/orders/{id}` | Get order with all items |
| GET | `/api/orders/` | List orders, filter by `?table_id=` or `?status=` |
| PATCH | `/api/orders/{id}/status` | Update order status (e.g. mark as served) |
| POST | `/api/orders/{id}/cancel` | Cancel order (only if pending/confirmed) |

**OrderCreate** (request body):
```json
{
  "table_id": 1,
  "notes": "no spicy",
  "items": [
    { "menu_item_id": 5, "quantity": 2, "notes": "extra sauce" }
  ]
}
```

**OrderResponse**:
```json
{
  "id": 1,
  "table_id": 1,
  "status": "pending",
  "total_amount": 25.50,
  "notes": "no spicy",
  "created_at": "2026-04-01T12:00:00Z",
  "updated_at": "2026-04-01T12:00:00Z",
  "items": [
    { "id": 1, "menu_item_id": 5, "quantity": 2, "status": "queued", "notes": "extra sauce" }
  ]
}
```

**OrderStatus** state machine:
```
pending → confirmed → preparing → ready → served
          any state → cancelled (only from pending/confirmed)
```

**OrderItemStatus** enum: `queued` | `cooking` | `done` | `cancelled`

---

## Kitchen API — KDS UI Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/kitchen/queue` | Prioritized list of items to cook (status: queued/cooking) |
| PATCH | `/api/kitchen/items/{id}/status` | Chef advances item: queued→cooking→done |
| GET | `/api/kitchen/stations/load` | Current item count per station (grouped by category) |

**KitchenQueueItem** (response shape):
```json
{
  "order_item_id": 1,
  "order_id": 1,
  "table_number": 5,
  "dish_name": "Grilled Salmon",
  "quantity": 2,
  "category": "main",
  "status": "queued",
  "notes": "extra sauce",
  "priority_score": 87.5,
  "wait_time_seconds": 320,
  "prep_time_minutes": 15
}
```

**Priority score** (docs/design.md §8.4) is computed from: wait time, dish complexity (prep_time), and station load. Higher score = cook first.

**StationLoad** (response shape):
```json
[
  { "station": "main", "active_items": 4, "queued_items": 7 },
  { "station": "drink", "active_items": 1, "queued_items": 3 }
]
```

---

## WebSocket — Real-Time Updates

**Endpoint**: `ws://localhost:8000/ws`

The design (docs/design.md §7.4) specifies WebSocket for pushing real-time updates to KDS and Dashboard. Both UIs connect to one WebSocket endpoint and receive events:

| Event | Payload | Consumer |
|-------|---------|----------|
| `order.created` | `{ order_id, table_number, items[] }` | Kitchen UI |
| `item.status_changed` | `{ order_item_id, order_id, new_status }` | Ordering UI, Kitchen UI |
| `dish.ready` | `{ order_item_id, order_id, table_number, dish_name }` | Ordering UI (staff notification) |
| `order.status_changed` | `{ order_id, new_status }` | Ordering UI |

---

## Error Handling Convention

All error responses follow a consistent shape:

```json
{
  "detail": "Order not found"
}
```

| HTTP Status | Meaning |
|-------------|---------|
| 400 | Invalid request (bad input, invalid state transition) |
| 404 | Resource not found |
| 422 | Validation error (Pydantic) |

---

## Summary for UI Teams

- **Ordering UI** team: use Sales API (Menu + Tables + Orders). Poll or listen to WebSocket for order status updates.
- **Kitchen UI** team: use Kitchen API (Queue + Item status + Station load). Connect WebSocket for new order notifications; call PATCH to advance item status as chef cooks.
- Base URL: `http://localhost:8000`. Swagger docs: `/docs`.
