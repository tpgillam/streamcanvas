#!/bin/bash

COUNTER=0
while :
do
  # echo "moo $COUNTER approve" 
  # let x=$(( ( RANDOM % 10 )  + 1 ))
  # let y=$(( ( RANDOM % 10 )  + 1 ))
  # let z=$(( ( RANDOM % 10 )  + 1 ))
  # let w=$(( ( RANDOM % 10 )  + 1 ))
  # let x=$(awk -v 'seed=$[(RANDOM & 32767) + 32768 * (RANDOM & 32767)]' 'BEGIN { printf("%.5f\n", rand() * 10.0) }')
  # let y=awk -v 'seed=$[(RANDOM & 32767) + 32768 * (RANDOM & 32767)]' 'BEGIN { printf("%.5f\n", rand() * 10.0) }'
  # let z=awk -v 'seed=$[(RANDOM & 32767) + 32768 * (RANDOM & 32767)]' 'BEGIN { printf("%.5f\n", rand() * 10.0) }'
  # let w=awk -v 'seed=$[(RANDOM & 32767) + 32768 * (RANDOM & 32767)]' 'BEGIN { printf("%.5f\n", rand() * 10.0) }'

  export x=$(python -c 'import random; print(random.random() * 10)')
  export y=$(python -c 'import random; print(random.random() * 10)')
  export z=$(python -c 'import random; print(random.random() * 10)')
  export w=$(python -c 'import random; print(random.random() * 10)')
  # echo "$x $y $z $w approve" 
  echo "$x $y $z $w " 
  if [ $(( $COUNTER % 50 )) -eq 0 ]; then
    echo "approve"
  fi
  # sleep 1
  let COUNTER=COUNTER+1
done

