# SPDX-FileCopyrightText: 2023 TOYOTA MOTOR CORPORATION and MaaS Blender Contributors
# SPDX-License-Identifier: Apache-2.0
from enum import Enum
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, conlist, constr, model_validator


class LocationSetting(BaseModel):
    locationId: str
    lat: float
    lng: float


class InputFilesItem(BaseModel):
    filename: str | None = None
    fetch_url: AnyHttpUrl | None = None

    @model_validator(mode="after")
    def check_exist_either(self):
        if self.filename or self.fetch_url:
            return self
        raise ValueError("specified neither filename nor fetch_url")


class OTPDetails(BaseModel):
    input_files: list[InputFilesItem]


class ServiceFileType(str, Enum):
    GBFS = "gbfs"
    GTFS = "gtfs"
    GTFS_FLEX = "gtfs_flex"


class NetworkSetting(BaseModel):
    type: ServiceFileType = ServiceFileType.GTFS
    input_files: conlist(InputFilesItem, min_length=1, max_length=1)
    agency_id: str | None = None  # equivalent to system_id for GBFS file


StreetMode = Literal[
    "WALK", "BICYCLE", "CAR", "BICYCLE_RENTAL", "CAR_RENTAL", "SCOOTER_RENTAL", "FLEX"
]
ParkingMode = Literal["BICYCLE_PARKING", "CAR_PARKING"]
TransitMode = Literal[
    "AIRPLANE",
    "BUS",
    "CABLE_CAR",
    "CARPOOL",
    "COACH",
    "FERRY",
    "FUNICULAR",
    "GONDOLA",
    "MONORAIL",
    "RAIL",
    "SNOW_AND_ICE",
    "SUBWAY",
    "TAXI",
    "TRAM",
    "TROLLEYBUS",
]


class TransitModePreferenceCostInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reluctance: float


class PlanTransitModePreferenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: TransitMode
    cost: TransitModePreferenceCostInput | None = None


class PlanTransitModesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access: list[StreetMode | ParkingMode | Literal["CAR_DROP_OFF"]] | None = None
    egress: list[StreetMode | Literal["CAR_PICKUP"]] | None = None
    transfer: list[Literal["WALK", "BICYCLE", "CAR"]] | None = None
    transit: list[PlanTransitModePreferenceInput] | None = None


class PlanModesInput(BaseModel):
    """OTP planConnection modes, passed to GraphQL without mode conversion."""

    model_config = ConfigDict(extra="forbid")

    direct: list[StreetMode | ParkingMode] | None = None
    directOnly: bool | None = None
    transit: PlanTransitModesInput | None = None
    transitOnly: bool | None = None


class Setup(BaseModel):
    otp_config: OTPDetails
    networks: dict[str, NetworkSetting]
    reference_time: constr(min_length=8, max_length=8)
    simulation_start_time: constr(pattern=r"^\d{2}:\d{2}$") = "00:00"
    modes: conlist(PlanModesInput, min_length=1) | None = None
    walking_meters_per_minute: float | None = (
        None  # get from router_config.json, if None
    )
    timezone: int = +9
