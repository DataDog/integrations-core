# I took these defaults from
# https://github.com/tswicegood/docker-gunicorn/blob/master/config.py

bind = "0.0.0.0:18000"
loglevel = "INFO"
workers = "4"
reload = True

default_proc_name = "dd_test_gunicorn"

errorlog = "-"
accesslog = "-"
