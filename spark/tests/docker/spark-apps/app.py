from pyspark import SparkContext
from pyspark.streaming import StreamingContext


def main():
    # Adapted from https://github.com/apache/spark/tree/master/examples/src/main/python/streaming
    sc = SparkContext(appName="PythonStreaming")
    ssc = StreamingContext(sc, 1)

    lines = ssc.socketTextStream("localhost", 9998)
    counts = lines.flatMap(lambda line: line.split(" ")).map(lambda word: (word, 1)).reduceByKey(lambda a, b: a + b)
    counts.pprint()

    ssc.start()
    ssc.awaitTermination()


if __name__ == '__main__':
    main()
