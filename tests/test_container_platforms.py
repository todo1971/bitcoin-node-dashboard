# Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
# SPDX-License-Identifier: GPL-3.0-only
import io
import json
import unittest
from unittest.mock import patch

from tools import check_container_platforms as checker


class ContainerPlatformsTests(unittest.TestCase):
    @staticmethod
    def response(payload):
        response = io.BytesIO(json.dumps(payload).encode())
        response.headers = {'Docker-Content-Digest':'sha256:index'}
        return response

    def inspect(self, platforms):
        payload = {'manifests':[{'platform':platform, 'digest':'sha256:platform'} for platform in platforms]}
        with patch.object(checker.urllib.request, 'urlopen', side_effect=[
            self.response({'token':'anonymous-pull-secret'}), self.response(payload)
        ]):
            return checker.inspect_image('bitcoin/bitcoin', '31.1')

    def test_required_platforms_accept_arm_variant_and_ignore_attestations(self):
        data = self.inspect([{'os':'linux','architecture':'amd64'},
                             {'os':'linux','architecture':'arm64','variant':'v8'},
                             {'os':'unknown','architecture':'unknown'}])
        self.assertEqual(len(data['platforms']), 2)
        self.assertNotIn('anonymous-pull-secret', json.dumps(data))
        self.assertEqual(data['digest'], 'sha256:index')

    def test_single_architecture_base_is_rejected_before_build(self):
        with self.assertRaisesRegex(RuntimeError, 'lacks required architectures'):
            self.inspect([{'os':'linux','architecture':'amd64'}])

    def test_32_bit_arm_is_not_accepted_as_arm64(self):
        with self.assertRaises(RuntimeError):
            self.inspect([{'os':'linux','architecture':'amd64'},
                          {'os':'linux','architecture':'arm','variant':'v7'}])
