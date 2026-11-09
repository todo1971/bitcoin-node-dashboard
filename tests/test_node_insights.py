# Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
# SPDX-License-Identifier: GPL-3.0-only
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing
from datetime import datetime
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

    def test_daily_totals_and_peaks_use_valid_intervals_in_local_days(self):
        # Berlin clocks fell back on October 25, making this a 25-hour day.
        start = int(datetime.fromisoformat('2026-10-25T00:00:00+02:00').timestamp())
        self.samples([(start-30,0,0,70), (start+30,60,60,130),
                      (start+60,90,3060,160), (start+150,180,3960,250),
                      (start+210,10,10,15), (start+270,70,70,75)])
        with closing(app.database_connection()) as connection, connection:
            connection.execute('UPDATE node_samples SET connections = CASE WHEN sampled_at <= ? THEN 70 ELSE 110 END',
                               (start + 60,))
        with patch.object(app.time, 'time', return_value=start+26*3600):
            result = app.traffic_history('7d', 'Europe/Berlin')
            utc = app.traffic_history('7d')
        today, previous_day = result['daily'][:2]
        self.assertEqual(today['window_seconds'], 3600)
        self.assertIsNone(today['sent_bytes'])
        self.assertEqual(previous_day['day_start'], start)
        self.assertEqual(previous_day['window_seconds'], 25*3600)
        self.assertEqual(previous_day['measured_seconds'], 180)
        self.assertEqual(previous_day['sent_bytes'], 3960)
        self.assertAlmostEqual(previous_day['mean_connections'], 280/3)
        self.assertEqual(previous_day['peak_sent_bytes_per_second'], 100)
        self.assertEqual(result['points'][-1]['peak_sent_bytes_per_second'], 100)
        self.assertIsNone(result['points'][-1]['sent_bytes_per_second'])
        self.assertNotEqual(utc['daily'][1]['day_start'], start)

    def test_live_rates_accept_normal_background_sample_interval(self):
        with patch.object(app, '_traffic_live_previous', None):
            self.assertFalse(app.live_traffic(1000, {'totalbytesrecv':100,'totalbytessent':200}, 100)['available'])
            rate = app.live_traffic(1060, {'totalbytesrecv':220,'totalbytessent':440}, 160)
        self.assertTrue(rate['available'])
        self.assertEqual(rate['received_bytes_per_second'], 2)

    def test_week_comparison_uses_complete_local_days_and_requires_coverage(self):
        day = int(datetime.fromisoformat('2026-11-07T00:00:00+01:00').timestamp())
        beginning, boundary = day - 14*86400, day - 7*86400
        samples, sent = [], 0
        for timestamp in range(beginning, day + 3601, 3600):
            if timestamp > beginning:
                sent += 3600 if timestamp <= boundary else 7200
            samples.append((timestamp, timestamp-beginning, sent, timestamp-beginning+100))
        self.samples(samples)
        with patch.object(app, 'SAMPLE_INTERVAL_SECONDS', 3600), patch.object(app.time, 'time', return_value=day+3600):
            result = app.traffic_history('24h', 'Europe/Berlin')['weekly']
        self.assertEqual(result['current']['sent_bytes'], 2*7*86400)
        self.assertEqual(result['previous']['sent_bytes'], 7*86400)
        self.assertEqual(result['current']['mean_daily_sent_bytes'], 2*86400)
        self.assertEqual(result['upload_change_percent'], 100)
        with closing(app.database_connection()) as connection, connection:
            connection.execute('DELETE FROM node_samples WHERE sampled_at > ? AND sampled_at < ?',
                               (boundary+86400, boundary+3*86400))
        with patch.object(app, 'SAMPLE_INTERVAL_SECONDS', 3600), patch.object(app.time, 'time', return_value=day+3631):
            self.assertIsNone(app.traffic_history('24h', 'Europe/Berlin')['weekly']['upload_change_percent'])

    def test_network_history_preserves_unknown_legacy_samples_and_stores_directions(self):
        self.samples([(1000,1,2,10)])
        app.store_snapshot({'generated_at':1060, 'chain':{'blocks':1},
                            'network':{'network_directions':{'ipv4':{'inbound':3,'outbound':2},
                                                           'ipv6':{'inbound':0,'outbound':1},
                                                           'onion':{'inbound':4,'outbound':0}}}})
        with patch.object(app.time, 'time', return_value=1120):
            points = app.traffic_history('1h')['network_points']
        self.assertIsNone(points[0]['ipv4_in'])
        self.assertEqual([points[-1][key] for key in ('ipv4_in','ipv4_out','ipv6_in','ipv6_out','onion_in','onion_out')],
                         [3,2,0,1,4,0])
        self.assertNotIn('addr', json.dumps(points))

    def test_network_column_migration_preserves_existing_history(self):
        self.samples([(1000,10,20,100)])
        with closing(app.database_connection()) as connection, connection:
            for network in ('ipv4', 'ipv6', 'onion'):
                for direction in ('in', 'out'):
                    connection.execute(f'ALTER TABLE node_samples DROP COLUMN {network}_{direction}')
        app.init_database()
        app.init_database()
        with closing(app.database_connection()) as connection:
            row = connection.execute('SELECT bytes_sent, ipv4_in, onion_out FROM node_samples').fetchone()
        self.assertEqual(tuple(row), (20,None,None))

    def test_daily_blocks_are_unique_and_incomplete_metrics_stay_unknown(self):
        start = int(datetime.fromisoformat('2026-11-07T00:00:00+01:00').timestamp())
        with closing(app.database_connection()) as connection, connection:
            connection.executemany("""INSERT INTO block_observations
                (height,observed_at,block_time,transactions,total_size,total_fee_btc,source)
                VALUES (?, ?, ?, ?, ?, ?, 'test')""", [
                    (1,start,start,100,1000000,0.1), (2,start,start+30,200,2000000,None),
                    (3,start,start-1,300,3000000,0.3), (4,start,start+4000,500,4000000,0.5)])
        with patch.object(app.time, 'time', return_value=start+3600):
            day = app.traffic_history('1h', 'Europe/Berlin')['daily'][0]
        self.assertEqual(day['blocks']['recorded_blocks'], 2)
        self.assertEqual(day['blocks']['transactions'], 300)
        self.assertEqual(day['blocks']['mean_block_size'], 1500000)
        self.assertIsNone(day['blocks']['total_fee_btc'])

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
                for path, key in (('/api/traffic?range=invalid', 'periods'), ('/api/recent-blocks', 'blocks'), ('/api/protocol-history?range=invalid','message_points')):
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
