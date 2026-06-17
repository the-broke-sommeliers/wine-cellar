#!/bin/bash
if [[ "$CZ_PRE_NEW_VERSION" != *rc* ]]; then
    sed -i "s/git checkout [0-9][^ ]*/git checkout $CZ_PRE_NEW_VERSION/" docs/setup/deployment.md
fi
