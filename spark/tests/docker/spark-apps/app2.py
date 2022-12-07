from pyspark.sql import SparkSession
from pyspark.sql.functions import explode, split, window


def main():
    spark = (
        SparkSession.builder.appName("StructuredStreaming")
        .config("spark.ui.port", "4050")
        .config("spark.sql.streaming.metricsEnabled", "true")
        .getOrCreate()
    )
    lines = (
        spark.readStream.format("socket")
        .option("host", "words-sender")
        .option("port", 9999)
        .option('includeTimestamp', 'true')
        .load()
    )

    # Split the lines into words
    words = lines.select(explode(split(lines.value, " ")).alias("word"), lines.timestamp)

    # Group the data by window and word and compute the count of each group
    word_counts = (
        words.withWatermark("timestamp", "30 seconds")
        .groupBy(window(words.timestamp, "30 seconds", "15 seconds", "3 seconds"), words.word)
        .count()
    )

    # Start running the query that prints the running counts to the console
    query = (
        word_counts.writeStream.queryName("my_named_query")
        .outputMode("complete")
        .format("console")
        .option('truncate', 'false')
        .start()
    )

    query.awaitTermination()
    print("Game over")


if __name__ == '__main__':
    main()
