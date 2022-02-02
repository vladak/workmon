#!/usr/bin/env python3

import time

from prometheus_client import Gauge, start_http_server

g = Gauge("table_position", "Table position")
start_http_server(8111)

# g.set(2)
g.set('NaN')
time.sleep(60)
