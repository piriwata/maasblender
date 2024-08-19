# SPDX-FileCopyrightText: 2022 TOYOTA MOTOR CORPORATION and MaaS Blender Contributors
# SPDX-License-Identifier: Apache-2.0
from enum import Enum
from pydantic import BaseModel, AnyHttpUrl

from mblib.jschema.events import DemandEvent, ReservedEvent, DepartedEvent, ArrivedEvent


class PlannerSetting(BaseModel):
    endpoint: AnyHttpUrl


class PreferenceMode(str, Enum):
    fixed = "fixed_or_walking"
    prefer = "prefer_or_others"


class Setup(BaseModel):
    planner: PlannerSetting
    confirmed_services: list[str] = []
    preference_mode: PreferenceMode = PreferenceMode.fixed


# Note: OtherEvent must be described at the end
TriggeredEvent = DemandEvent | ReservedEvent | DepartedEvent | ArrivedEvent
