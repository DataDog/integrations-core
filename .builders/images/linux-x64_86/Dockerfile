ARG BASE_IMAGE=quay.io/pypa/manylinux2014_x86_64
FROM ${BASE_IMAGE}

ARG PYTHON_MAJOR

ENV PATH="/opt/python/cp${PYTHON_MAJOR}-cp${PYTHON_MAJOR}/bin:${PATH}"

CMD ["python", "-m", "pip", "install", "-r", "/home/requirements.in"]
