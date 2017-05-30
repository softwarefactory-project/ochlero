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

import argparse
import logging
import os
import re
import sys

from systemd import journal as systemd_journal
import paho.mqtt.publish as mqtt_publish
import yaml

# import datetime
import time
import select


LOGGER = logging.getLogger('ochlero')
LOGGER.setLevel(logging.DEBUG)


# TODO add predefined regexps for convenience
PREDEFINED_TYPES = {
    "_SYSLOGTIMESTAMP_": "[A-Z][a-z]+\s+\d+\s\d+:\d+:\d+",
    "_IPv4_": ("(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
               "(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"),
    "_EMAIL_": "([a-z0-9_\.-]+)@([\da-z\.-]+)\.([a-z\.]{2,6})",
    "_ALPHANUMERIC_": "\w+",
    "_INT_": "[0-9]+",
    "_URL_": "(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?",
}


class MessageMacro(object):
    def __call__(self, *args, **kwargs):
        raise NotImplementedError

    def __str__(self):
        raise NotImplementedError


class UnicodeMacro(str, MessageMacro):
    def __call__(self, *args, **kwargs):
        return self


class EpochMacro(str, MessageMacro):
    def __call__(self, *args, **kwargs):
        return str(int(time.time()))

    def __str__(self):
        return self()


PREDEFINED_MACROS = {
    "_EPOCH_": EpochMacro(),
}


def _map_predefined(_map, substitute):
    mapped = substitute
    for t, r in _map.items():
        try:
            _r = r()
        except TypeError:
            _r = r
        mapped = mapped.replace(t, _r)
    return mapped


def map_predefined_types(substitute):
    return _map_predefined(PREDEFINED_TYPES, substitute)


def map_predefined_macros(msg):
    return _map_predefined(PREDEFINED_MACROS, msg)


class Publisher(object):
    def __init__(self, hostname, port, auth_dict=None):
        self.hostname = hostname
        self.port = port
        self.auth_dict = auth_dict

    def publish(self, topic, message):
        msg = map_predefined_macros(message)
        mqtt_publish.single(topic, payload=msg,
                            hostname=self.hostname, port=self.port,
                            client_id="ochlero/%i" % os.getpid(),
                            auth=self.auth_dict)
        LOGGER.debug("'''%s''' published to topic %s" % (msg, topic))


class Event(object):
    def __init__(self, name, pattern, substitutes, publish_msg):
        self.name = name
        self.original_pattern = pattern
        self.original_substitutes = substitutes
        self.substitutes = dict((u, map_predefined_types(v))
                                for u, v in substitutes.items())
        self.original_publish_msg = publish_msg
        self.build_pattern()
        self.build_publish_msg()

    def build_pattern(self):
        pattern = self.original_pattern
        for s, p in self.substitutes.items():
            named_grp = '(?P<%s>%s)' % (s, p)
            pattern = pattern.replace('${%s}' % s, named_grp)
        self.precompiled_pattern = '^%s$' % pattern
        self.pattern = re.compile(self.precompiled_pattern)

    def build_publish_msg(self):
        self.publish_msg = self.original_publish_msg
        for s in self.substitutes:
            self.publish_msg = self.publish_msg.replace('${%s}' % s,
                                                        '%%(%s)s' % s)

    def prescan(self, entry):
        match = self.pattern.match(entry)
        if match:
            if not match.groupdict():
                # arbitrary dictionary, published message is likely static
                return {'XXX': 'YYY'}
            return match.groupdict()
        return None

    def scan(self, entry):
        match = self.prescan(entry)
        if not match:
            return None
        return self.publish_msg % match


class Watcher(object):
    def __init__(self, unit, comm, topic, publisher, events):
        self.unit = unit
        self.topic = topic
        self.comm = comm
        self.publisher = publisher
        self.events = events

    def watch(self, entry):
        LOGGER.debug("Watching for unit '%s', comm '%s'" % (self.unit,
                                                            self.comm))
        if self.unit and self.unit != entry.get('_SYSTEMD_UNIT'):
            msg = "event unit '%s' did not match unit '%s'"
            LOGGER.debug(msg % (entry.get('_SYSTEMD_UNIT'), self.unit))
            return
        # command might appear as the syslog identifier
        if (self.comm and self.comm != entry.get('_COMM')) and\
           (self.comm and self.comm != entry.get('SYSLOG_IDENTIFIER')):
            msg = "event command, syslog id '%s,%s' did not match comm '%s'"
            LOGGER.debug(msg % (entry.get('_COMM'),
                                entry.get('SYSLOG_IDENTIFIER'),
                                self.comm))
            return
        LOGGER.debug("Event matches unit/command filter")
        for event in self.events:
            scan = event.scan(entry['MESSAGE'])
            if scan:
                msg = "Event '%s' matched into '%s'" % (event.name,
                                                        scan)
                LOGGER.debug(msg)
                try:
                    self.publisher.publish(self.topic, scan)
                except TypeError:
                    # happens with python 2.7
                    self.publisher.publish(self.topic,
                                           scan.encode('utf8'))


def main():
    console = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    LOGGER.addHandler(console)

    parser = argparse.ArgumentParser(description="ochlero")
    parser.add_argument('--config-file', '-c', metavar='/PATH/TO/CONF',
                        help='The path to the configuration file to use.')
    parser.add_argument('--verbose', '-v', default=False, action='store_true',
                        help='Run in debug mode')

    args = parser.parse_args()
    if args.verbose:
        console.setLevel(logging.DEBUG)
    else:
        console.setLevel(logging.INFO)
    if not args.config_file:
        sys.exit('Please provide a config file with option -c.')
    if not os.path.isfile(args.config_file):
        sys.exit('%s not found.' % args.config_file)
    with open(args.config_file, 'r') as raw_conf:
        conf = yaml.load(raw_conf)
    if 'mqtt' not in conf:
        sys.exit('MQTT configuration missing in %s' % args.config_file)

    LOGGER.debug(
        'Creating MQTT publisher on %s:%s' % (conf['mqtt']['host'],
                                              conf['mqtt']['port']))
    publisher = Publisher(conf['mqtt']['host'],
                          port=conf['mqtt']['port'],
                          auth_dict=conf['mqtt'].get('auth'))

    LOGGER.info('Starting the watch...')
    p = select.poll()
    journal = systemd_journal.Reader()
    # Set the reader's default log level
    journal.log_level(systemd_journal.LOG_DEBUG)
    # Only include entries since the current box has booted.
    journal.this_boot()
    # journal.this_machine()
    # Move to the end of the journal
    journal.seek_tail()
    # Important! - Discard old journal entries
    journal.get_previous()
    watchers = []
    for watcher in conf.get('watchers'):
        msg = "Adding watcher: unit '%s', comm '%s'"
        msg = msg % (watcher.get('unit', 'N/A'),
                     watcher.get('comm', 'N/A'))
        LOGGER.debug(msg)
        events = []
        e_id = 0
        for event in watcher['events']:
            name = event.get('name', 'event%03d' % e_id)
            e = Event(name,
                      event['pattern'],
                      event.get('where', {}),
                      event['publish'])
            LOGGER.debug(' |_ Adding event %s' % name)
            events.append(e)
            e_id += 1
        w = Watcher(watcher.get('unit'), watcher.get('comm'),
                    watcher['topic'], publisher, events)
        watchers.append(w)

    fd = journal.fileno()
    poll_event_mask = journal.get_events()
    p.register(fd, poll_event_mask)
    while p.poll():
        try:
            if journal.process() == systemd_journal.APPEND:
                LOGGER.debug("The journal was updated, checking...")
                for entry in journal:
                    LOGGER.debug("New event: %s" % entry['MESSAGE'])
                    for watcher in watchers:
                        watcher.watch(entry)
        except KeyboardInterrupt:
            LOGGER.info('Ctrl-C detected. Bye!')
            sys.exit('Manually stopped')


if __name__ == '__main__':
    main()
