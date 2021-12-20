set target=c:\ibm_mq
set version=9.2.2.0
set file=%version%-IBM-MQC-Redist-Win64.zip
set ibm_source=https://public.dhe.ibm.com/ibmdl/export/pub/software/websphere/messaging/mqdev/redist/%file%
set source=https://drive.google.com/uc?export=download&id=1ysTsHxAAxIwl0EwFnYzN5cNRBnvKwELw

md %target%
:: Downloading IBM MQ client
powershell -command "Invoke-WebRequest -Uri %source% -OutFile %target%\%file%"
:: Extracting IBM MQ client
powershell -command "Expand-Archive -LiteralPath %target%\%file% -DestinationPath %target%"
dir %target%
