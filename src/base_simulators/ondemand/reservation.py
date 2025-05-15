# SPDX-FileCopyrightText: 2022 TOYOTA MOTOR CORPORATION and MaaS Blender Contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import logging
import typing
from datetime import timedelta

from core import Trip, Stop, Network, User
from mobility import Car, Route, StopTime
from event import EventQueue


logger = logging.getLogger(__name__)


class CarSetting(typing.NamedTuple):
    mobility_id: str
    capacity: int
    trip: Trip
    stop: Stop


class Evaluation:
    def __init__(self, car: Car, plan: Route):
        self.car = car
        self.stop_times = plan.stop_times
        self.values = [timedelta(days=1)]
        self.value = timedelta(days=1)

        start_window, end_window = car.window()
        # unavailable
        if start_window is None:
            return

        if to := self.car.moving:
            # If on moving, set to the next stop and time.
            previous = StopTime(stop=to.stop, departure=to.arrival)
        else:
            # If not on moving, set to the current stop and time.
            now = self.car.env.datetime_now
            if now >= start_window:
                previous = StopTime(stop=car.stop, departure=now)
            else:
                # wait till start time
                previous = StopTime(stop=car.stop, departure=start_window)

        for previous, stop_time in zip([previous] + plan.stop_times, plan.stop_times):
            stop_time.arrival = previous.departure + timedelta(
                minutes=self.car.network.duration(
                    previous.stop.stop_id, stop_time.stop.stop_id
                )
            )
            stop_time.departure = max(
                [
                    stop_time.arrival
                    + self.car.board_time * bool(stop_time.off)
                    + self.car.board_time * bool(stop_time.on)
                ]
                + [user.desired_dept + self.car.board_time for user in stop_time.on]
            )

        if plan.stop_times[-1].arrival <= end_window:
            self.values = [
                stop_time.arrival
                - user.desired_dept
                + self.car.board_time
                - user.ideal_duration
                for stop_time in plan.stop_times
                for user in stop_time.off
            ]
            self.value = sum(self.values, timedelta()) / len(self.values)

    def __lt__(self, other: Evaluation):
        return self.value < other.value


class CarManager:
    """responsible for processing across multiple on-demand buses."""

    def __init__(
        self,
        network: Network,
        event_queue: EventQueue,
        max_delay_time: float,
        settings: typing.Collection[CarSetting],
    ):
        self.network = network
        self.event_queue = event_queue
        self.max_delay_time: timedelta = timedelta(minutes=max_delay_time)
        self.mobilities: typing.Dict[str, Car] = {
            setting.mobility_id: Car(
                network=self.network,
                queue=self.event_queue,
                mobility_id=setting.mobility_id,
                capacity=setting.capacity,
                trip=setting.trip,
                stop=setting.stop,
            )
            for setting in settings
        }

    @property
    def env(self):
        return self.event_queue.env

    def depart(self, user_id: str):
        for mobility in self.mobilities.values():
            if user := mobility.find_reserved_user(user_id):
                mobility.user_ready(user)
                return user

    def reserve(self, user: User):
        self.env.process(self._reserve(user))

    def _reserve(self, user: User):
        yield self.env.timeout(0)

        if solution := self.minimum_delay(user):
            departure = None
            for stop_time in solution.stop_times:
                if user in stop_time.on:
                    departure = stop_time.departure
                if user in stop_time.off:
                    assert departure
                    self.event_queue.reserved(
                        mobility=solution.car,
                        user=user,
                        departure=departure,
                        arrival=stop_time.arrival,
                    )

            solution.car.reserve(user=user, schedule=solution.stop_times)

        else:
            self.event_queue.reserve_failed(user)

    def minimum_delay(self, user: User) -> Evaluation | None:
        return min(
            (
                Evaluation(mobility, route)
                for mobility in self.mobilities.values()
                if (route := mobility.solve_new_route(user))
            ),
            default=None,
        )
