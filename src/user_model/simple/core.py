# SPDX-FileCopyrightText: 2022 TOYOTA MOTOR CORPORATION and MaaS Blender Contributors
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import logging
from dataclasses import dataclass

import simpy

logger = logging.getLogger(__name__)


class Location:
    def __init__(self, id_, lat: float, lng: float):
        self.location_id = id_
        self.lat = lat
        self.lng = lng

    def __repr__(self):
        return f"Location({self.location_id}, {self.lat}, {self.lng})"

    def __str__(self):
        return self.location_id


class Runner:
    def __init__(self):
        self._env = simpy.Environment()

    @property
    def env(self):
        return self._env

    def start(self):
        pass

    def peek(self):
        return self.env.peek()

    def step(self):
        self.env.step()
        return self.env.now


class Task:
    def __call__(self, user: User) -> simpy.Event:
        raise NotImplementedError()


class User:
    """A moving object that travels between locations using multiple mobility services"""

    def __init__(
        self, id_: str, org: Location, dst: Location, dept: float, tasks: list[Task]
    ):
        self.user_id = id_
        self.org = org  # （旅程全体の）出発地
        self.dst = dst  # （旅程全体の）目的地
        self.dept = dept  # departure time
        self.task: Task | None = None  # 移動中の旅程
        self.tasks: list[Task] = tasks  # 未来の旅程

    def run(self):
        while True:
            if not len(self.tasks):
                return
            self.task = self.tasks.pop(0)
            failed = yield self.task(self)
            if failed:
                self.tasks = failed


@dataclass(frozen=True)
class Trip:
    org: Location
    dst: Location
    dept: float
    arrv: float
    service: str


@dataclass(frozen=True)
class Route:
    trips: list[Trip]

    @property
    def org(self):
        return self.trips[0].org

    @property
    def dst(self):
        return self.trips[-1].dst

    @property
    def dept(self):
        return self.trips[0].dept

    @property
    def arrv(self):
        return self.trips[-1].arrv

    def __iter__(self):
        return iter(self.trips)

    def is_walking_only(self) -> bool:
        return all(t.service == "walking" for t in self.trips)
