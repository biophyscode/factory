#!/usr/bin/env python

"""
Run a script in the background with a new group ID and a script which will kill the job and children.
"""

import sys,os,re,subprocess
specs = {}
regex_pop = '^%s=(.+)'
for name in ['cmd','name','log','cwd','pre','stopper']:
	try: 
		flag = sys.argv.pop([None!=re.match(regex_pop%name,s) for s in sys.argv].index(True))
		specs[name] = re.match(regex_pop%name,flag).group(1)	
	except: specs[name] = None
#---required flags
if any([not specs[name] for name in ['cmd','name']]):
	print('[USAGE] \'./backrun.py name="<name>" command="<command>"\' (make sure you use double quotes)')
	print('[USAGE] runs a job in the background and gives you a killswitch')
	sys.exit(1)
#---defaults
if not specs['cwd']: specs['cwd'] = './'
if not specs['log']: specs['log'] = 'log-backrun-%s'%specs['name']
specs['pre'] = specs['pre']+' && ' if specs['pre'] else ''
if not specs['stopper']: specs['stopper'] = 'script-stop-%s.sh'%specs['name']
print(specs)
cmd_full = "%snohup %s > %s 2>&1 &"%(specs['pre'],specs['cmd'],specs['log'])
print('[BACKRUN] running "%s"'%cmd_full)
job = subprocess.Popen(cmd_full,shell=True,cwd=specs['cwd'],preexec_fn=os.setsid,executable='/bin/bash')
ask = subprocess.Popen('ps xao pid,ppid,pgid,sid,comm',shell=True,
	stdout=subprocess.PIPE,stderr=subprocess.PIPE,executable='/bin/bash')
print(job.pid)
stdout,stderr = ask.communicate()
#---get the pgid for this job pid
#---note that sometimes OSX only gives the first three items in the ps request
ids = [int(j) for j in re.search('^(%d)\s+(\d+)\s+(\d+).*?\n'%job.pid,stdout.decode(),flags=re.M).groups()]
pgid = ids[2]
print('[NOTE] pid=%d pgid=%d'%(pid,pgid))
term_command = 'pkill -TERM -g %d'%pgid
kill_switch = os.path.join(specs['cwd'],specs['stopper'])
with open(kill_switch,'w') as fp: fp.write(term_command+'\n')
os.chmod(kill_switch,0o744)
job.communicate()
