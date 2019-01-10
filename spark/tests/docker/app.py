import time

from pyspark import SparkContext
from pyspark.streaming import StreamingContext


def main():
    # Adapted from https://github.com/apache/spark/tree/master/examples/src/main/python/streaming
    sc = SparkContext(appName='PythonStreamingQueue')
    ssc = StreamingContext(sc, 1)

    # Create the queue through which RDDs can be pushed to
    # a QueueInputDStream
    rddQueue = []
    for _ in range(5):
        rddQueue += [ssc.sparkContext.parallelize([j for j in range(1, 1001)], 10)]

    # Create the QueueInputDStream and use it do some processing
    inputStream = ssc.queueStream(rddQueue)
    mappedStream = inputStream.map(lambda x: (x % 10, 1))
    reducedStream = mappedStream.reduceByKey(lambda a, b: a + b)
    reducedStream.pprint()

    ssc.start()
    time.sleep(6)
    ssc.stop(stopSparkContext=True, stopGraceFully=True)


if __name__ == '__main__':
    main()
