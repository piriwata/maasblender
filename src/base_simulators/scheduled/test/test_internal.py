# SPDX-FileCopyrightText: 2023 TOYOTA MOTOR CORPORATION and MaaS Blender Contributors
# SPDX-License-Identifier: Apache-2.0
import unittest
import logging
from datetime import datetime, date, time, timedelta

from simulation import Simulation
from core import EventType, Stop, StopTime, Service, Trip

logger = logging.getLogger(__name__)


def run(simulation: Simulation, until: float):
    events = []
    while simulation.peek() < until:
        _ = simulation.step()
        events.extend(simulation.event_queue.events)
    # expect nothing to happen. just let time forward.
    if simulation.env.now < until:
        simulation.env.run(until=until)
    return events


# 以下の地名、座標などは以下の著作物を改変して利用しています。
# まいどはやバスGTFS-JP、富山市、クリエイティブ・コモンズ・ライセンス　表示4.0国際
# （http://creativecommons.org/licenses/by/4.0/deed.ja）
gtfs_stations = {
    "3_1":  Stop("3_1", "3_1", lat=36.695557, lng=137.220786),
    "7_1":  Stop("7_1", "7_1", lat=36.696726, lng=137.227181),
    "11_1": Stop("11_1", "11_1", lat=36.690094, lng=137.231366),
    "15_1": Stop("15_1", "15_1", lat=36.685561, lng=137.225999),
    "19_1": Stop("19_1", "19_1", lat=36.692095, lng=137.220579),
    "23_0": Stop("23_0", "23_0", lat=36.688812, lng=137.213258),
    "27_1": Stop("27_1", "27_1", lat=36.683816, lng=137.207189),
    "31_1": Stop("31_1", "31_1", lat=36.69018, lng=137.203424),
    "35_1": Stop("35_1", "35_1", lat=36.702725, lng=137.207239),
}


class SimpleTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.stops = gtfs_stations
        self.mobility_id = "mobility"

        self.simulation = Simulation(
            start_time=datetime.combine(date.today(), time()),
            capacity=20,
            trips={
                self.mobility_id: Trip(
                    route=...,
                    service=Service(
                        start_date=date.today(),
                        end_date=date.today() + timedelta(days=1),
                        monday=True, tuesday=True, wednesday=True, thursday=True, friday=True,
                        saturday=True, sunday=True
                    ),
                    stop_times=[
                        StopTime(
                            stop=self.stops[each[0]],
                            departure=timedelta(minutes=each[1])
                        )
                        for each in [
                            ("3_1", 543),
                            ("7_1", 548),
                            ("11_1", 558),
                            ("15_1", 562),
                            ("19_1", 566),
                            ("23_0", 574),
                            ("27_1", 578),
                            ("31_1", 583),
                            ("35_1", 590),
                        ]
                    ]
                )
            }
        )
        self.simulation.start()

    def test_operation(self):
        triggered_events = run(self.simulation, until=549)
        expected_events = [
            {
                'eventType': EventType.ARRIVED,
                'time': 543.0,
                'details': {
                    'userId': None,
                    'mobilityId': self.mobility_id,
                    'location': {
                        "locationId": self.stops["3_1"].stop_id,
                        "lat": self.stops["3_1"].lat,
                        "lng": self.stops["3_1"].lng
                    },
                }
            }, {
                'eventType': EventType.DEPARTED,
                'time': 543.0,
                'details': {
                    'userId': None,
                    'mobilityId': self.mobility_id,
                    'location': {
                        "locationId": self.stops["3_1"].stop_id,
                        "lat": self.stops["3_1"].lat,
                        "lng": self.stops["3_1"].lng
                    },
                }
            }, {
                'eventType': EventType.ARRIVED,
                'time': 548.0,
                'details': {
                    'userId': None,
                    'mobilityId': self.mobility_id,
                    'location': {
                        "locationId": self.stops["7_1"].stop_id,
                        "lat": self.stops["7_1"].lat,
                        "lng": self.stops["7_1"].lng
                    },
                }
            }, {
                'eventType': EventType.DEPARTED,
                'time': 548.0,
                'details': {
                    'userId': None,
                    'mobilityId': self.mobility_id,
                    'location': {
                        "locationId": self.stops["7_1"].stop_id,
                        "lat": self.stops["7_1"].lat,
                        "lng": self.stops["7_1"].lng
                    },
                }
            },
        ]
        self.assertEqual(expected_events, triggered_events)

    def test_a_user_flow(self):
        user = {
            "user_id": "U_001",
            "org": "3_1",
            "dst": "23_0",
            "dept": 490,
        }

        run(self.simulation, until=user["dept"])

        self.simulation.reserve_user(
            user_id=user["user_id"],
            org=user["org"],
            dst=user["dst"],
            dept=user["dept"],
        )
        triggered_events = run(self.simulation, until=user["dept"] + 1)

        expected_events = [
            {
                'eventType': EventType.RESERVED,
                'time': user["dept"],
                'details': {
                    'success': True,
                    'userId':  user["user_id"],
                    'mobilityId': self.mobility_id,
                    'route': [{
                        'org': {
                            "locationId": self.stops[user["org"]].stop_id,
                            "lat": self.stops[user["org"]].lat,
                            "lng": self.stops[user["org"]].lng
                        },
                        'dst': {
                            "locationId": self.stops[user["dst"]].stop_id,
                            "lat": self.stops[user["dst"]].lat,
                            "lng": self.stops[user["dst"]].lng
                        },
                        'dept': 543.0,
                        'arrv': 574.0
                    }]
                }
            }
        ]
        self.assertEqual(expected_events, triggered_events)

        self.simulation.dept_user(
            user_id=user["user_id"],
        )

        triggered_events = run(self.simulation, until=574.1)
        triggered_events = [
            event
            for event in triggered_events
            if event["details"]["userId"]
        ]

        expected_events = [
            {
                'eventType': EventType.DEPARTED,
                'time': 543.0,
                'details': {
                    'userId': user["user_id"],
                    'mobilityId': self.mobility_id,
                    'location': {
                        "locationId": self.stops[user["org"]].stop_id,
                        "lat": self.stops[user["org"]].lat,
                        "lng": self.stops[user["org"]].lng
                    },
                }
            }, {
                'eventType': EventType.ARRIVED,
                'time': 574.0,
                'details': {
                    'userId': user["user_id"],
                    'mobilityId': self.mobility_id,
                    'location': {
                        "locationId": self.stops[user["dst"]].stop_id,
                        "lat": self.stops[user["dst"]].lat,
                        "lng": self.stops[user["dst"]].lng
                    },
                }
            },
        ]
        self.assertEqual(expected_events, triggered_events)


if __name__ == '__main__':
    unittest.main()
