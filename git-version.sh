#!/usr/bin/env bash

pushd "$1"
GIT_VERSION=`git log -n1 --format="%h"`
popd

echo ${GIT_VERSION}
