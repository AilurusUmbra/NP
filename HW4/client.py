import sys
import socket
import json
import os
import stomp

class Listener():
    def on_message(self, headers, msg):
        print(msg)

class UserInfo():
    def __init__(self, name, token):
        self.username = name
        self.token = token
        #self.user_sub = sub_id
        #sub_id = token
        self.group_sub = {}


class Client(object):
    def __init__(self, ip, port):
        try:
            socket.inet_aton(ip)
            if 0 < int(port) < 65535:
                self.ip = ip
                self.port = int(port)
            else:
                raise Exception('Port value should between 1~65535')
            self.cookie = {}
        except Exception as e:
            print(e, file=sys.stderr)
            sys.exit(1)

        self.username=""
        self.users={}
        self.mq = stomp.Connection([(self.ip, 61613)])
        self.mq.set_listener('', Listener())
        self.mq.connect()

    def run(self):
        while True:
            cmd = sys.stdin.readline()
            if cmd == 'exit' + os.linesep:
                return
            if cmd != os.linesep:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.connect((self.ip, self.port))
                        cmd = self.__attach_token(cmd)
                        s.send(cmd.encode())
                        resp = s.recv(4096).decode()
                        self.__show_result(json.loads(resp), cmd)
                except Exception as e:
                    print(e, file=sys.stderr)

    def __show_result(self, resp, cmd=None):
        if 'message' in resp:
            print(resp['message'])

        if 'invite' in resp:
            if len(resp['invite']) > 0:
                for l in resp['invite']:
                    print(l)
            else:
                print('No invitations')

        if 'friend' in resp:
            if len(resp['friend']) > 0:
                for l in resp['friend']:
                    print(l)
            else:
                print('No friends')

        if 'group' in resp:
            if len(resp['group']) > 0:
                for l in resp['group']:
                    print(l)
            else:
                print('No groups')

        if 'post' in resp:
            if len(resp['post']) > 0:
                for p in resp['post']:
                    print('{}: {}'.format(p['id'], p['message']))
            else:
                print('No posts')

        if cmd:
            command = cmd.split()
            if resp['status'] == 0: 
                if command[0] == 'login':
                    self.users[self.username] = UserInfo(self.username, resp['token'])
                    self.cookie[command[1]] = resp['token']
                    self.__amq_subscribe(command[1], command[1])

                elif command[0] == 'logout' or command[0] == 'delete':
                    self.__amq_user_unsub(self.users[self.username])
                    self.users.pop(self.username)

                if 'groupname' in resp:
                    print("yes has group")
                    for g in resp['groupname']:
                        print("subscribe group: ", self.username, '/topic/' + g)
                        self.users[self.username].group_sub[g] = '/topic/' + g 
                        print("no problem1")
                        self.__amq_subscribe(self.username , '/topic/' + g)
                        print("no 2")

    def __attach_token(self, cmd=None):
        if cmd:
            command = cmd.split()
            if len(command) > 1:
                self.username = command[1]
                if command[0] != 'register' and command[0] != 'login':
                    if command[1] in self.cookie:
                        command[1] = self.cookie[command[1]]
                    else:
                        command.pop(1)
            return ' '.join(command)
        else:
            return cmd

    def __amq_subscribe(self, user, ch):
        self.mq.subscribe(ch, user+ch)



    def __amq_user_unsub(self, userinfo):
        print("unsub")
        self.mq.unsubscribe(userinfo.username)
        for ele in userinfo.group_sub.values():
            self.mq.unsubscribe(userinfo.username+ele)


def launch_client(ip, port):
    c = Client(ip, port)
    c.run()

if __name__ == '__main__':
    if len(sys.argv) == 3:
        launch_client(sys.argv[1], sys.argv[2])
    else:
        print('Usage: python3 {} IP PORT'.format(sys.argv[0]))
