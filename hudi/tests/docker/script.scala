import org.apache.hudi.QuickstartUtils._
import scala.collection.JavaConversions._
import org.apache.spark.sql.SaveMode._
import org.apache.hudi.DataSourceReadOptions._
import org.apache.hudi.DataSourceWriteOptions._
import org.apache.hudi.config.HoodieWriteConfig
import org.apache.spark.sql.SparkSession

object SimpleApp {
  def main(args: Array[String]) {
    val spark = SparkSession.builder.appName("Simple Application").getOrCreate()
    import spark.implicits._
    //hudi examples found in https://hudi.apache.org/docs/quick-start-guide
    val tableName = "hudi_trips_cow"
    val basePath = "file:///tmp/hudi_trips_cow"
    val dataGen = new DataGenerator

    val df = spark.read.json(spark.sparkContext.parallelize(convertToStringList(dataGen.generateInserts(10)), 2))

    df.write.format("hudi").
        options(getQuickstartWriteConfigs).
        option("hoodie.metrics.on", "true").
        option("hoodie.metrics.reporter.type", "JMX").
        option("hoodie.metrics.jmx.port", "9999").
        option(PRECOMBINE_FIELD_OPT_KEY, "ts").
        option(RECORDKEY_FIELD_OPT_KEY, "uuid").
        option(PARTITIONPATH_FIELD_OPT_KEY, "partitionpath").
        option(HoodieWriteConfig.TABLE_NAME, tableName).
        mode(Append).
        save(basePath)


    val dfUpdates = spark.read.json(spark.sparkContext.parallelize(convertToStringList(dataGen.generateUpdates(10)), 2))

    dfUpdates.write.format("hudi").
        options(getQuickstartWriteConfigs).
        option("hoodie.metrics.on", "true").
        option("hoodie.metrics.reporter.type", "JMX").
        option("hoodie.metrics.jmx.port", "9999").
        option(PRECOMBINE_FIELD_OPT_KEY, "ts").
        option(RECORDKEY_FIELD_OPT_KEY, "uuid").
        option(PARTITIONPATH_FIELD_OPT_KEY, "partitionpath").
        option(HoodieWriteConfig.TABLE_NAME, tableName).
        mode(Append).
        save(basePath)

    val tripsSnapshotDF = spark.
        read.
        format("hudi").
        load(basePath)
    tripsSnapshotDF.createOrReplaceTempView("hudi_trips_snapshot")

    val commits = spark.sql("select distinct(_hoodie_commit_time) as commitTime from  hudi_trips_snapshot order by commitTime").map(k => k.getString(0)).take(50)
    val beginTime = commits(commits.length - 2) // commit time we are interested in

    val tripsIncrementalDF = spark.read.format("hudi").
        option("hoodie.metrics.on", "true").
        option("hoodie.metrics.reporter.type", "JMX").
        option("hoodie.metrics.jmx.port", "9999").
        option(QUERY_TYPE_OPT_KEY, QUERY_TYPE_INCREMENTAL_OPT_VAL).
        option(BEGIN_INSTANTTIME_OPT_KEY, beginTime).
        load(basePath)
    tripsIncrementalDF.createOrReplaceTempView("hudi_trips_incremental")

    spark.sql("select `_hoodie_commit_time`, fare, begin_lon, begin_lat, ts from  hudi_trips_incremental where fare > 20.0").show()


    val beginTimeWithEnd = "000" 
    val endTime = commits(commits.length - 2) 

    val tripsPointInTimeDF = spark.read.format("hudi").
        option("hoodie.metrics.on", "true").
        option("hoodie.metrics.reporter.type", "JMX").
        option("hoodie.metrics.jmx.port", "9999").
        option(QUERY_TYPE_OPT_KEY, QUERY_TYPE_INCREMENTAL_OPT_VAL).
        option(BEGIN_INSTANTTIME_OPT_KEY, beginTimeWithEnd).
        option(END_INSTANTTIME_OPT_KEY, endTime).
        load(basePath)
        
    tripsPointInTimeDF.createOrReplaceTempView("hudi_trips_point_in_time")
    spark.sql("select `_hoodie_commit_time`, fare, begin_lon, begin_lat, ts from hudi_trips_point_in_time where fare > 20.0").show()


    spark.sql("select uuid, partitionpath from hudi_trips_snapshot").count() 
    val ds = spark.sql("select uuid, partitionpath from hudi_trips_snapshot").limit(2)

    val deletes = dataGen.generateDeletes(ds.collectAsList()) 
    val dfParallel = spark.read.json(spark.sparkContext.parallelize(deletes, 2))

    dfParallel.write.format("hudi"). 
        options(getQuickstartWriteConfigs).
        option("hoodie.metrics.on", "true").
        option("hoodie.metrics.reporter.type", "JMX").
        option("hoodie.metrics.jmx.port", "9999").
        option(OPERATION_OPT_KEY,"delete"). 
        option(PRECOMBINE_FIELD_OPT_KEY, "ts"). 
        option(RECORDKEY_FIELD_OPT_KEY, "uuid"). 
        option(PARTITIONPATH_FIELD_OPT_KEY, "partitionpath"). 
        option(HoodieWriteConfig.TABLE_NAME, tableName). 
        mode(Append). 
        save(basePath)

    spark.
        read.format("hudi").
        load(basePath).
        select("uuid","partitionpath").
        show(10, false)

    val insertsOverwrite = convertToStringList(dataGen.generateInserts(10))
    val dfOverwrite = spark.read.json(spark.sparkContext.parallelize(insertsOverwrite, 2))

    dfOverwrite.write.format("hudi").
        options(getQuickstartWriteConfigs).
        option("hoodie.metrics.on", "true").
        option("hoodie.metrics.reporter.type", "JMX").
        option("hoodie.metrics.jmx.port", "9999").
        option(OPERATION_OPT_KEY,"insert_overwrite_table").
        option(PRECOMBINE_FIELD_OPT_KEY, "ts").
        option(RECORDKEY_FIELD_OPT_KEY, "uuid").
        option(PARTITIONPATH_FIELD_OPT_KEY, "partitionpath").
        option(HoodieWriteConfig.TABLE_NAME, tableName).
        mode(Append).
        save(basePath)

    spark.
    read.format("hudi").
    load(basePath).
    select("uuid","partitionpath").
    show(10, false)


    spark.
        read.format("hudi").
        load(basePath).
        select("uuid","partitionpath").
        sort("partitionpath","uuid").
        show(100, false)

    val insertsOverwrite2 = convertToStringList(dataGen.generateInserts(10))
    val dfOverwrite2 = spark.
        read.json(spark.sparkContext.parallelize(insertsOverwrite2, 2)).
        filter("partitionpath = 'americas/united_states/san_francisco'")

    dfOverwrite2.write.format("hudi").
        options(getQuickstartWriteConfigs).
        option("hoodie.metrics.on", "true").
        option("hoodie.metrics.reporter.type", "JMX").
        option("hoodie.metrics.jmx.port", "9999").
        option("hoodie.embed.timeline.server", "true").
        option(OPERATION_OPT_KEY,"insert_overwrite").
        option(PRECOMBINE_FIELD_OPT_KEY, "ts").
        option(RECORDKEY_FIELD_OPT_KEY, "uuid").
        option(PARTITIONPATH_FIELD_OPT_KEY, "partitionpath").
        option(HoodieWriteConfig.TABLE_NAME, tableName).
        mode(Append).
        save(basePath)

    spark.
        read.format("hudi").
        load(basePath).
        select("uuid","partitionpath").
        sort("partitionpath","uuid").
        show(100, false)

    while(true) {
        Thread.sleep(10)
    }
  }
}