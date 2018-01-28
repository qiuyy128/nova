nohup celery -A nova worker --loglevel=info --logfile=nova.log &
# 通过multi命令你可以启动多个workers
celery multi start -A nova worker -c 4 -l info --pidfile=nova%I.pid --logfile=nova%I.log
