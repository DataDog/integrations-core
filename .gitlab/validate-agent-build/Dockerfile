FROM 486234852809.dkr.ecr.us-east-1.amazonaws.com/base-python3:focal
USER root

COPY devtools/deb/slack-notifier/ /slack-notifier

RUN clean-apt install python3.9-dev git gcc
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python3 -u get-pip.py && rm get-pip.py
RUN pip install -r /slack-notifier/requirements.txt
RUN pip install /slack-notifier
RUN rm -Rf /slack-notifier

COPY validate_agent_build.py /validate_agent_build.py
COPY trigger_agent_build.py /trigger_agent_build.py

