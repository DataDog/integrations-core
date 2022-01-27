scalaVersion := "2.12.11"
libraryDependencies ++= Seq(
  "org.apache.spark" %% "spark-sql" % sys.env.get("SPARK_VERSION").get % "provided",
  "org.apache.spark" %% "spark-core" % sys.env.get("SPARK_VERSION").get % "provided",
  "org.apache.hudi" %% "hudi-spark3-bundle" % sys.env.get("HUDI_VERSION").get
)
