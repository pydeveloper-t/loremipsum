#!/bin/bash
host=$1
port=$2
mkdir loremipsum
cd loremipsum
sudo apt-get install git
git clone https://github.com/pydeveloper-t/loremipsum.git .
pip3 install virtualenv
virtualenv venv
source ./venv/bin/activate
pip3 install -r requirements.txt
uvicorn lorem_generator:app --host $host --port $port &
server_pid=$!
echo "$server_pid"
python3 client_app.py --host $host --port $port
kill $server_pid
deactivate
exit

