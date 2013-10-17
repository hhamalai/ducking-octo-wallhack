import datetime
import json
import os
import socket
import subprocess
import time

import settings

HOST = settings.HOST
PORT = settings.PORT
IB_SERVER_GUID = settings.IB_SERVER_GUID
TEST_TYPE = settings.TEST_TYPE

TEST_SUITE_CLOCK_OFFSET = {
    'vm': 0,
    'node': 15,
}

ENABLED_VM_TESTS = set(['iperf', 'ping', 'zeromq-thr', 'zeromq-lat',
    'zeromq-thr-16', 'zeromq-lat-16', 'zeromq-thr-65536', 'zeromq-lat-65536'])

ENABLED_NODE_TESTS = set(['iperf', 'ping', 'iperf-sdp', 'zeromq-thr', 'zeromq-thr-sdp', 'zeromq-lat',
        'zeromq-lat-sdp', 'zeromq-thr-16', 'zeromq-thr-sdp-16', 'zeromq-lat-16',
        'zeromq-lat-sdp-16', 'zeromq-thr-65536', 'zeromq-thr-sdp-65536',
        'zeromq-lat-65536', 'zeromq-lat-sdp-65536', 'ibping', 'ib_read_lat'])

all_test_suites = [{
               'name': 'iperf',
               'client_call': ["iperf", "-c", HOST],
               'server_call': ["iperf", "-s"],
               'env': {}
               },
               {
               'name': 'ping',
               'client_call': ["ping", "-c", "50", "-w", "300", "-i", "0.25", "-W", "5", HOST],
               'server_call': ["ping", "-c", "50", "-w", "300", "-i", "0.25", "-W", "5", HOST],
               'env': {}
               },
               {
               'name': 'iperf-sdp',
               'client_call': ["iperf", "-c", HOST],
               'server_call': ["iperf", "-s"],
               'env': {'LD_PRELOAD': 'libsdp.so'}
               },
               {
               'name': 'zeromq-thr',
               'client_call': ['/root/zeromq3-x/perf/remote_thr', 'tcp://%s:5555' % HOST, '1024', '100'],
               'server_call': ['/root/zeromq3-x/perf/local_thr', 'tcp://%s:5555' % HOST, '1024', '100'],
               'env': {}
               },
               {
               'name': 'zeromq-thr-sdp',
               'client_call': ['/root/zeromq3-x/perf/remote_thr', 'tcp://%s:5555' % HOST, '1024', '100'],
               'server_call': ['/root/zeromq3-x/perf/local_thr', 'tcp://%s:5555' % HOST, '1024', '100'],
               'env': {'LD_PRELOAD': 'libsdp.so'}
               }, 
               {
               'name': 'zeromq-lat',
               'client_call': ['/root/zeromq3-x/perf/remote_lat', 'tcp://%s:5555' % HOST, '1024', '100'],
               'server_call': ['/root/zeromq3-x/perf/local_lat', 'tcp://%s:5555' % HOST, '1024', '100'],
               'env': {}
               },
               {
               'name': 'zeromq-lat-sdp',
               'client_call': ['/root/zeromq3-x/perf/remote_lat', 'tcp://%s:5555' % HOST, '1024', '100'],
               'server_call': ['/root/zeromq3-x/perf/local_lat', 'tcp://%s:5555' % HOST, '1024', '100'],
               'env': {'LD_PRELOAD': 'libsdp.so'}
               }, 
               {
               'name': 'zeromq-thr-16',
               'client_call': ['/root/zeromq3-x/perf/remote_thr', 'tcp://%s:5555' % HOST, '16', '100'],
               'server_call': ['/root/zeromq3-x/perf/local_thr', 'tcp://%s:5555' % HOST, '16', '100'],
               'env': {}
               },
               {
               'name': 'zeromq-thr-sdp-16',
               'client_call': ['/root/zeromq3-x/perf/remote_thr', 'tcp://%s:5555' % HOST, '16', '100'],
               'server_call': ['/root/zeromq3-x/perf/local_thr', 'tcp://%s:5555' % HOST, '16', '100'],
               'env': {'LD_PRELOAD': 'libsdp.so'}
               }, 
               {
               'name': 'zeromq-lat-16',
               'client_call': ['/root/zeromq3-x/perf/remote_lat', 'tcp://%s:5555' % HOST, '16', '100'],
               'server_call': ['/root/zeromq3-x/perf/local_lat', 'tcp://%s:5555' % HOST, '16', '100'],
               'env': {}
               },
               {
               'name': 'zeromq-lat-sdp-16',
               'client_call': ['/root/zeromq3-x/perf/remote_lat', 'tcp://%s:5555' % HOST, '16', '100'],
               'server_call': ['/root/zeromq3-x/perf/local_lat', 'tcp://%s:5555' % HOST, '16', '100'],
               'env': {'LD_PRELOAD': 'libsdp.so'}
               }, 
               {
               'name': 'zeromq-thr-65536',
               'client_call': ['/root/zeromq3-x/perf/remote_thr', 'tcp://%s:5555' % HOST, '65536', '100'],
               'server_call': ['/root/zeromq3-x/perf/local_thr', 'tcp://%s:5555' % HOST, '65536', '100'],
               'env': {}
               },
               {
               'name': 'zeromq-thr-sdp-65536',
               'client_call': ['/root/zeromq3-x/perf/remote_thr', 'tcp://%s:5555' % HOST, '65536', '100'],
               'server_call': ['/root/zeromq3-x/perf/local_thr', 'tcp://%s:5555' % HOST, '65536', '100'],
               'env': {'LD_PRELOAD': 'libsdp.so'}
               }, 
               {
               'name': 'zeromq-lat-65536',
               'client_call': ['/root/zeromq3-x/perf/remote_lat', 'tcp://%s:5555' % HOST, '65536', '100'],
               'server_call': ['/root/zeromq3-x/perf/local_lat', 'tcp://%s:5555' % HOST, '65536', '100'],
               'env': {}
               },
               {
               'name': 'zeromq-lat-sdp-65536',
               'client_call': ['/root/zeromq3-x/perf/remote_lat', 'tcp://%s:5555' % HOST, '65536', '100'],
               'server_call': ['/root/zeromq3-x/perf/local_lat', 'tcp://%s:5555' % HOST, '65536', '100'],
               'env': {'LD_PRELOAD': 'libsdp.so'}
               },
               {
               'name': 'ibping',
               'client_call': ['/usr/sbin/ibping', '-G', IB_SERVER_GUID, "-c", "10"],
               'server_call': ['/usr/sbin/ibping', '-S'],
               'env': {}
               },
               {
               'name': 'ib_read_lat',
               'client_call': ['/usr/bin/ib_read_lat', '-C', HOST, '-a'],
               'server_call': ['/usr/bin/ib_read_lat', '-C', '-a'],
               'env': {}
               },
]

enabled = []
if TEST_TYPE == 'vm':
    enabled = ENABLED_VM_TESTS
elif TEST_TYPE == 'node':
    enabled = ENABLED_NODE_TESTS
assert enabled
test_suites = [x for x in all_test_suites if x.get('name') in enabled]


def run_suite(timestamp, suite_name, client_call, server_call, env):
        current_dir = "results/%s" % datetime.datetime.strftime(timestamp, format="%Y-%m-%dT%H:%M:%S")
        try:
            os.mkdir(current_dir)
        except OSError:
            pass

        try:
            print "running suite..."
            server_program = server_call[0]
            server_args = server_call[1:]
            status = None
            while status != 'ok':
                print "connecting..."
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((HOST, PORT))
                s.sendall(json.dumps({"cmd": "start",
                                      "program": server_program,
                                      "args": server_args,
                                      "env": env}))
                response = json.loads(s.recv(8192))
                print response
                status = response.get('status')
                if status == 'error':
                    if response.get('code') == 'busy':
                        print "busy, waiting"
                        s.close()
                        time.sleep(10)
                    else:
                        print response
                        raise Exception

            time.sleep(5)
            logfile = file("%s/%s-client.log" % (current_dir, suite_name), "w", 0)
            logfile.write("#%s\n#%s\n\n" % (client_call, env))
            os.fsync(logfile)

            p = subprocess.Popen(client_call, stdout=logfile, env=env)
            p.wait()
            logfile.close()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            s.sendall(json.dumps({"cmd": "terminate"}))
            logfile = file("%s/%s-server.log" % (current_dir, suite_name), "w", 0)
            resp = ""
            while True:
                partial = s.recv(1024)
                if not partial:
                    break
                resp = resp + partial
                print resp
            results = json.loads(resp)
            print "outcome:",
            print results.get('status')
            logfile.write(results.get('log'))
            logfile.close()
            s.close()
        except KeyboardInterrupt:
            print "Keyboard interrupt, closing"
        except Exception as err:
            print err


def main():
    prev_hour = None
    while True:
        timestamp = datetime.datetime.now()
        if timestamp.hour != prev_hour:
            if timestamp.minute > TEST_SUITE_CLOCK_OFFSET[TEST_TYPE]:
                prev_hour = timestamp.hour
                for suite in test_suites:
                    run_suite(timestamp, suite.get('name'), suite.get('client_call'), suite.get('server_call'), suite.get('env'))
        time.sleep(10)


if __name__ == '__main__':
    main()
