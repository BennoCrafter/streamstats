"""Common data model for any streaming service we analyse."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterator, Optional


@dataclass
class ViewingEvent:
    """One watched/played item, normalised across services."""

    profile: str
    title: str
    start_time: datetime
    duration: timedelta
    service: str = ""
    device: Optional[str] = None
    country: Optional[str] = None


@dataclass
class BillingEvent:
    """One actually-charged payment, normalised across services."""

    date: date
    amount: float
    currency: str
    description: str


class StreamingService(ABC):
    """Superclass every service (Netflix, Disney+, Spotify, ...) implements."""

    name: str

    @abstractmethod
    def viewing_events(self) -> Iterator[ViewingEvent]:
        """Yield every watch/play event, oldest fields as exported by the service."""

    @abstractmethod
    def billing_events(self) -> Iterator[BillingEvent]:
        """Yield every actually-settled payment."""
