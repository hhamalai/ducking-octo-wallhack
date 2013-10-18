import datetime
import json
import os
import socket
import subprocess
import time
import sys
import settings

HOST = settings.HOST
PORT = settings.PORT
IB_SERVER_GUID = settings.IB_SERVER_GUID
TEST_TYPE = settings.TEST_TYPE


def run_suite(timestamp, suite_name, client_call, server_call, env):
    current_dir = "results/batch/%s" % datetime.datetime.strftime(timestamp, format="%Y-%m-%dT%H:%M:%S")
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
        print "terminate"
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
        logfile.write(results.get('log'))
        logfile.close()
        s.close()
    except KeyboardInterrupt:
        print "Keyboard interrupt, closing"
    except Exception as err:
        print "Exception:", err
        sys.exit(0)


def main():
    timestamp = datetime.datetime.now()
    msgsizes = [2**x for x in range(30)]
    for msgsize in msgsizes:
        run_suite(timestamp,
                  "zmq-thr-%s" % msgsize,
                  ['/root/zeromq-3.2.4/perf/remote_thr', 'tcp://%s:5555' % HOST, '%s' % msgsize, '100'],
                  ['/root/zeromq-3.2.4/perf/local_thr', 'tcp://%s:5555' % HOST, '%s' % msgsize, '100'],
                  {'LD_PRELOAD': 'libsdp.so'})

    for msgsize in msgsizes:
        run_suite(timestamp,
                  "zmq-lat-%s" % msgsize,
                  ['/root/zeromq-3.2.4/perf/remote_lat', 'tcp://%s:5555' % HOST, '%s' % msgsize, '100'],
                  ['/root/zeromq-3.2.4/perf/local_lat', 'tcp://%s:5555' % HOST, '%s' % msgsize, '100'],
                  {'LD_PRELOAD': 'libsdp.so'})



if __name__ == '__main__':
    main()
