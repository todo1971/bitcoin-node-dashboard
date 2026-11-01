# Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
# SPDX-License-Identifier: GPL-3.0-only
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import app


class PeerInsightsTests(unittest.TestCase):
    def test_client_comments_addresses_and_sensitive_types_are_not_published(self):
        data = app.peer_distributions([{'subver':'/Satoshi:31.1.0(private-comment)/',
            'addr':'192.0.2.1', 'connection_type':'private-broadcast', 'services':'c08'},
            {'subver':'<script>evil</script>', 'servicesnames':['NODE_WITNESS', 'NEW_FLAG'], 'inbound':True}])
        encoded = json.dumps(data)
        for forbidden in ('private-comment', '192.0.2.1', 'private-broadcast', '<script>'):
            self.assertNotIn(forbidden, encoded)
        self.assertEqual(data['clients'][0]['name'], 'Satoshi 31.1.0')
        self.assertIn({'name':'WITNESS', 'count':2}, data['services'])
        self.assertIn({'name':'other', 'count':1}, data['connection_types'])

    def test_client_rows_are_bounded_and_counts_preserved(self):
        data = app.peer_distributions([{'subver':f'/Client:{n}.0/'} for n in range(30)])
        self.assertEqual(len(data['clients']), 12)
        self.assertEqual(data['other_clients'], 18)
        self.assertEqual(data['services_unknown'], 30)


class TrafficTests(unittest.TestCase):
    def test_rates_require_continuous_counters_and_uptime(self):
        before = dict(timestamp=1000, received=100, sent=200, uptime=20)
        after = dict(timestamp=1060, received=220, sent=440, uptime=80)
        self.assertEqual(app.traffic_delta(before, after, 180)['received_bytes_per_second'], 2)
        for changed in (dict(uptime=30), dict(received=10), dict(timestamp=1400), dict(sent=None), dict(sent='440'), dict(sent=float('nan'))):
            self.assertFalse(app.traffic_delta(before, after | changed, 180)['available'])
        self.assertFalse(app.traffic_delta(None, after, 180)['available'])
        self.assertEqual(app.traffic_delta(before, after | dict(received=100), 180)['received_bytes_per_second'], 0)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db = patch.object(app, 'DATABASE_PATH', str(Path(self.directory.name) / 'test.sqlite'))
        self.db.start()
        app.init_database()

    def tearDown(self):
        self.db.stop()
        self.directory.cleanup()

    def samples(self, values):
        with closing(app.database_connection()) as connection, connection:
            connection.executemany('INSERT INTO node_samples (sampled_at,blocks,bytes_received,bytes_sent,bitcoind_uptime) VALUES (?,1,?,?,?)', values)

    def test_history_totals_exclude_reset_gap_and_boundary_intervals(self):
        # UTC midnight 2026-11-01; first interval straddles day/month boundary.
        start = 1793491200
        self.samples([(start-30,100,200,100), (start+30,220,440,160),
                      (start+90,340,680,220), (start+150,10,20,20),
                      (start+210,130,260,80), (start+600,900,1000,470)])
        with patch.object(app.time, 'time', return_value=start+600):
            result = app.traffic_history('1h')
        self.assertEqual(result['periods']['today']['received_bytes'], 240)
        self.assertEqual(result['periods']['today']['measured_seconds'], 120)
        self.assertEqual(result['periods']['today']['gaps'], 2)
        self.assertEqual(result['periods']['selected']['received_bytes'], 360)
        self.assertTrue(any(row['received_bytes_per_second'] is None for row in result['points']))
        self.assertEqual(result['periods']['month'], result['periods']['today'])

    def test_missing_counters_are_unknown_and_future_samples_excluded(self):
        self.samples([(1000,None,10,10), (1060,100,20,70), (1120,100,20,130), (1300,999999,999999,310)])
        with patch.object(app.time, 'time', return_value=1120):
            data = app.traffic_history('invalid')
        self.assertEqual(data['range'], '24h')
        self.assertEqual(data['periods']['selected']['received_bytes'], 0)
        self.assertEqual(data['periods']['selected']['measured_seconds'], 60)

    def test_no_samples_do_not_invent_zero_totals(self):
        data = app.traffic_history('1h')
        self.assertIsNone(data['periods']['selected']['received_bytes'])
        self.assertEqual(data['points'], [])

    def test_live_rates_accept_normal_background_sample_interval(self):
        with patch.object(app, '_traffic_live_previous', None):
            self.assertFalse(app.live_traffic(1000, {'totalbytesrecv':100,'totalbytessent':200}, 100)['available'])
            rate = app.live_traffic(1060, {'totalbytesrecv':220,'totalbytessent':440}, 160)
        self.assertTrue(rate['available'])
        self.assertEqual(rate['received_bytes_per_second'], 2)

    def test_recent_blocks_are_bounded_and_do_not_make_rpc_calls(self):
        with closing(app.database_connection()) as connection, connection:
            connection.executemany('INSERT INTO block_observations (height,observed_at,source) VALUES (?,1000,?)', [(height,'sample') for height in range(30)])
        with patch.object(app, 'bitcoin_cli', side_effect=AssertionError('unexpected RPC')):
            blocks = app.recent_blocks_data()['blocks']
        self.assertEqual(len(blocks), 20)
        self.assertEqual([row['height'] for row in blocks], list(range(29,9,-1)))
        self.assertIsNone(blocks[0]['total_size'])

    def test_public_endpoints_are_read_only_and_fail_with_controlled_error(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with patch.object(app, 'bitcoin_cli', side_effect=AssertionError('unexpected RPC')):
                for path, key in (('/api/traffic?range=invalid', 'periods'), ('/api/recent-blocks', 'blocks')):
                    with urllib.request.urlopen(base + path, timeout=5) as response:
                        self.assertIn(key, json.load(response))
            with patch.object(app, 'recent_blocks_data', side_effect=RuntimeError('QA database error')):
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(base + '/api/recent-blocks', timeout=5)
                self.assertEqual(caught.exception.code, 503)
                self.assertEqual(json.load(caught.exception), {'error':'Node insights unavailable'})
                caught.exception.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
