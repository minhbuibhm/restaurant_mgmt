# Reflection Report — Applying SOLID Principles in IRMS

## Abstract

This report reflects on how SOLID principles guided the design and implementation of two core IRMS modules: Order Management and Kitchen Queue Management. Applying these principles resulted in a system where services are independently maintainable, business rules are isolated from HTTP handling, and new behaviors (e.g., new priority factors, new kitchen stations) can be added without modifying existing code. The main challenge was resisting the temptation to over-couple the Order and Kitchen modules for convenience — SOLID pushed us toward a cleaner boundary that paid off in testability and extensibility.

---

## How Each Principle Shaped the Design

### Single Responsibility Principle (SRP)

Each layer has exactly one reason to change:

- **Routers** handle HTTP concerns only (request parsing, response formatting). They contain zero business logic — every operation delegates to a service function.
- **Services** own the business rules. `order_service.py` manages order lifecycle and validation. `kitchen_service.py` manages queue prioritization and item status. Neither knows about HTTP status codes or request objects.
- **Models** define data structure. **Schemas** define API contracts.

**Impact:** When we needed to add auto-sync of order status based on item completion, the change was entirely within `kitchen_service.py`. No router or model changes were needed.

### Open/Closed Principle (OCP)

The priority scoring system in `kitchen_service.py` is the clearest example. The `calculate_priority_score()` function computes a weighted score from three factors: wait time, dish complexity, and station load.

Adding a new factor (e.g., VIP table priority, rush order flag) requires only:
1. Adding a new weight constant
2. Adding a new scoring term

The existing scoring terms and the queue-sorting logic remain untouched. The function is **open for extension** (new factors) but **closed for modification** (existing logic stays stable).

### Liskov Substitution Principle (LSP)

Status enums (`OrderStatus`, `OrderItemStatus`) serve as the type contract. Any valid status value can be used wherever the enum is expected. The state machine (`VALID_ORDER_TRANSITIONS`, `VALID_ITEM_TRANSITIONS`) is defined as a dictionary, not as conditional branches — so the system treats all statuses uniformly through lookup rather than special-casing.

This means adding a new status (e.g., `ON_HOLD`) only requires adding it to the enum and the transition map — all existing code that processes statuses continues to work.

### Interface Segregation Principle (ISP)

The Kitchen router only depends on `kitchen_service` functions. It never calls `order_service.create_order()` or any order-specific logic. Conversely, the Orders router doesn't know about priority scores or station loads.

Each service exposes only the functions its consumers need:
- **Order service:** `create_order`, `get_order`, `list_orders`, `update_order_status`, `cancel_order`
- **Kitchen service:** `get_kitchen_queue`, `advance_item_status`, `get_station_load`

No service is forced to depend on methods it doesn't use.

### Dependency Inversion Principle (DIP)

Routers depend on service functions (the abstraction layer), not on SQLAlchemy queries directly. Services depend on the `AsyncSession` interface injected via FastAPI's `Depends(get_db)`, not on a concrete database engine.

This means:
- Swapping PostgreSQL for another async-compatible database requires no service changes
- Testing services in isolation only requires providing a mock session
- Routers are decoupled from both the ORM and the database

---

## Challenges Faced

### 1. Order-Kitchen Coupling

The most significant design tension was the Order→Kitchen handoff. The naive approach would be for `order_service.update_order_status()` to directly call `kitchen_service` functions when an order is confirmed. This would create a hard dependency between the two modules.

**Solution:** Instead of explicit coupling, the kitchen queue is query-based — `get_kitchen_queue()` simply queries all `OrderItem` rows with status `queued`/`cooking` that belong to confirmed/preparing orders. No explicit "enqueue" step is needed. This keeps the two services independent while still achieving the end-to-end flow.

### 2. Bidirectional Status Sync

When a chef marks all items as `done`, the parent order should automatically become `ready`. This creates a reverse dependency (kitchen→order status).

**Solution:** The `_sync_order_status()` helper in `kitchen_service.py` handles this by directly updating the order's status field after item changes, based on simple rules (any cooking → preparing, all done → ready). This keeps the sync logic co-located with the kitchen module rather than splitting it across services.

### 3. Priority Scoring Extensibility

Defining a fixed scoring formula risks violating OCP when new business requirements arrive. We chose a weighted-sum approach with named constants (`WEIGHT_WAIT_TIME`, `WEIGHT_COMPLEXITY`, `WEIGHT_STATION_LOAD`), making it straightforward to add new terms without restructuring the function.

---

## Conclusion

SOLID principles provided concrete guardrails during implementation. SRP kept our files focused and small. OCP made the priority algorithm future-proof. DIP made the system testable. The result is a backend where each module can evolve independently — adding a new kitchen station type, changing the priority formula, or swapping the database engine each requires changes in exactly one place.
