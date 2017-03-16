import logging
import os
import re
import sys

import systemd
import paho.mqtt.publish as mqtt_publish
# import yaml

# import datetime
# import time
import select


LOGGER = logging.getLogger('ochlero')
LOGGER.setLevel(logging.DEBUG)


# TODO add predefined regexps for convenience
PREDEFINED_TYPES = {
    "_SYSLOGTIME_": "",
    "_IPv4_": "",
    "_EMAIL_": "",
    "_LOGLEVEL_": "",
    "_ALPHANUMERIC_": "\w+",
    "_INT_": "[0-9]+",
}


def map_predefined_types(substitute):
    mapped = substitute
    for t, r in PREDEFINED_TYPES.items():
        mapped = mapped.replace(t, r)
    return mapped


class Publisher(object):
    def __init__(self, hostname, port, auth_dict=None):
        self.hostname = hostname
        self.port = port
        self.auth_dict = auth_dict

    def publish(self, topic, message):
        mqtt_publish.single(topic, payload=message,
                            hostname=self.hostname, port=self.port,
                            client_id="ochlero/%i" % os.getpid(),
                            auth=self.auth_dict)


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
    def __init__(self, unit, topic, publisher, events):
        self.unit = unit
        self.topic = topic
        self.publisher = publisher
        self.events = events
        # Create a systemd.journal.Reader instance
        self.journal = systemd.journal.Reader()
        # Set the reader's default log level
        self.journal.log_level(systemd.journal.LOG_INFO)
        # Only include entries since the current box has booted.
        self.journal.this_boot()
        self.journal.this_machine()
        # Filter log entries
        self.journal.add_match(_SYSTEMD_UNIT=self.unit)
        # Move to the end of the journal
        self.journal.seek_tail()
        # Important! - Discard old journal entries
        self.journal.get_previous()

    def watch(self):
        if self.journal.process() == systemd.journal.APPEND:
            for entry in self.journal:
                for event in self.events:
                    scan = event.scan(entry)
                    if scan:
                        self.publisher.publish(self.topic, scan)


def main():
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    LOGGER.addHandler(console)

    LOGGER.info('Starting the watch...')
    p = select.poll()
    watchers = []
    # INIT WATCHERS
    for watcher in watchers:
        fd = watcher.journal.fileno()
        poll_event_mask = watcher.journal.get_events()
        p.register(fd, poll_event_mask)
    while True:
        try:
            # check every 250ms
            if p.poll(250):
                for watcher in watchers:
                    watcher.watch()
        except KeyboardInterrupt:
            LOGGER.info('Ctrl-C detected. Bye!')
            sys.exit('Manually stopped')


if __name__ == '__main__':
    main()
