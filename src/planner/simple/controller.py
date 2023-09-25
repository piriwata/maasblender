# SPDX-FileCopyrightText: 2022 TOYOTA MOTOR CORPORATION and MaaS Blender Contributors
# SPDX-License-Identifier: Apache-2.0
import datetime
import io
import logging
import typing
import zipfile

import aiohttp
import fastapi

import httputil
from config import env
from core import Location, MobilityNetwork, WalkingNetwork, Path
from gbfs.network import Network as GbfsNetwork
from gbfs.reader import FilesReader as GbfsFiles
from gtfs.network import Network as GtfsNetwork
from gtfs.reader import FilesReader as GtfsFiles
from gtfs_flex.network import Network as GtfsFlexNetwork
from gtfs_flex.reader import FilesReader as GtfsFlexFiles
from maassim.network import Network as MaaSSimNetwork
from maassim.reader import FilesReader as MaaSSimFiles
from jschema import query, response
from route_planner import Planner, DirectPathPlanner

logger = logging.getLogger(__name__)
app = fastapi.FastAPI(
    title="planner",
    description="provide itinerary plans for various services",
    # version="0.1.0",
    # docs_url="/docs"
    # redoc_url="/redoc",
)


@app.on_event("startup")
def startup():
    class MultilineLogFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            message = super().format(record)
            return message.replace("\n", "\t\n")  # indicate continuation line by trailing tab

    formatter = MultilineLogFormatter(env.log_format)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logging.basicConfig(level=env.log_level, handlers=[handler])

    # replace logging formatter for uvicorn
    for handler in logging.getLogger("uvicorn").handlers:
        handler.setFormatter(formatter)

    logger.debug("configuration: %s", env.json())


@app.exception_handler(Exception)
def exception_callback(request: fastapi.Request, exc: Exception):
    from fastapi.responses import PlainTextResponse
    # omitted traceback here, because uvicorn outputs traceback as ASGI Exception
    logger.error("failed process called at %s", request.url)
    return PlainTextResponse(str(exc), status_code=500)


file_table = httputil.FileManager(limit=env.FILE_SIZE_LIMIT)
planner: Planner | None = None


@app.post("/upload")
async def upload(upload_file: fastapi.UploadFile = fastapi.File(...)):
    try:
        file_table.put(upload_file)
    finally:
        upload_file.file.close()
    return {
        "message": f"successfully uploaded. {upload_file.filename}"
    }


@app.post("/setup", response_model=response.Message)
async def setup(settings: query.Setup):
    networks: typing.List[MobilityNetwork] = [
        WalkingNetwork("walking", walking_meters_per_minute=settings.walking_meters_per_minute)
    ]
    start_time = datetime.datetime.strptime(settings.reference_time, '%Y%m%d')
    async with aiohttp.ClientSession() as session:
        for name, setting in settings.networks.items():
            if setting.type == "gbfs":
                ref = setting.input_files[0]
                filename, data = await file_table.pop(session, filename=ref.filename, url=ref.fetch_url)
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    if any(info.is_dir() for info in archive.infolist()):
                        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                                                    detail=f"exists directory in GBFS zip file")
                    gbfs_files = GbfsFiles(archive)
                network = GbfsNetwork(
                    service=name,
                    walking_meters_per_minute=settings.walking_meters_per_minute,
                    mobility_meters_per_minute=setting.mobility_meters_per_minute
                )
                network.setup(gbfs_files.stations.values())
            elif setting.type == "gtfs":
                ref = setting.input_files[0]
                filename, data = await file_table.pop(session, filename=ref.filename, url=ref.fetch_url)
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    if any(info.is_dir() for info in archive.infolist()):
                        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                                                    detail=f"exists directory in GTFS zip file")
                    gtfs_files = GtfsFiles(archive)
                network = GtfsNetwork(
                    service=name,
                    start_time=start_time,
                    walking_meters_per_minute=settings.walking_meters_per_minute,
                    max_waiting_bus_time=setting.max_waiting_time
                )
                network.setup(gtfs_files.trips.values())
            elif setting.type == "gtfs_flex":
                ref = setting.input_files[0]
                filename, data = await file_table.pop(session, filename=ref.filename, url=ref.fetch_url)
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    if any(info.is_dir() for info in archive.infolist()):
                        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                                                    detail=f"exists directory in GTFS FLEX zip file")
                    gtfs_flex_files = GtfsFlexFiles(archive)
                network = GtfsFlexNetwork(
                    service=name,
                    start_time=start_time,
                    walking_meters_per_minute=settings.walking_meters_per_minute,
                    mobility_meters_per_minute=setting.mobility_meters_per_minute,
                    expected_waiting_time=setting.expected_waiting_time,
                )
                network.setup(gtfs_flex_files.trips.values())
            elif setting.type == "maassim":
                ref = setting.input_files[0]
                filename, data = await file_table.pop(session, filename=ref.filename, url=ref.fetch_url)
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    if any(info.is_dir() for info in archive.infolist()):
                        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                                                    detail=f"exists directory in MaaSSim zip file")
                    maassim_files = MaaSSimFiles(archive)
                network = MaaSSimNetwork(
                    service=name,
                    start_time=start_time,
                    walking_meters_per_minute=settings.walking_meters_per_minute,
                    mobility_meters_per_minute=setting.mobility_meters_per_minute,
                    expected_waiting_time=setting.expected_waiting_time,
                    start_window=setting.start_window,
                    end_window=setting.end_window,
                )
                network.setup(maassim_files.G, maassim_files.params)
            else:
                raise NotImplementedError(f"{setting.type} is not implemented.")
            networks.append(network)

    global planner
    planner = DirectPathPlanner(networks)

    return {
        "message": "successfully configured."
    }


@app.post("/matrix", response_model=response.DistanceMatrix)
async def meters_for_all_stops_combinations(stops: list[query.LocationSetting]):
    return planner.meters_for_all_stops_combinations([
        Location(e.locationId, e.lat, e.lng) for e in stops
    ])


@app.post("/plan", response_model=list[Path])
async def plan(org: query.LocationSetting, dst: query.LocationSetting, dept: float):
    return planner.plan(
        org=Location(id_=org.locationId, lat=org.lat, lng=org.lng),
        dst=Location(id_=dst.locationId, lat=dst.lat, lng=dst.lng),
        dept=dept
    )
