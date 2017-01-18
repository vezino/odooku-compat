import odooku.patches
from odooku.projects import load_projects
load_projects()

import gevent.monkey
gevent.monkey.patch_all()

import psycogreen.gevent
psycogreen.gevent.patch_psycopg()

import csv
csv.field_size_limit(500 * 1024 * 1024)
