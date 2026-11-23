# SPDX-FileCopyrightText: 2023 TOYOTA MOTOR CORPORATION and MaaS Blender Contributors
# SPDX-License-Identifier: Apache-2.0
import asyncio
import datetime
import logging
import math
import re
import typing

import aiohttp
from core import Location, Path, Trip, calc_distance
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.aiohttp import log as aiohttp_logger
from jschema.response import DistanceMatrix

logger = logging.getLogger(__name__)
aiohttp_logger.setLevel(logging.WARNING)
pattern = re.compile(r".+:(.*)")


def id_from_gtfs_id(gtfs_id: str) -> str:
    return pattern.match(gtfs_id).groups()[0]


class OpenTripPlanner:
    def __init__(
        self,
        endpoint: str,
        ref_datetime: datetime.datetime,
        walking_meters_per_minute: float,
        transport_modes: list[typing.Mapping] | None,
        services: typing.Mapping[str, str],
    ):
        super().__init__()
        self.endpoint = endpoint
        self.client = Client(
            transport=AIOHTTPTransport(
                url=f"{endpoint}/otp/routers/default/index/graphql"
            ),
            fetch_schema_from_transport=True,
        )
        self.ref_datetime = ref_datetime
        self.walking_velocity = walking_meters_per_minute
        self.transport_modes = (
            transport_modes
            if transport_modes
            else [
                {
                    "direct": ["WALK"],
                    "transit": {
                        "access": ["WALK"],
                        "egress": ["WALK"],
                        "transfer": ["WALK"],
                    },
                },
                {"direct": ["WALK", "FLEX"], "directOnly": True},
                {
                    "direct": ["WALK"],
                    "transit": {
                        "access": ["WALK", "FLEX"],
                        "egress": ["WALK", "FLEX"],
                        "transfer": ["WALK"],
                    },
                },
            ]
        )
        self.services = services  # key: agency_id, value: service name

        # ToDo: overwrite otp default walking velocity to self.walking_velocity

    async def close(self):
        await self.client.close_async()

    async def agency_ids(self) -> set[str]:
        query = gql("""
        query Agencies {
          agencies {
            gtfsId
          }
        }
        """)
        response = await self.client.execute_async(query)
        return {id_from_gtfs_id(agency["gtfsId"]) for agency in response["agencies"]}

    def _elapsed(self, timestamp: str):
        return (
            datetime.datetime.fromtimestamp(int(timestamp) / 1000).astimezone()
            - self.ref_datetime
        ) / datetime.timedelta(minutes=1)

    async def health(self):
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(f"{self.endpoint}/otp/actuators/health") as resp,
            ):
                result = await resp.json()
            return result == {"status": "UP"}
        except aiohttp.ClientConnectionError:
            return False

    async def meters_for_all_stops_combinations(
        self, stops: list[Location], base: datetime.datetime
    ):
        matrix: list[list[float]] = []
        async with self.client as session:
            for stop_a in stops:
                vals = await asyncio.gather(
                    *[
                        self.distance(
                            session,
                            org=stop_a,
                            dst=stop_b,
                            date_time=base,
                        )
                        for stop_b in stops
                    ]
                )
                matrix.append(list(vals))
        return DistanceMatrix(stops=[stop.id_ for stop in stops], matrix=matrix)

    async def plan(
        self,
        org: Location,
        dst: Location,
        dept: float,
        arrv: float | None = None,
    ) -> list[Path]:
        paths: list[Path] = []
        for modes in self.transport_modes:
            async for path in self._plan_query(
                modes=modes, org=org, dst=dst, dept=dept, arrv=arrv
            ):
                if path not in paths:  # ignore duplicated walking path
                    paths.append(path)

        if arrv is not None:
            # arrive-by: sort by departure time descending (latest departure first)
            paths.sort(key=lambda e: e.dept, reverse=True)
        else:
            paths.sort(key=lambda e: e.arrv)

        if not any(
            all(trip.service == "walking" for trip in path.trips) for path in paths
        ):
            # If a walking route is not found, append a walking route.
            walk_path = self.straight_walk_path(org, dst, dept=dept, arrv=arrv)
            paths.append(walk_path)
            if not paths:
                logger.warning("no plan by OTP, and return straight walk path.")
            else:
                logger.warning(
                    "no walking plan found by OTP, and appended a walking path: %s",
                    walk_path,
                )

        return paths

    def straight_walk_path(
        self,
        org: Location,
        dst: Location,
        dept: float,
        arrv: float | None = None,
    ) -> Path:
        walk_time = calc_distance(org, dst) / self.walking_velocity
        if arrv is not None:
            dept = arrv - walk_time
        else:
            arrv = dept + walk_time
        return Path(
            trips=[
                Trip(
                    org=org,
                    dst=dst,
                    dept=dept,
                    arrv=arrv,
                    service="walking",
                )
            ],
            walking_time_minutes=walk_time,
        )

    async def stops(self) -> list[typing.Mapping[str, str]]:
        query = gql("""
        query Stops {
          stops {
            gtfsId
          }
        }
        """)

        response = await self.client.execute_async(query)
        return response["stops"]

    @staticmethod
    def _location_input(location: Location) -> dict:
        return {
            "label": location.id_,
            "location": {
                "coordinate": {"latitude": location.lat, "longitude": location.lng}
            },
        }

    async def distance(
        self, session, org: Location, dst: Location, date_time: datetime.datetime
    ) -> int:
        query = gql("""
        query DistanceQuery($origin: PlanLabeledLocationInput!, $destination: PlanLabeledLocationInput!, $dateTime: PlanDateTimeInput) {
          planConnection(
            origin: $origin
            destination: $destination
            dateTime: $dateTime
            modes: { direct: [CAR], directOnly: true }
            first: 1
          ) {
            edges {
              node {
                legs {
                    distance
                }
              }
            }
          }
        }
        """)

        response = await session.execute(
            query,
            variable_values={
                "dateTime": {"earliestDeparture": date_time.isoformat()},
                "origin": self._location_input(org),
                "destination": self._location_input(dst),
            },
        )

        if response["planConnection"]["edges"]:
            itinerary = response["planConnection"]["edges"][0]["node"]
            # Return the total distance across all itinerary legs.
            return sum(leg["distance"] for leg in itinerary["legs"])
        else:
            return -1

    async def _plan_query(
        self,
        modes: typing.Mapping,
        org: Location,
        dst: Location,
        dept: float,
        arrv: float | None = None,
    ):
        query = gql("""
    query PlanQuery($modes: PlanModesInput, $origin: PlanLabeledLocationInput!, $destination: PlanLabeledLocationInput!, $dateTime: PlanDateTimeInput) {
      planConnection(
        origin: $origin
        destination: $destination
        dateTime: $dateTime
        modes: $modes
        first: 3
        preferences: { transit: { transfer: { maximumTransfers: 4 } } }
      ) {
        edges {
          node {
            walkTime
            legs {
              mode
              agency {
                gtfsId
              }
              from {
                name
                lat
                lon
                stop {
                  gtfsId
                }
                departureTime
              }
              to {
                name
                lat
                lon
                stop {
                  gtfsId
                }
                arrivalTime
              }
            }
          }
        }
      }
    }
            """)

        if arrv is not None:
            # arrive-by: use arrv as the target time, round down to avoid overshooting
            target_datetime = self.ref_datetime + datetime.timedelta(
                seconds=math.floor(arrv * 60)
            )
            date_time_field = "latestArrival"
        else:
            # depart-after: use dept as the departure time, round up to avoid fractional seconds
            target_datetime = self.ref_datetime + datetime.timedelta(
                seconds=math.ceil(dept * 60)
            )
            date_time_field = "earliestDeparture"

        response = await self.client.execute_async(
            query,
            variable_values={
                "modes": modes,
                "dateTime": {date_time_field: target_datetime.isoformat()},
                "origin": self._location_input(org),
                "destination": self._location_input(dst),
            },
        )

        for edge in response["planConnection"]["edges"]:
            itinerary = edge["node"]
            itinerary["legs"][0]["from"]["name"] = org.id_
            itinerary["legs"][-1]["to"]["name"] = dst.id_
            yield Path(
                trips=[self._leg_to_trip(leg) for leg in itinerary["legs"]],
                walking_time_minutes=itinerary["walkTime"] / 60,
            )

    def _leg_to_trip(self, leg: typing.Mapping) -> Trip:
        org = leg["from"]
        dst = leg["to"]

        if leg["mode"] == "WALK":
            # walking
            service = "walking"
            org_id = org["name"]
            dst_id = dst["name"]
        elif leg["mode"] == "BICYCLE":
            # GBFS
            service = self.services[org["vehicleRentalStation"]["network"]]
            org_id = id_from_gtfs_id(org["vehicleRentalStation"]["stationId"])
            dst_id = id_from_gtfs_id(dst["vehicleRentalStation"]["stationId"])
        # GTFS
        else:
            service = self.services[id_from_gtfs_id(leg["agency"]["gtfsId"])]
            org_id = id_from_gtfs_id(org["stop"]["gtfsId"])
            dst_id = id_from_gtfs_id(dst["stop"]["gtfsId"])

        return Trip(
            service=service,
            org=Location(
                id_=org_id,
                lat=org["lat"],
                lng=org["lon"],
            ),
            dst=Location(
                id_=dst_id,
                lat=dst["lat"],
                lng=dst["lon"],
            ),
            dept=self._elapsed(org["departureTime"]),
            arrv=self._elapsed(dst["arrivalTime"]),
        )
