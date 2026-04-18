from dataclasses import dataclass, field

from app.services.contracts import IPriorityStrategy, KitchenTicket
from app.services.priority_scorer import PriorityScorer


@dataclass
class KitchenQueue:
    tickets: list[KitchenTicket] = field(default_factory=list)
    strategy: IPriorityStrategy = field(default_factory=PriorityScorer)

    def add_item(
        self,
        ticket: KitchenTicket,
        station_active_count: int,
    ) -> None:
        ticket.calculate_priority(self.strategy, station_active_count)
        self.tickets.append(ticket)

    def enqueue(self, ticket: KitchenTicket, station_active_count: int) -> None:
        self.add_item(ticket, station_active_count)

    def dequeue(self) -> KitchenTicket | None:
        if not self.tickets:
            return None
        return self.tickets.pop(0)

    def reorder(self) -> list[KitchenTicket]:
        self.tickets.sort(key=lambda ticket: ticket.priority, reverse=True)
        return self.tickets

    def re_rank_by_priority(self) -> list[KitchenTicket]:
        return self.reorder()

    def get_estimated_wait_time(self, station_active_count: int, prep_time_minutes: int) -> int:
        return station_active_count * prep_time_minutes
