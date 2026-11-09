# Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
# SPDX-License-Identifier: GPL-3.0-only
import json
import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from unittest.mock import patch
import app


class AddressCountsTests(unittest.TestCase):
    def test_all_networks_is_not_counted_twice(self):
        raw={'ipv4':{'new':10,'tried':2,'total':12},'all_networks':{'new':10,'tried':2,'total':12}}
        self.assertEqual(app.address_manager_counts(raw),raw['all_networks'])
        self.assertEqual(app.address_manager_counts({'ipv4':raw['ipv4']}),raw['all_networks'])
        self.assertEqual(app.address_manager_counts(raw['all_networks']),raw['all_networks'])

    def test_network_fallback_sums_only_complete_known_networks(self):
        result=app.address_manager_counts({'ipv4':{'new':10,'tried':2,'total':12},'onion':{'new':5,'tried':1,'total':6}})
        self.assertEqual(result,{'new':15,'tried':3,'total':18})
        self.assertIsNone(app.address_manager_counts({'192.0.2.1':{'new':1,'tried':0,'total':1}}))
        self.assertIsNone(app.address_manager_counts({'ipv4':{'new':10,'tried':2}}))

    def test_invalid_missing_and_zero_counts_are_distinct(self):
        self.assertEqual(app.address_manager_counts({'new':0,'tried':0,'total':0}),{'new':0,'tried':0,'total':0})
        for raw in (None,{},[],{'new':1,'tried':2,'total':4},
                    {'new':True,'tried':0,'total':1},{'new':-1,'tried':2,'total':1},
                    {'new':1.5,'tried':0,'total':1.5},{'all_networks':None,'ipv4':{'new':1,'tried':0,'total':1}}):
            with self.subTest(raw=raw):
                self.assertIsNone(app.address_manager_counts(raw))


class AddressHistoryTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.database=patch.object(app,'DATABASE_PATH',str(Path(self.directory.name)/'addresses.sqlite'))
        self.database.start();app._protocol_cache.clear();app.init_database()

    def tearDown(self):
        self.database.stop();self.directory.cleanup()

    def test_samples_preserve_nulls_connections_and_do_not_store_addresses(self):
        with patch.object(app.time,'time',return_value=1000),patch.object(app,'safe_call',side_effect=[None,{'connections':4}]):
            app.sample_address_manager()
        with patch.object(app.time,'time',return_value=1060),patch.object(app,'safe_call',side_effect=[{'new':0,'tried':0,'total':0},{'connections':0}]):
            app.sample_address_manager()
        with closing(app.database_connection()) as connection:
            rows=[dict(row) for row in connection.execute('SELECT * FROM address_manager_samples ORDER BY sampled_at')]
        self.assertIsNone(rows[0]['total']);self.assertEqual(rows[0]['connections'],4)
        self.assertEqual(rows[1]['total'],0);self.assertEqual(rows[1]['connections'],0)
        self.assertEqual(set(rows[0]),{'sampled_at','new','tried','total','connections'})

    def test_history_does_not_average_away_failures_or_include_future_rows(self):
        with closing(app.database_connection()) as connection,connection:
            connection.executemany('INSERT INTO address_manager_samples VALUES (?,?,?,?,?)',[
                (1000,10,2,12,2),(1010,None,None,None,4),(2000,999,999,1998,999)])
        with patch.object(app.time,'time',return_value=1100):
            result=app.protocol_history('1h')
        self.assertIsNone(result['address_points'][0]['new'])
        self.assertEqual(result['address_points'][0]['connections'],3)
        self.assertEqual(result['address_latest']['sampled_at'],1010)
        self.assertFalse(result['address_latest']['stale'])

    def test_stale_counts_remain_explicit_and_new_table_is_idempotent(self):
        with closing(app.database_connection()) as connection,connection:
            connection.execute('INSERT INTO address_manager_samples VALUES (1000,10,2,12,4)')
        app.init_database()
        with patch.object(app.time,'time',return_value=1400),patch.object(app,'bitcoin_cli',side_effect=AssertionError('No public RPC')):
            result=app.protocol_history('1h')
        self.assertTrue(result['address_latest']['stale'])
        self.assertEqual(result['address_latest']['total'],12)

    def test_retention_and_empty_history_do_not_invent_nodes(self):
        now=2000000000
        with closing(app.database_connection()) as connection,connection:
            connection.execute('INSERT INTO address_manager_samples VALUES (1,10,2,12,4)')
        with patch.object(app.time,'time',return_value=now),patch.object(app,'safe_call',side_effect=[None,None]):
            app.sample_address_manager()
        with patch.object(app.time,'time',return_value=now):
            result=app.protocol_history('1h')
        self.assertIsNone(result['address_latest']['total'])
        self.assertIsNone(result['address_latest']['connections'])
        with closing(app.database_connection()) as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM address_manager_samples').fetchone()[0],1)
