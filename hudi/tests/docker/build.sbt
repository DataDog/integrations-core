scalaVersion := "2.12.11"
libraryDependencies ++= Seq(
  "org.apache.spark" %% "spark-sql" % "3.0.0" % "provided",
  "org.apache.spark" %% "spark-core" % "3.0.0" % "provided",
  "org.apache.hudi" %% "hudi-spark-client" % "0.10.0-rc3" from "https://repository.apache.org/content/repositories/orgapachehudi-1048/org/apache/hudi/hudi-spark3-bundle_2.12/0.10.0-rc3/hudi-spark3-bundle_2.12-0.10.0-rc3.jar"
)
