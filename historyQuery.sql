SELECT
    j.name,
    sjh1.job_id,
    sjh1.step_name,
    sjh1.step_id,
    sjh1.instance_id AS step_instance_id,
    (
        SELECT MIN(sjh2.instance_id)
        FROM msdb.dbo.sysjobhistory AS sjh2
        WHERE sjh2.job_id = sjh1.job_id
        AND sjh2.step_id = 0
        AND sjh2.instance_id >= sjh1.instance_id
    ) AS completion_instance_id,
    (
        SELECT DATEDIFF(SECOND, GETDATE(), SYSDATETIMEOFFSET()) +
            DATEDIFF(SECOND, '19700101',
                DATEADD(HOUR, sjh1.run_time / 10000,
                    DATEADD(MINUTE, (sjh1.run_time / 100) % 100,
                        DATEADD(SECOND, sjh1.run_time % 100,
                            CAST(CAST(sjh1.run_date AS CHAR(8)) AS DATETIME)
                        )
                    )
                )
            )
    ) AS run_epoch_time,
    (
        (sjh1.run_duration / 10000) * 3600
        + ((sjh1.run_duration % 10000) / 100) * 60
        + (sjh1.run_duration % 100)
    ) AS run_duration_seconds,
    sjh1.run_status,
    sjh1.message
FROM 
    msdb.dbo.sysjobhistory AS sjh1
INNER JOIN msdb.dbo.sysjobs AS j
ON j.job_id = sjh1.job_id
WHERE
    EXISTS (
        SELECT 1
        FROM msdb.dbo.sysjobhistory AS sjh2
        WHERE sjh2.job_id = sjh1.job_id
        AND sjh2.step_id = 0
        AND sjh2.instance_id >= sjh1.instance_id
        HAVING  MIN(DATEDIFF(SECOND, GETDATE(), SYSDATETIMEOFFSET()) +
                    DATEDIFF(SECOND, '19700101',
                        DATEADD(HOUR, sjh2.run_time / 10000,
                            DATEADD(MINUTE, (sjh2.run_time / 100) % 100,
                                DATEADD(SECOND, sjh2.run_time % 100,
                                    CAST(CAST(sjh2.run_date AS CHAR(8)) AS DATETIME)
                                )
                            )
                        )
                    )
                + (sjh2.run_duration / 10000) * 3600
        + ((sjh2.run_duration % 10000) / 100) * 60
        + (sjh2.run_duration % 100)) > 0 + 1719947315
    )