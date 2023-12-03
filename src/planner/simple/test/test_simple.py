# SPDX-FileCopyrightText: 2023 TOYOTA MOTOR CORPORATION and MaaS Blender Contributors
# SPDX-License-Identifier: Apache-2.0
import unittest


class OtpTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_foolproof(self):
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
