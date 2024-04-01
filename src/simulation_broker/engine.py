# SPDX-FileCopyrightText: 2022 TOYOTA MOTOR CORPORATION and MaaS Blender Contributors
# SPDX-License-Identifier: Apache-2.0
import asyncio
import logging
import typing

from jschema.event import Event

from mblib.io.result import ResultWriter
from mblib.jschema.spec import SpecificationResponse
from validation import EventValidator

logger = logging.getLogger(__name__)




class Runner:
    def __init__(self, name: str):
        self.name = name

    async def spec(self) -> SpecificationResponse:
        raise NotImplementedError()

    async def setup(self, setting: typing.Mapping) -> None:
        pass

    async def start(self) -> None:
        pass

    async def peek(self) -> int | float:
        raise NotImplementedError()

    async def step(self) -> tuple[int | float, list[Event]]:
        raise NotImplementedError()

    async def triggered(self, event: Event) -> None:
        raise NotImplementedError()

    async def finish(self) -> None:
        pass

    async def reservable(self, org: str, dst: str) -> bool:
        pass


class RunnerEngine:
    def __init__(self, writer: ResultWriter):
        self._writer = writer
        self.validator: EventValidator = None
        self._runners: dict[str, Runner] = {}

    @property
    def runners(self):
        yield from self._runners.values()

    async def setup_runners(self, runners: typing.Mapping[str, Runner]):
        for name, runner in runners.items():
            spec = await runner.spec()
            self.validator.specs[name] = spec
            self._runners[name] = runner

        logger.debug("validator: %s", self.validator)
        self.validator.check_versions()
        self.validator.check_schemas()
        self.validator.check_features()

    async def start(self):
        for runner in self.runners:
            await runner.start()

    async def peek(self):
        return min(await asyncio.gather(*[runner.peek() for runner in self.runners]))

    async def step(self, until: int | float = None) -> int | float:
        peeks = await asyncio.gather(*[runner.peek() for runner in self.runners])

        # step the simulator with the lowest peek() value
        runner, min_peek = min(zip(self.runners, peeks), key=lambda e: e[1])
        # If the next event is after the value of until, returns the scheduled time of it
        if until and min_peek > until:
            return min_peek

        now, events = await runner.step()

        for event in events:
            self.validator.check_event_on_step_response(runner.name, event)
            event.source = runner.name
            await self._writer.write_json(event.model_dump(exclude_none=True))

            # sync triggered events with the other runners
            if service := event.service:
                self.validator.check_event_on_triggered_request(service, event)
                await self._runners[service].triggered(event)
            else:
                for each in self.runners:
                    self.validator.check_event_on_triggered_request(each.name, event)
                    await each.triggered(event)
        return now

    async def finish(self):
        for runner in self.runners:
            try:
                await runner.finish()
            except:
                logger.info("error on %s", runner)
                raise

    async def reservable(self, service: str, org: str, dst: str):
        if runner := self._runners.get(service, None):
            try:
                return await runner.reservable(org, dst)
            except:
                logger.info("error on %s", runner)
                raise
        else:
            msg = f"service: {service} was not found. (services: {list(self._runners.keys())})"
            raise KeyError(msg)
