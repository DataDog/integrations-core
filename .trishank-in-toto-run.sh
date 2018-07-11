#!/bin/bash

in-toto-run -n tag -p . -g B9D5EC8FD089F227 -x
mv tag.6e7ac369.link .links/
git add .links
git commit -a
