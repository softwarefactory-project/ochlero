from unittest import TestCase

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
