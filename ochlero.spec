%global         sum systemd log monitor that publishes to an MQTT bus on specific events

Name:           ochlero
Version: 0.1.1.2.gb75d33a
Release:        2%{?dist}
Summary:        %{sum}

License:        ASL 2.0
URL:            https://softwarefactory-project.io/r/p/software-factory/%{name}
Source0: HEAD.tgz

BuildArch:      noarch

Requires:       python-paho-mqtt
Requires:       PyYAML
Requires:       systemd-python

Buildrequires:  python2-devel
Buildrequires:  python-setuptools
Buildrequires:  python2-pbr
Buildrequires:  python-nose
Buildrequires:	python-mock
Buildrequires:  git
Buildrequires:	systemd-python
Buildrequires:	PyYAML
Buildrequires:	python-paho-mqtt

%description
systemd log monitor that publishes to an MQTT bus on specific events

%prep
%autosetup -n %{name}-%{version}

%build
# init git for pbr
git init
%{__python2} setup.py build

%install
%{__python2} setup.py install --skip-build --root %{buildroot}

%check
nosetests -v

%files -n ochlero
%{python2_sitelib}/*
%{_bindir}/*

%changelog
* Tue Mar 21 2017 Matthieu Huin <mhuin@redhat.com> - 0.1.1-2
- Add mock to build dependencies

* Mon Mar 20 2017 Matthieu Huin <mhuin@redhat.com> - 0.1.1-1
- Initial package
