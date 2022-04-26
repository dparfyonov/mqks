#!/bin/sh
./server/mqksd  &
./server/mqksd 24001 25001 &
./server/mqksd 24002 25002