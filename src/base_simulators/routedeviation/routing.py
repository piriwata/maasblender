# SPDX-FileCopyrightText: 2026 TOYOTA MOTOR CORPORATION and MaaS Blender Contributors
# SPDX-License-Identifier: Apache-2.0
from abc import ABC, abstractmethod
from datetime import datetime

from core import DeviatedStopTimeWithDateTime, Stop, TemporaryStop


class Router(ABC):
    @abstractmethod
    async def plan(
        self,
        origin: Stop,
        destination: Stop,
        temporary_stops: list[TemporaryStop],
        departure: datetime,
        arrival: datetime,
    ) -> list[DeviatedStopTimeWithDateTime] | None:
        raise NotImplementedError


class EqualIntervalRouter(Router):
    async def plan(
        self,
        origin: Stop,
        destination: Stop,
        temporary_stops: list[TemporaryStop],
        departure: datetime,
        arrival: datetime,
    ) -> list[DeviatedStopTimeWithDateTime]:
        duration = arrival - departure
        return [
            DeviatedStopTimeWithDateTime(
                stop, departure + i / (len(temporary_stops) + 1) * duration
            )
            for i, stop in enumerate(temporary_stops, 1)
        ]
