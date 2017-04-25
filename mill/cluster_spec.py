#!/usr/bin/env python

"""
File naming conventions for the "cluster".
Important to the connection between factory and the cluster.
"""

keepsakes = 'waiting running finished'.split()

#---extract the stamp with e.g.: '^%s$'%re.sub('STAMP','(.+)',waiting)
#---glob the files with e.g.: re.sub('STAMP','*',waiting)
waiting = 'STAMP.req'
running = 'run-STAMP'
finished = 'fin-STAMP'
