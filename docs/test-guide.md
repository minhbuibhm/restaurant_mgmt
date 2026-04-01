# Test Guide — IRMS Backend

## Abstract

This guide provides test cases for verifying the two implemented modules: **Order Management** and **Kitchen Queue Management**. Tests follow the end-to-end business flow: seed data → place order → confirm → kitchen processes → serve. Each test case includes the curl command, what it validates, and the expected result.

**Prerequisites:** Run `docker compose up --build -d` and wait for startup. All endpoints are at `http://localhost:8000/api`. Swagger UI available at `http://localhost:8000/docs`.

---

## 1. Seed Data (run once)

These create the reference data that orders depend on.

| # | Action | Command | Expected |
|---|--------|---------|----------|
| S1 | Create category | `POST /menu/categories` `{"name":"main","description":"Main dishes"}` | 201, returns `id: 1` |
| S2 | Create 2nd category | `POST /menu/categories` `{"name":"drink","description":"Beverages"}` | 201, returns `id: 2` |
| S3 | Create menu item | `POST /menu/items` `{"name":"Grilled Salmon","price":15.5,"category_id":1,"prep_time_minutes":20}` | 201, `is_available: true` |
| S4 | Create drink item | `POST /menu/items` `{"name":"Lemonade","price":5.0,"category_id":2,"prep_time_minutes":3}` | 201 |
| S5 | Create table | `POST /tables/` `{"number":5,"capacity":4}` | 201, `status: available` |

---

## 2. Order Flow

| # | Action | Command | Expected |
|---|--------|---------|----------|
| O1 | Place order | `POST /orders/` `{"table_id":1,"items":[{"menu_item_id":1,"quantity":2},{"menu_item_id":2,"quantity":1}]}` | 201, `status: pending`, `total_amount: 36.0`, 2 items with `status: queued` |
| O2 | Get order | `GET /orders/1` | 200, order with all items populated |
| O3 | List by status | `GET /orders/?status=pending` | 200, returns array containing order 1 |
| O4 | Confirm order | `PATCH /orders/1/status` `{"status":"confirmed"}` | 200, `status: confirmed` |
| O5 | Invalid transition | `PATCH /orders/1/status` `{"status":"pending"}` | 400, "Cannot transition from 'confirmed' to 'pending'" |
| O6 | Serve before ready | `PATCH /orders/1/status` `{"status":"served"}` | 400, invalid transition |

### Order Validation

| # | Action | Command | Expected |
|---|--------|---------|----------|
| V1 | Invalid table | `POST /orders/` `{"table_id":999,"items":[{"menu_item_id":1,"quantity":1}]}` | 400, "Table not found" |
| V2 | Invalid menu item | `POST /orders/` `{"table_id":1,"items":[{"menu_item_id":999,"quantity":1}]}` | 400, "Menu item 999 not found" |

---

## 3. Kitchen Flow (after O4 — order is confirmed)

| # | Action | Command | Expected |
|---|--------|---------|----------|
| K1 | View queue | `GET /kitchen/queue` | 200, 2 items sorted by `priority_score` desc. Each has `table_number`, `dish_name`, `category`, `wait_time_seconds`, `priority_score` |
| K2 | Station load | `GET /kitchen/stations/load` | 200, `[{station:"main", queued:1, active:0}, {station:"drink", queued:1, active:0}]` |
| K3 | Start cooking salmon | `PATCH /kitchen/items/1/status` `{"status":"cooking"}` | 200, `status: cooking`, `order_status: preparing` |
| K4 | Station load update | `GET /kitchen/stations/load` | main: `active:1, queued:0` |
| K5 | Finish salmon | `PATCH /kitchen/items/1/status` `{"status":"done"}` | 200, `status: done`, order still `preparing` (drink not done) |
| K6 | Cook + finish drink | `PATCH /kitchen/items/2/status` `{"status":"cooking"}` then `{"status":"done"}` | After both done: `order_status: ready` |
| K7 | Invalid: done→cooking | `PATCH /kitchen/items/1/status` `{"status":"cooking"}` | 400, "Cannot transition item from 'done' to 'cooking'" |

---

## 4. Complete Flow (after K6 — order is ready)

| # | Action | Command | Expected |
|---|--------|---------|----------|
| F1 | Serve order | `PATCH /orders/1/status` `{"status":"served"}` | 200, `status: served` |
| F2 | Kitchen queue empty | `GET /kitchen/queue` | 200, `[]` (all items done) |
| F3 | Final order state | `GET /orders/1` | `status: served`, all items `status: done`, `total_amount: 36.0` |

---

## 5. Cancel Flow (create a new order for this)

| # | Action | Command | Expected |
|---|--------|---------|----------|
| C1 | Place new order | `POST /orders/` `{"table_id":1,"items":[{"menu_item_id":1,"quantity":1}]}` | 201, `status: pending` |
| C2 | Cancel from pending | `POST /orders/2/cancel` | 200, `status: cancelled`, all items `status: cancelled` |
| C3 | Cancel again | `POST /orders/2/cancel` | 400, cannot transition from cancelled |

---

## Quick Smoke Test (single script)

Run all critical steps in sequence to verify the full flow works:

```bash
BASE=http://localhost:8000/api

# Seed
curl -s -X POST $BASE/menu/categories -H 'Content-Type: application/json' -d '{"name":"main"}'
curl -s -X POST $BASE/menu/items -H 'Content-Type: application/json' -d '{"name":"Salmon","price":15.5,"category_id":1,"prep_time_minutes":20}'
curl -s -X POST $BASE/tables/ -H 'Content-Type: application/json' -d '{"number":1,"capacity":4}'

# Order flow
curl -s -X POST $BASE/orders/ -H 'Content-Type: application/json' -d '{"table_id":1,"items":[{"menu_item_id":1,"quantity":2}]}'
curl -s -X PATCH $BASE/orders/1/status -H 'Content-Type: application/json' -d '{"status":"confirmed"}'

# Kitchen flow
curl -s $BASE/kitchen/queue
curl -s -X PATCH $BASE/kitchen/items/1/status -H 'Content-Type: application/json' -d '{"status":"cooking"}'
curl -s -X PATCH $BASE/kitchen/items/1/status -H 'Content-Type: application/json' -d '{"status":"done"}'

# Verify
curl -s $BASE/orders/1  # should be "ready"
```
