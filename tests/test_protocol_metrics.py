# Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
# SPDX-License-Identifier: GPL-3.0-only
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import closing
import app


def peer(identity=1, connected=900, received=100, sent=200):
    return {'id':identity,'conntime':connected,'addr':'192.0.2.123:8333',
            'bytesrecv_per_msg':{'block':received,'inv':20,'mystery':5},
            'bytessent_per_msg':{'tx':sent,'headers':10}}


def state(timestamp, uptime, peers):
    return {'timestamp':timestamp,'uptime':uptime,'peer_count':len(peers),
            'peers':app.message_peer_counters(peers)}


class MessageTrafficTests(unittest.TestCase):
    def test_stable_connections_count_each_group_without_disclosing_identity(self):
        before=state(1000,100,[peer()])
        current=state(1060,160,[peer(received=220,sent=380),peer(2,1040)])
        row=app.message_traffic_delta(before,current)
        self.assertEqual(row['blocks_received'],120)
        self.assertEqual(row['transactions_sent'],180)
        self.assertEqual(row['announcements_received'],0)
        self.assertEqual(row['matched_peers'],1)
        self.assertEqual(row['skipped_peers'],1)
        self.assertEqual(row['seconds'],60)
        self.assertNotIn('192.0.2.123',json.dumps(row))
        self.assertNotIn('peers',row)

    def test_gaps_uptime_resets_and_clock_reversal_are_unknown(self):
        before=state(1000,100,[peer()])
        for current in (state(1060,10,[peer()]),state(1400,500,[peer()]),
                        state(990,160,[peer()]),state(1060,180,[peer()])):
            with self.subTest(current=current):
                row=app.message_traffic_delta(before,current)
                self.assertEqual(row['seconds'],0)
                self.assertIsNone(row['blocks_received'])

    def test_counter_resets_reconnected_ids_and_departures_are_not_summed(self):
        before=state(1000,100,[peer(),peer(2)])
        for peers in ([peer(received=1)], [peer(1,1040,10000,10000)], []):
            row=app.message_traffic_delta(before,state(1060,160,peers))
            self.assertEqual(row['matched_peers'],0)
            self.assertIsNone(row['blocks_received'])

    def test_missing_zero_and_invalid_counters_are_distinct(self):
        before=state(1000,100,[peer(received=0,sent=0)])
        zero=app.message_traffic_delta(before,state(1060,160,[peer(received=0,sent=0)]))
        self.assertEqual(zero['blocks_received'],0)
        self.assertEqual(app.message_peer_counters([{'id':1,'conntime':900}]),{})
        for value in (-1,True,float('nan'),'100'):
            malformed=peer();malformed['bytesrecv_per_msg']['block']=value
            self.assertEqual(app.message_peer_counters([malformed]),{})
        self.assertIsNone(app.message_traffic_delta(None,before)['blocks_received'])


class ProtocolDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.database=patch.object(app,'DATABASE_PATH',str(Path(self.directory.name)/'metrics.sqlite'))
        self.database.start()
        app._protocol_cache.clear()
        app.init_database()

    def tearDown(self):
        self.database.stop()
        self.directory.cleanup()

    def test_migration_preserves_old_block_rows_and_is_repeatable(self):
        with closing(app.database_connection()) as connection, connection:
            connection.execute('DROP TABLE block_observations')
            connection.execute('CREATE TABLE block_observations(height INTEGER PRIMARY KEY,observed_at INTEGER,block_time INTEGER,transactions INTEGER,total_size INTEGER,total_fee_btc REAL,transaction_rate REAL,source TEXT)')
            connection.execute("INSERT INTO block_observations(height,observed_at,source) VALUES (1,1000,'snapshot')")
        app.init_database()
        with closing(app.database_connection()) as connection:
            row=connection.execute('SELECT * FROM block_observations').fetchone()
        self.assertEqual(row['height'],1)
        self.assertIsNone(row['block_weight'])
        self.assertIsNone(row['fee_p50'])

    def store(self,timestamp,beginning,seconds,value):
        columns=('sampled_at','beginning','seconds','matched_peers','skipped_peers',*app.MESSAGE_COLUMNS)
        values=(timestamp,beginning,seconds,1,0,*([value]*10))
        with closing(app.database_connection()) as connection,connection:
            connection.execute(f"INSERT INTO message_traffic_samples({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",values)

    def test_historical_rates_are_time_weighted_and_boundaries_excluded(self):
        self.store(1100,1040,60,120)
        self.store(1220,1100,120,120)
        self.store(1250,1250,0,None)
        self.store(1260,1220,40,400)  # future: exclude
        self.store(1000,-3000,60,999999)  # crosses selected boundary
        with patch.object(app.time,'time',return_value=1250):
            result=app.protocol_history('1h')
        self.assertEqual(result['message_totals']['blocks_received'],240)
        self.assertEqual(result['message_totals']['measured_seconds'],180)
        self.assertEqual(result['message_points'][0]['blocks_received'],2)
        self.assertTrue(any(row['blocks_received'] is None for row in result['message_points']))

    def test_bucket_rates_weight_elapsed_time_instead_of_averaging_rates(self):
        self.store(1010,1000,10,100)
        self.store(1040,1010,30,60)
        with patch.object(app.time,'time',return_value=1050):
            result=app.protocol_history('24h')
        self.assertEqual(result['message_points'][0]['blocks_received'],4)

    def test_block_percentiles_use_last_block_in_bucket_not_an_average(self):
        with closing(app.database_connection()) as connection,connection:
            for height,at,median,weight in ((10,1001,2,2_000_000),(11,1010,20,4_000_000)):
                connection.execute("INSERT INTO block_observations(height,observed_at,block_time,source,fee_p50,block_weight) VALUES (?,?,?,'snapshot',?,?)",(height,at,at,median,weight))
        with patch.object(app.time,'time',return_value=1100):
            result=app.protocol_history('1h')
        self.assertEqual(len(result['block_points']),1)
        self.assertEqual(result['block_points'][0]['fee_p50'],20)
        self.assertEqual(result['block_points'][0]['fullness_percent'],100)

    def test_empty_history_stays_unknown_and_endpoint_needs_no_rpc(self):
        with patch.object(app,'bitcoin_cli',side_effect=AssertionError('RPC must not run')):
            result=app.protocol_history('invalid')
        self.assertEqual(result['range'],'24h')
        self.assertEqual(result['message_points'],[])
        self.assertIsNone(result['message_totals']['blocks_received'])

    def test_sampler_persists_only_aggregates_and_retains_continuous_intervals(self):
        with patch.object(app,'_message_baseline',None),patch.object(app.time,'time',side_effect=[1000,1060]),patch.object(app,'safe_call',side_effect=[[peer()],100,[peer(received=220)],160]):
            app.sample_message_traffic();app.sample_message_traffic()
        with closing(app.database_connection()) as connection:
            rows=connection.execute('SELECT * FROM message_traffic_samples ORDER BY sampled_at').fetchall()
        self.assertEqual(rows[1]['blocks_received'],120)
        self.assertIsNone(rows[0]['blocks_received'])
        self.assertNotIn('192.0.2.123',json.dumps([dict(row) for row in rows]))


class BlockVisualTests(unittest.TestCase):
    def test_exact_weight_includes_coinbase_and_fees_remain_weighted_percentiles(self):
        stats={'blockhash':'a'*64,'total_weight':3_999_000,'feerate_percentiles':[1,2,3,4,5]}
        with patch.object(app,'safe_call',return_value={'weight':4_000_000}) as rpc:
            metrics=app.block_visual_metrics(stats)
        self.assertEqual(metrics,(4_000_000,1,2,3,4,5))
        rpc.assert_called_once_with('getblock','a'*64,'1')

    def test_pruned_missing_or_malformed_data_never_invents_values(self):
        for values in (None,[1,2],[5,4,3,2,1],[1,2,3,4,float('inf')]):
            with patch.object(app,'safe_call',return_value=None):
                self.assertEqual(app.block_visual_metrics({'blockhash':'a'*64,'feerate_percentiles':values}),(None,)*6)
