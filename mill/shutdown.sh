#!/bin/bash

<<notes
Turn off the servers.
Works for both celery and old-school backrun.
notes

#---check for stop scripts which indicate old-school background running
if ls ./logs/script-stop* 1> /dev/null 2>&1; then
	#---run the stop scripts
	for f in ./logs/script-stop*; do
		echo "[STATUS] shutting down with \"$f\""
		./$f
		rm $f
	done
fi

#---celery shutdown procedure
if [[ -z $1 ]]; then incoming="\.\w+"; else incoming="\.$1"; fi
#---get the PID of the suspended screen
#---previously used: screen -r multiplexer and the user had to send ctrl+c
echo "[SERVE] shutting down runserver, worker, and flower"
PID=$(screen -ls | perl -ne 'BEGIN{ $arg=shift } print $1 . " " if /^\s*([0-9]+)$arg\.multiplexer/' $incoming)
if ! [[ -z $PID ]]; then kill -KILL $PID; fi
PID=$(screen -ls | perl -ne 'BEGIN{ $arg=shift } print $1 . " " if /^\s*([0-9]+)$arg\.flower/' $incoming)
if ! [[ -z $PID ]]; then kill -KILL $PID; fi
PID=$(screen -ls | perl -ne 'BEGIN{ $arg=shift } print $1 . " " if /^\s*([0-9]+)$arg\.worker_sim/' $incoming)
if ! [[ -z $PID ]]; then kill -KILL $PID; fi
PID=$(screen -ls | perl -ne 'BEGIN{ $arg=shift } print $1 . " " if /^\s*([0-9]+)$arg\.worker_calc/' $incoming)
if ! [[ -z $PID ]]; then kill -KILL $PID; fi
#---! should we wipe screens here? with: screen -wipe &> /dev/null
echo "[SERVE] see log/log-serve for messages"
echo "[STATUS] bye"
