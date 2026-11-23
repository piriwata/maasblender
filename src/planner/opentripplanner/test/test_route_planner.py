# SPDX-FileCopyrightText: 2026 TOYOTA MOTOR CORPORATION and MaaS Blender Contributors
# SPDX-License-Identifier: Apache-2.0
import datetime
import unittest
from unittest.mock import AsyncMock

from core import Location
from route_planner import OpenTripPlanner


class RoutePlannerTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.base = datetime.datetime(2024, 2, 1, tzinfo=datetime.UTC)
        self.planner = OpenTripPlanner("http://otp", self.base, 80, None, {})
        self.planner.client = AsyncMock()
        self.org = Location("origin", 36.7, 137.2)
        self.dst = Location("destination", 36.8, 137.3)

    def test_default_modes(self):
        walk_transit, direct_flex, access_egress_flex = self.planner.transport_modes
        self.assertEqual(walk_transit["direct"], ["WALK"])
        self.assertNotIn("transit", walk_transit["transit"])
        self.assertEqual(direct_flex["direct"], ["WALK", "FLEX"])
        self.assertTrue(direct_flex["directOnly"])
        self.assertEqual(access_egress_flex["transit"]["access"], ["WALK", "FLEX"])
        self.assertEqual(access_egress_flex["transit"]["egress"], ["WALK", "FLEX"])

    async def test_empty_results_keep_straight_walking_fallback(self):
        self.planner.client.execute_async.return_value = {
            "planConnection": {"edges": []}
        }
        paths = await self.planner.plan(self.org, self.dst, dept=10, arrv=20)
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0].arrv, 20)
        self.assertEqual(paths[0].trips[0].service, "walking")
