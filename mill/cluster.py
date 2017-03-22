#!/usr/bin/env python

"""
Orchestrate a poor man's cluster system.
Because Ryan and Joe intensely dislike other vegetable-named methods for doing this.
"""

from makeface import abspath

class Cluster:

	"""
	Make a computation cluster.
	"""

	def __init__(self,dn):
		"""
		Register a jobs directory and validate it.
		"""
		self.dn = abspath(dn)
		if not os.path.isdir(self.dn): os.mkdir(self.dn)

	def get_queue(self):
		"""
		See how many jobs are running or waiting.
		"""

	def submit():
		"""
		Add a new job.
		"""





