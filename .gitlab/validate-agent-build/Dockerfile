FROM 486234852809.dkr.ecr.us-east-1.amazonaws.com/base-python3:focal

RUN clean-apt install python3-pip
RUN pip3 install requests
RUN pip3 install awscli
COPY validate_agent_build.py /validate_agent_build.py
COPY trigger_agent_build.py /trigger_agent_build.py

