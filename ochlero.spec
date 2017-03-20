%global         sum systemd log monitor that publishes to an MQTT bus on specific events

Name:           ochlero
Version:        0.1.1
Release:        1%{?dist}
Summary:        %{sum}

License:        ASL 2.0
URL:            https://softwarefactory-project.io/r/p/software-factory/%{name}
Source0:        https://pypi.python.org/packages/83/f3/df455eae3ab50c19e09d0946fc05efed01983599f1cf5f635ba4a2e34551/%{name}-%{version}.tar.gz#md5=67d32ee445663656292c82472ae32a07

BuildArch:      noarch

Requires:       python-paho-mqtt
Requires:       PyYAML
Requires:       systemd-python

Buildrequires:  python2-devel
Buildrequires:  python-setuptools
Buildrequires:  python2-pbr
Buildrequires:  python-nose
Buildrequires:  python2-mock

%description
systemd log monitor that publishes to an MQTT bus on specific events

%package -n ochlero
Summary:        %{sum}

Requires:       python-paho-mqtt
Requires:       PyYAML
Requires:       systemd-python

Buildrequires:  python2-devel
Buildrequires:  python-setuptools
Buildrequires:  python2-pbr
Buildrequires:  python-nose
Buildrequires:  python2-mock

%description -n ochlero
systemd log monitor that publishes to an MQTT bus on specific events

%prep
%autosetup -n %{name}-%{version}

%build
%{__python2} setup.py build

%install
%{__python2} setup.py install --skip-build --root %{buildroot}

%check
nosetests -v

%files -n ochlero
%{python2_sitelib}/*
%{_bindir}/*

%changelog
* Mon Mar 20 2017 Matthieu Huin <mhuin@redhat.com> - 0.1.1-1
- Initial package
