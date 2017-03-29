#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2017 Red Hat
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from unittest import TestCase

from mock import patch, Mock

from ochlero import ochlero


class TestPredefinedTypeMapper(TestCase):
    def test_mapper(self):
        """Test mapping of predefined types"""
        sample = "aaa"
        self.assertEqual(sample, ochlero.map_predefined_types(sample))
        sample = "_INT_"
        self.assertEqual("[0-9]+",
                         ochlero.map_predefined_types(sample))
        sample = "aaa _INT_"
        self.assertEqual("aaa [0-9]+",
                         ochlero.map_predefined_types(sample))
        sample = "aaa _INT_ bbb _ALPHANUMERIC_ ccc _INT_"
        self.assertEqual("aaa [0-9]+ bbb \w+ ccc [0-9]+",
                         ochlero.map_predefined_types(sample))


class TestPredefinedMacroMapper(TestCase):
    def test_mapper(self):
        """Test mapping of predefined macros"""
        sample = "aaa"
        self.assertEqual(sample, ochlero.map_predefined_macros(sample))
        sample = "aaa _EPOCH_"
        with patch("time.time") as t:
            t.return_value = 123456
            self.assertEqual("aaa 123456",
                             ochlero.map_predefined_macros(sample))


class TestEvent(TestCase):
    def test_pattern_no_substitutes(self):
        """Test a pattern without substitution"""
        event = ochlero.Event('testEvent', 'abcd', {}, 'dcba')
        self.assertEqual('^abcd$', event.precompiled_pattern)
        self.assertEqual({'XXX': 'YYY'}, event.prescan('abcd'))
        self.assertEqual('dcba', event.scan('abcd'))
        self.assertEqual(None, event.scan('trolololo'))

    def test_pattern_with_substitutes(self):
        """Test a pattern with simple substitution"""
        event = ochlero.Event('testEvent', 'abcd ${a} ${b} dcba',
                              {'a': 'aaa', 'b': 'bbb'}, 'hello ${b} ${a}')
        self.assertEqual('^abcd (?P<a>aaa) (?P<b>bbb) dcba$',
                         event.precompiled_pattern)
        self.assertEqual(None, event.prescan('abcd'))
        self.assertEqual({'a': 'aaa', 'b': 'bbb'},
                         event.prescan('abcd aaa bbb dcba'))
        self.assertEqual('hello bbb aaa',
                         event.scan('abcd aaa bbb dcba'))
        self.assertEqual(None, event.scan('trolololo'))

    def test_pattern_with_predefined_substitutes(self):
        """Test a pattern using predefined substitutions"""
        event = ochlero.Event('testEvent', 'abcd ${a} ${b} dcba',
                              {'a': '_INT_', 'b': '_ALPHANUMERIC_'},
                              'hello ${b} ${a}')
        self.assertEqual('^abcd (?P<a>[0-9]+) (?P<b>\w+) dcba$',
                         event.precompiled_pattern)
        self.assertEqual(None, event.prescan('abcd'))
        self.assertEqual({'a': '42', 'b': 'ROFLCOPTER'},
                         event.prescan('abcd 42 ROFLCOPTER dcba'))
        self.assertEqual('hello ROFLCOPTER 42',
                         event.scan('abcd 42 ROFLCOPTER dcba'))
        self.assertEqual(None, event.scan('trolololo'))


class TestWatcher(TestCase):
    def test_watcher(self):
        """Test watchers scanning journal events"""
        mockPublisher = Mock()
        events = [ochlero.Event('testEvent', 'abcd', {}, 'dcba'), ]
        watcher = ochlero.Watcher('test_unit', None,
                                  'test_topic', mockPublisher, events)
        # TODO get a real entry dict
        j_entry = {'MESSAGE': 'abcd', }
        watcher.watch(j_entry)
        self.assertTrue(not mockPublisher.publish.called)
        j_entry['_SYSTEMD_UNIT'] = 'test_unit'
        watcher.watch(j_entry)
        mockPublisher.publish.assert_called_with('test_topic', 'dcba')
        j_entry['_SYSTEMD_UNIT'] = None
        j_entry['_COMM'] = 'test_comm'
        watcher = ochlero.Watcher(None, 'test_comm',
                                  'test_topic', mockPublisher, events)
        watcher.watch(j_entry)
        mockPublisher.publish.assert_called_with('test_topic', 'dcba')
        j_entry['_COMM'] = None
        j_entry['SYSLOG_IDENTIFIER'] = 'test_comm'
        watcher.watch(j_entry)
        mockPublisher.publish.assert_called_with('test_topic', 'dcba')
