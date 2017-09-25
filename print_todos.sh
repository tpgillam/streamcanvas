#!/bin/bash
grep -rni 'TODO\|FIXME' streamcanvas/*.py *.py
echo
echo 'Contents of TODO:'
cat TODO
