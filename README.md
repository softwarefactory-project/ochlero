OCHLERO
=======

Ochlero is a script that monitors the systemd journal for specific events that
trigger publications on an MQTT queue.

"Ochlero" comes from "Ochlerotatus Triseriatus", a species of tree hole breeding
mosquitoes (https://en.wikipedia.org/wiki/Ochlerotatus_triseriatus), ie
mosquitoes that like logs...

Running and testing
-------------------

Ochlero is tested against and runs on python 2.7 and python 3.5.

With python 2.x you need to install the systemd and mqtt wrappers on your system.
On CentOS or Fedora, you can do so with the following command (extra repositories
such as EPEL might need to be activated):

:: sudo yum install systemd-python python-paho-mqtt

This is necessary due to a problem in the PyPI version of the systemd wrapper.

With python 3.5, running

:: pip install -r requirements.txt

should be enough.

To start ochlero, simply run

:: ochlero -c /path/to/config/file
