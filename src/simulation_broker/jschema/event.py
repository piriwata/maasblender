# SPDX-FileCopyrightText: 2024 TOYOTA MOTOR CORPORATION and MaaS Blender Contributors
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, Extra
import typing


class Event(BaseModel, extra=Extra.allow):
    eventType: str
    source: str | None = None
    time: float
    service: str | None = None