# SPDX-FileCopyrightText: 2023 TOYOTA MOTOR CORPORATION and MaaS Blender Contributors
# SPDX-License-Identifier: Apache-2.0
from pydantic import BaseModel

from mblib.jschema import response
from mblib.jschema.events import Event

Message = response.Message
Peek = response.Peek
Step = response.Step[Event]


class DistanceMatrix(BaseModel):
    stops: list[str]
    matrix: list[list[float]]
