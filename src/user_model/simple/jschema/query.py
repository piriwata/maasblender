# SPDX-FileCopyrightText: 2022 TOYOTA MOTOR CORPORATION and MaaS Blender Contributors
# SPDX-License-Identifier: Apache-2.0
from pydantic import BaseModel, AnyHttpUrl

from jschema.events import DemandEvent, ReservedEvent, DepartedEvent, ArrivedEvent, Event as OtherEvent


class PlannerSetting(BaseModel):
    endpoint: AnyHttpUrl


class Setup(BaseModel):
    planner: PlannerSetting
    confirmed_services: list[str] = []


# Note: OtherEvent must be described at the end
TriggeredEvent = DemandEvent | ReservedEvent | DepartedEvent | ArrivedEvent | OtherEvent
