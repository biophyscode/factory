#!/usr/bin/env python

"""
Start the cluster here. Requires a separate script because backrun calls it.
A single argument sends the kill-switch to the cluster shutdown for cleanup.
"""

import os,sys
from cluster import Cluster
kwargs = dict(spot='cluster')
if sys.argv>1: kwargs.update(kill_switch=sys.argv[1])
elif sys.argv>2: raise Exception('too many arguments')
#---ensure no zombie clusters which CAUSE SERIOUS ERRORS from overeager cluster submission
os.system('ps aux | grep -P "[c]lusterhalt" | awk \'{print $2}\' | pkill')
Cluster(**kwargs)
