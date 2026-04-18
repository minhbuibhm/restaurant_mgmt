from app.services.contracts import IPriorityStrategy, KitchenTicket


class HybridPriorityStrategy(IPriorityStrategy):
    """Ranks kitchen tickets using wait time, complexity, and station load."""

    def __init__(
        self,
        wait_time_weight: float = 0.5,
        complexity_weight: float = 0.3,
        station_load_weight: float = 0.2,
        max_wait_seconds: int = 1800,
        max_prep_time: int = 60,
        max_station_load: int = 10,
    ) -> None:
        self.wait_time_weight = wait_time_weight
        self.complexity_weight = complexity_weight
        self.station_load_weight = station_load_weight
        self.max_wait_seconds = max_wait_seconds
        self.max_prep_time = max_prep_time
        self.max_station_load = max_station_load

    def weigh_wait_time(self, wait_seconds: float) -> float:
        return min(wait_seconds / self.max_wait_seconds, 1.0) * 100

    def weigh_complexity(self, prep_time_minutes: int) -> float:
        return (1 - min(prep_time_minutes / self.max_prep_time, 1.0)) * 100

    def weigh_station_load(self, station_active_count: int) -> float:
        return max(0, (1 - station_active_count / self.max_station_load)) * 100

    def calculate(self, ticket: KitchenTicket, station_load: int) -> float:
        return round(
            self.wait_time_weight * self.weigh_wait_time(ticket.wait_time_seconds)
            + self.complexity_weight * self.weigh_complexity(ticket.dish.average_prep_time)
            + self.station_load_weight * self.weigh_station_load(station_load),
            1,
        )


# Backward-compatible alias for the current codebase/report wording.
PriorityScorer = HybridPriorityStrategy
