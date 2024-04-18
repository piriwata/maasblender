# SPDX-FileCopyrightText: 2024 TOYOTA MOTOR CORPORATION
# SPDX-License-Identifier: Apache-2.0
import typing
from enum import StrEnum

from pydantic import BaseModel, Extra, model_validator

# TODO: replace with actual version URI once relaese information is available
VERSION_1 = "https://github.com/maasblender/maasblender/tree/main"


class EventType(StrEnum):
    DEMAND = "DEMAND"
    RESERVE = "RESERVE"
    RESERVED = "RESERVED"
    DEPART = "DEPART"
    DEPARTED = "DEPARTED"
    ARRIVED = "ARRIVED"


class Event(BaseModel):
    eventType: EventType
    source: str | None = (
        None  # not included within API response '/step', and set by broker
    )
    time: float


class Location(BaseModel):
    locationId: str
    lat: float
    lng: float


class DemandEventDetails(BaseModel, extra=Extra.allow):
    userId: str
    userType: str | None = None
    demandId: str
    org: Location
    dst: Location
    service: str | None = None
    dept: float | None = None  # immediate departure demand or arrive-by demand if None
    arrv: float | None = None  # arrive-by demand if not None


class DemandEvent(Event):
    eventType: typing.Literal[EventType.DEMAND]
    details: DemandEventDetails


class ReserveEventDetails(BaseModel, extra=Extra.allow):
    userId: str
    demandId: str
    org: Location
    dst: Location
    dept: float
    arrv: float | None = None


class ReserveEvent(Event):
    eventType: typing.Literal[EventType.RESERVE]
    service: str
    details: ReserveEventDetails


class Trip(BaseModel, extra=Extra.allow):
    org: Location
    dst: Location
    dept: float
    arrv: float
    service: str | None = None


class ReservedEventDetails(BaseModel, extra=Extra.allow):
    success: bool
    userId: str
    demandId: str
    route: list[Trip] = []


class ReservedEvent(Event):
    eventType: typing.Literal[EventType.RESERVED]
    details: ReservedEventDetails


class DepartEventDetails(BaseModel, extra=Extra.allow):
    userId: str
    demandId: str


class DepartEvent(Event):
    eventType: typing.Literal[EventType.DEPART]
    service: str
    details: DepartEventDetails


class DepartedArrivedEventDetails(BaseModel, extra=Extra.allow):
    userId: str | None
    demandId: str | None
    location: Location

    @model_validator(mode="after")
    def check_exist_id(self):
        if self.userId and not self.demandId:  # userId only
            raise ValueError(f"missing demandId with userId(={self.userId})")
        elif not self.userId and self.demandId:  # demandId only
            raise ValueError(f"missing userId with demandId(={self.demandId})")
        else:
            return self


class DepartedEvent(Event):
    eventType: typing.Literal[EventType.DEPARTED]
    details: DepartedArrivedEventDetails


class ArrivedEvent(Event):
    eventType: typing.Literal[EventType.ARRIVED]
    details: DepartedArrivedEventDetails
