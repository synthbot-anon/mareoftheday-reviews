#!/bin/bash

docker run --rm -it -p 8000:8000 -v "$(pwd)":/host synthbot/mareoftheday-reviews --host 0.0.0.0 --port 8000