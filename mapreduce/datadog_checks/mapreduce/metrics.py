"""
MapReduce Job Metrics
---------------------
mapreduce.job.elapsed_time                The elapsed time since the application started (in ms)
mapreduce.job.maps_total                 The total number of maps
mapreduce.job.maps_completed             The number of completed maps
mapreduce.job.reduces_total              The total number of reduces
mapreduce.job.reduces_completed          The number of completed reduces
mapreduce.job.maps_pending               The number of maps still to be run
mapreduce.job.maps_running               The number of running maps
mapreduce.job.reduces_pending            The number of reduces still to be run
mapreduce.job.reduces_running            The number of running reduces
mapreduce.job.new_reduce_attempts        The number of new reduce attempts
mapreduce.job.running_reduce_attempts    The number of running reduce attempts
mapreduce.job.failed_reduce_attempts     The number of failed reduce attempts
mapreduce.job.killed_reduce_attempts     The number of killed reduce attempts
mapreduce.job.successful_reduce_attempts The number of successful reduce attempts
mapreduce.job.new_map_attempts           The number of new map attempts
mapreduce.job.running_map_attempts       The number of running map attempts
mapreduce.job.failed_map_attempts        The number of failed map attempts
mapreduce.job.killed_map_attempts        The number of killed map attempts
mapreduce.job.successful_map_attempts    The number of successful map attempts

MapReduce Job Counter Metrics
-----------------------------
mapreduce.job.counter.reduce_counter_value   The counter value of reduce tasks
mapreduce.job.counter.map_counter_value      The counter value of map tasks
mapreduce.job.counter.total_counter_value    The counter value of all tasks

MapReduce Map Task Metrics
--------------------------
mapreduce.job.map.task.progress     The distribution of all map task progresses

MapReduce Reduce Task Metrics
--------------------------
mapreduce.job.reduce.task.progress      The distribution of all reduce task progresses
"""

# Metric types
HISTOGRAM = 'histogram'
INCREMENT = 'increment'

# Metrics to collect
MAPREDUCE_JOB_METRICS = {
    'elapsedTime': ('mapreduce.job.elapsed_time', HISTOGRAM),
    'mapsTotal': ('mapreduce.job.maps_total', INCREMENT),
    'mapsCompleted': ('mapreduce.job.maps_completed', INCREMENT),
    'reducesTotal': ('mapreduce.job.reduces_total', INCREMENT),
    'reducesCompleted': ('mapreduce.job.reduces_completed', INCREMENT),
    'mapsPending': ('mapreduce.job.maps_pending', INCREMENT),
    'mapsRunning': ('mapreduce.job.maps_running', INCREMENT),
    'reducesPending': ('mapreduce.job.reduces_pending', INCREMENT),
    'reducesRunning': ('mapreduce.job.reduces_running', INCREMENT),
    'newReduceAttempts': ('mapreduce.job.new_reduce_attempts', INCREMENT),
    'runningReduceAttempts': ('mapreduce.job.running_reduce_attempts', INCREMENT),
    'failedReduceAttempts': ('mapreduce.job.failed_reduce_attempts', INCREMENT),
    'killedReduceAttempts': ('mapreduce.job.killed_reduce_attempts', INCREMENT),
    'successfulReduceAttempts': ('mapreduce.job.successful_reduce_attempts', INCREMENT),
    'newMapAttempts': ('mapreduce.job.new_map_attempts', INCREMENT),
    'runningMapAttempts': ('mapreduce.job.running_map_attempts', INCREMENT),
    'failedMapAttempts': ('mapreduce.job.failed_map_attempts', INCREMENT),
    'killedMapAttempts': ('mapreduce.job.killed_map_attempts', INCREMENT),
    'successfulMapAttempts': ('mapreduce.job.successful_map_attempts', INCREMENT),
}

MAPREDUCE_JOB_COUNTER_METRICS = {
    'reduceCounterValue': ('mapreduce.job.counter.reduce_counter_value', INCREMENT),
    'mapCounterValue': ('mapreduce.job.counter.map_counter_value', INCREMENT),
    'totalCounterValue': ('mapreduce.job.counter.total_counter_value', INCREMENT),
}

MAPREDUCE_MAP_TASK_METRICS = {'elapsedTime': ('mapreduce.job.map.task.elapsed_time', HISTOGRAM)}

MAPREDUCE_REDUCE_TASK_METRICS = {'elapsedTime': ('mapreduce.job.reduce.task.elapsed_time', HISTOGRAM)}
