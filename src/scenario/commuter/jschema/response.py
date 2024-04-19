# SPDX-FileCopyrightText: 2023 TOYOTA MOTOR CORPORATION and MaaS Blender Contributors
# SPDX-License-Identifier: Apache-2.0
from pydantic import BaseModel
import typing

from mblib.jschema import response
from mblib.jschema.events import DemandEvent

Message = response.Message
Peek = response.Peek
StepEvent: typing.TypeAlias = DemandEvent
Step = response.Step[StepEvent]


class User(BaseModel):
    userId: str
    userType: str | None
