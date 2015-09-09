# Installing Utilery

Warning: Utilery is not yet released as python package,
because some Python dependencies are not released yet in pypi.

## System dependencies

- PostgreSQL
- PostGIS
- python3.4
- git (for installation)

## Install using a virtualenv

1. Install [PostgreSQL](https://wiki.postgresql.org/wiki/Detailed_installation_guides)

1. Install dependencies:

        sudo apt-get install python3.4 python3.4-dev python-pip python-virtualenv virtualenvwrapper git

1. Create a virtualenv:

        mkvirtualenv utilery --python=/usr/bin/python3.4

1. Clone Utilery:

        git clone https://github.com/etalab/utilery

1. Install python package:

        cd utilery
        pip install .

1. Install unstable python dependencies:

        pip install -r requirements.txt




## What to do next?
Now you certainly want to [configure Utilery](config.md).
