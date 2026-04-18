from dataclasses import dataclass, field

from app.schemas.kitchen import KitchenQueueItem
from app.services.priority_scorer import PriorityScorer


@dataclass
class KitchenQueue:
    pending_items: list[KitchenQueueItem] = field(default_factory=list)
    scorer: PriorityScorer = field(default_factory=PriorityScorer)

    def add_item(
        self,
        item: KitchenQueueItem,
        wait_seconds: float,
        prep_time_minutes: int,
        station_active_count: int,
    ) -> None:
        item.priority_score = self.scorer.calculate_score(
            wait_seconds=wait_seconds,
            prep_time_minutes=prep_time_minutes,
            station_active_count=station_active_count,
        )
        self.pending_items.append(item)

    def re_rank_by_priority(self) -> list[KitchenQueueItem]:
        self.pending_items.sort(key=lambda item: item.priority_score, reverse=True)
        return self.pending_items

    def get_estimated_wait_time(self, station_active_count: int, prep_time_minutes: int) -> int:
        return station_active_count * prep_time_minutes
