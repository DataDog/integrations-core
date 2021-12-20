set target=c:\ibm_mq
set version=9.2.2.0
set file=%version%-IBM-MQC-Redist-Win64.zip
set source=https://public.dhe.ibm.com/ibmdl/export/pub/software/websphere/messaging/mqdev/redist/%file%

:: Downloading IBM MQ client
powershell -command "Invoke-WebRequest -Uri %source% -OutFile %target%\%file%"
dir $target
:: Extracting IBM MQ client
powershell -command "Expand-Archive %target%\%file% %target%"
dir $target
