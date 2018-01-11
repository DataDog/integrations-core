#!/bin/bash

for d in $(find . -type d -d 1 | grep -v venv); do
    echo "processing $d..."
    if [ -f $d/check.py ]; then
        mkdir -p $d/check/$d
        touch $d/check/__init__.py
        touch $d/check/$d/__init__.py
        git mv $d/check.py $d/check/$d/$d.py
        if [ -f $d/conf.yaml.default ]; then
            git mv $d/conf.yaml.default $d/check/$d/$d.yaml.default
        else
            git mv $d/conf.yaml.example $d/check/$d/$d.yaml.example
        fi
        mkdir -p $d/test
        touch $d/test/__init__.py
        git mv $d/test_* $d/test/
    fi
    if [ ! -f $d/setup.py ]; then
        cp ntp/setup.py $d/setup.py
        git add $d/setup.py
    fi
done
