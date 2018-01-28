#!/bin/bash
set -e
HOST=$1
SERVICENAME=$2
LINENUM=$3
LOGFILE="/u01/projects/futhor/nova.log"
if [ $LINENUM ];then
    ssh -A -T root@$HOST "sed -n ${LINENUM}p $LOGFILE"
else
    ssh -A -T root@$HOST "wc -l $LOGFILE|awk '{print \$1}'"
fi