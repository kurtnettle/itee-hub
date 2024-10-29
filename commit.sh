#!/bin/bash

if [ $(git status --porcelain | wc -l) -eq "0" ]; then
    echo "INFO: no update."
else
    echo "INFO: pushing new update"
    git config --local user.name 'github-actions[bot]'
    git config --local user.email '41898282+github-actions[bot]@users.noreply.github.com'
    git add .
    git commit -am "updated on $(date -u '+%Y-%m-%d %H:%M:%S %Z')"
    git push    
fi  