FROM mbrekkevold/navbase-debian:jessie

ENV DISPLAY :99
ENV ADMINPASSWORD omicronpersei8

# Remove these superfluous, and possibly conflicting accounts
RUN for U in systemd-timesync systemd-network systemd-resolve systemd-bus-proxy; do userdel -f $U; done

### Installing packages
RUN echo "deb http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys A040830F7FAC5991 1397BC53640DB551

# TODO: Might not need all the dependencies
RUN apt-get update && \
    apt-get -y --no-install-recommends build-dep \
	python-psycopg2 python-lxml librrd-dev python-imaging python-ldap

RUN apt-get update && \
    apt-get -y --no-install-recommends install \
	locales mercurial subversion git-core python-virtualenv python-pip \
	build-essential librrd-dev python-dev autoconf automake libsnmp30 \
	cron sudo apache2 libapache2-mod-wsgi rubygems inotify-tools python-cairo \
	postgresql postgresql-contrib postgresql-client \
	ruby-dev libxml2-dev libxslt1-dev net-tools \
	postgresql-server-dev-all libpq-dev libwww-perl python-rrdtool \
	iceweasel xvfb nodejs-legacy curl \
	python-iso8601 imagemagick x11vnc google-chrome-stable rrdtool cloc \
	cmake nbtscan python-gammu

RUN gem install --version '3.3.9' sass ; \
    gem install --version '~> 0.9' rb-inotify

# NPM for Javascript testing needs
RUN curl --insecure https://www.npmjs.com/install.sh | clean=no bash

# Build and install libtidy5
RUN cd /tmp && \
    git clone https://github.com/htacg/tidy-html5.git && \
    cd tidy-html5/build/cmake && \
    cmake ../.. -DCMAKE_INSTALL_PREFIX=/usr -DBUILD_SHARED_LIB:BOOL=ON && \
    make && make install && echo tidy5 installed

RUN adduser --system --group --home=/build --shell=/bin/bash build
RUN echo "build    ALL=NOPASSWD: ALL" >> /etc/sudoers

# Build and install Python requirements
ADD runtime-requirements.txt /runtime-requirements.txt
ADD test-requirements.txt /test-requirements.txt
RUN pip install -r /runtime-requirements.txt -r /test-requirements.txt
RUN pip install whisper carbon graphite-web django-tagging

# Install geckodriver to properly run Selenium tests in Firefox versions>=47
RUN cd /tmp && \
    wget https://github.com/mozilla/geckodriver/releases/download/v0.11.1/geckodriver-v0.11.1-linux64.tar.gz && \
    tar xvzf geckodriver-v0.11.1-linux64.tar.gz && \
    mv geckodriver /usr/local/bin/

# Install chromedriver to properly run Selenium tests in Chrome, if need be
RUN cd /tmp && \
    apt-get update && \
    apt-get -y --no-install-recommends install unzip && \
    wget http://chromedriver.storage.googleapis.com/2.24/chromedriver_linux64.zip && \
    unzip chromedriver_linux64.zip && \
    mv chromedriver /usr/local/bin/

# This does not make files in source accessible for RUN-commands
VOLUME ["/source"]

ENTRYPOINT ["/source/tests/docker/bootstrap.sh"]
