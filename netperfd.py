import sys
import os
import json
import socket
import signal
import time
import threading
from multiprocessing import Lock
import settings

HOST = settings.HOST
PORT = settings.PORT

child_pid = None

def test_start(program, args=None, env={}):
    global child_pid
    pid = os.fork()
    if pid == 0:
        try:
            if not args:
                args = [program]
            else:
                args = [program] + args
            stdout = open('/tmp/test_out', 'w', 0)
            stdout.write("#%s\n#%s\n#%s\n\n" % (program, args, env))
            sys.stdout.flush()
            os.dup2(stdout.fileno(), sys.stdout.fileno())
            os.execvpe(program, args, env)
            time.sleep(10)
        except Exception as err:
            print "Exception", err
        finally:
            sys.exit()
    child_pid = pid


def test_terminate():
    global child_pid
    if not child_pid:
        print "nothing to terminate"
        return
    print "terminating", child_pid
    os.kill(child_pid, signal.SIGINT)
    os.wait()
    child_pid = None





class PassiveTestEndpoint(object):
    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((HOST, PORT))
        self.s.listen(1)
        self.mutex = Lock()

    def loop(self):
        while True:
            conn, addr = self.s.accept()
            print addr, 'connected'
            self.handle_read(conn)

    def handle_read(self, s):
        data = None
        try:
            resp = s.recv(8192)
            if not resp:
                return
            data = json.loads(resp)
        except OSError: pass
        if data:
            cmd = data.get('cmd')
            if cmd == "start":
                self.mutex.acquire()
                program = data.get('program')
                args = data.get('args')
                env = data.get('env')
                if not child_pid:
                    print "now running", program, args
                    test_start(program, args, env)
                    s.sendall(json.dumps({'status': 'ok'}))
                else:
                    s.sendall(json.dumps({'status': 'error',
                                          'code': 'busy',
                                          'errmsg': 'test (%s) stillrunning ' % child_pid}))
                s.close()
                self.mutex.release()
            elif cmd == "terminate":
                self.mutex.acquire()
                print "terminate"
                if not child_pid:
                    s.sendall(json.dumps({'status': 'error',
                                             'code': 'no_child',
                                             'errmsg': 'nothing to terminate'}))
                else:
                    test_terminate()
                    log_content = file('/tmp/test_out', 'r').read()
                    s.sendall(json.dumps({'status': 'ok', 'log': log_content}))
                s.close()
                self.mutex.release()

def main():
    try:
        pte = PassiveTestEndpoint()
        pte.loop()
    except KeyboardInterrupt:
        print "closing"

if __name__ == '__main__':
    main()
