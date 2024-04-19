# SPDX-FileCopyrightText: 2023 TOYOTA MOTOR CORPORATION and MaaS Blender Contributors
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel

from mblib.jschema.events import ReserveEvent, DepartEvent


class Setup(BaseModel):
    walking_meters_per_minute: float = 80.0  # (m/min)


TriggeredEvent = ReserveEvent | DepartEvent
