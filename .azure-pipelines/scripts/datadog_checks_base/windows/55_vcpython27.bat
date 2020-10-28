:: Need to install Microsoft Visuall C++ 9.0 for python 2.7 manually because of
:: https://github.com/microsoft/azure-pipelines-image-generation/issues/793/
:: Some dependencies require compilation steps, at time of writing only `mmh3`.
choco install vcpython27 --yes
