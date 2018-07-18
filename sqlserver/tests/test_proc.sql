
IF  EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[GetDatadogMetricsTest]') AND type in (N'P', N'PC'))
DROP PROCEDURE [dbo].[GetDatadogMetricsTest]
GO

SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO


-- =======================================================================================
-- Description:	Gets metrics for Datadog
-- =======================================================================================
CREATE PROCEDURE [dbo].[GetDatadogMetricsTest]
AS
BEGIN
	set transaction isolation level read uncommitted
	set nocount on

	-- if the DB is read only then we must be a secondary so don't report any data
	IF (SELECT CONVERT(sysname,DatabasePropertyEx(DB_NAME(),'Updateability'))) = 'READ_ONLY'
		RETURN

	CREATE TABLE #Datadog
	(
		[metric] varchar(255) not null,
		[type] varchar(50) not null,
		[value] float not null,
		[tags] varchar(255)
	)

	INSERT INTO #Datadog (metric, type, value, tags)
	VALUES ('sql.test.gauge', 'gauge', 5, 'tag:test')
		,('sql.test.rate', 'rate', 500, null)
		,('sql.test.histogram', 'histogram', FLOOR(RAND()*20), null)

	SELECT * FROM #Datadog
END
GO

GRANT EXECUTE ON [dbo].[GetDatadogMetricsTest] To Public
GO
