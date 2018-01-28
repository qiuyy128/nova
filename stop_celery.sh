celery multi stop -A nova worker -c 4 -l info --pidfile=nova.pid
ps -ef|grep celery|grep -v grep |awk '{print $2}'|xargs kill -9
