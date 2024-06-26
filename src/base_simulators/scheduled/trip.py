# SPDX-FileCopyrightText: 2022 TOYOTA MOTOR CORPORATION and MaaS Blender Contributors
# SPDX-License-Identifier: Apache-2.0
import typing
import dataclasses
from datetime import date

from core import Trip, Route, Service, StopTime, Stop, StopTimeWithDateTime, Path


@dataclasses.dataclass(frozen=True)
class SingleTrip(Trip):
    """Sequence of two or more stops that occur during a specific time period."""

    route: Route
    service: Service
    stop_times: typing.List[StopTime]
    block_id: str = ""

    def __post_init__(self):
        assert len(self.stop_times) >= 2

    @property
    def stops(self) -> typing.List[Stop]:
        return [stop_time.stop for stop_time in self.stop_times]

    def is_operation(self, at: date) -> bool:
        return self.service.is_operation(at)

    def stop_times_at(self, at_date: date):
        return [
            StopTimeWithDateTime(stop_time=stop_time, reference_date=at_date)
            for stop_time in self.stop_times
        ]

    def start_time(self, at: date):
        return list(self.stop_times_at(at))[0].arrival

    def end_time(self, at: date):
        return list(self.stop_times_at(at))[-1].departure

    def paths(self, org: Stop, dst: Stop, at: date):
        if not self.service.is_operation(at):
            return

        # This is redundant because a single trip may contain multiple identical stations.
        for stop_time_org in self.stop_times_at(at):
            if stop_time_org.stop == org:
                for stop_time_dst in self.stop_times_at(at):
                    if (
                        stop_time_dst.stop == dst
                        and stop_time_org.departure < stop_time_dst.arrival
                    ):
                        yield Path(pick_up=stop_time_org, drop_off=stop_time_dst)


@dataclasses.dataclass(frozen=True)
class BlockTrip(Trip):
    """Sequence of trips which belong to a block"""

    trips: typing.List[SingleTrip]

    def __post_init__(self):
        assert len(self.trips) >= 2
        assert len(set(trip.block_id for trip in self.trips)) <= 1
        assert self.trips[0].block_id != ""

        # The following assertion is generally true for most cases,
        assert (
            self.trips[0].stop_times[0].departure
            < self.trips[1].stop_times[0].departure
        )

    @property
    def stops(self) -> typing.List[Stop]:
        return [stop_time.stop for trip in self.trips for stop_time in trip.stop_times]

    def is_operation(self, at: date) -> bool:
        return any([trip.service.is_operation(at) for trip in self.trips])

    def stop_times_at(self, at: date):
        # Depending on the service configuration, a block trip can be split into multiple trips
        # instead of being treated as a single block trip depending on the day of the week,
        # but this will not be considered for now.
        return [
            StopTimeWithDateTime(stop_time=stop_time, reference_date=at)
            for trip in self.trips
            if trip.service.is_operation(at)
            for stop_time in trip.stop_times
        ]

    def start_time(self, at: date):
        return list(self.stop_times_at(at))[0].arrival

    def end_time(self, at: date):
        return list(self.stop_times_at(at))[-1].departure

    def paths(self, org: Stop, dst: Stop, at: date):
        if not self.is_operation(at):
            return

        for stop_time_org in self.stop_times_at(at):
            if stop_time_org.stop == org:
                for stop_time_dst in self.stop_times_at(at):
                    if (
                        stop_time_dst.stop == dst
                        and stop_time_org.departure < stop_time_dst.arrival
                    ):
                        yield Path(pick_up=stop_time_org, drop_off=stop_time_dst)
