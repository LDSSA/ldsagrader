#!/usr/bin/env bash

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

source /usr/local/bin/activate LU
ldsagrader checksum digest "/opt/lu/Exercise notebook.ipynb" > /tmp/checksums
ldsagrader notebook validate --checksums=/tmp/checksums "/opt/lu/Exercise notebook.ipynb"
