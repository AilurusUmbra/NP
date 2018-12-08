import socket
import json
import hashlib
from uuid import uuid4
from peewee import *

# Database class
from dbclass import InitTables, UserTable, PairTable, FriendInvite, PostTable


class ServerClass:
    def __init__(self, HOST, PORT):
        InitTables([UserTable, PairTable, FriendInvite, PostTable])

        self.host = HOST
        self.port = PORT
        self.command = ''
        self.cmdsplit = []
        self.func_mapping = {
            # no exit in server
            'register': self.register,
            'login': self.login,

            'logout': self.logout,
            'delete': self.delete,
            'invite': self.invite,
            'list-invite': self.listInvite,
            'accept-invite': self.acceptInvite,
            'list-friend': self.listFriend,

            'post': self.post,
            'receive-post': self.recvPost,
        }
        while True:
            self.connectTCP()

    def connectTCP(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ss:
            ss.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            ss.bind((self.host, self.port))
            ss.listen(1)
            client, clientIP = ss.accept()
            with client:
                print('==========')
                print('Connected by: ', clientIP)
                self.command = client.recv(1024).decode()
                print('Received: ', self.command)
                client.sendall(self.cmdSpliting().encode('UTF-8'))

    def Response(self, status, message = '',
                    token = '', post = '', friend = '', invite = ''):
        resp = {'status': status}
        if token:
            resp['token'] = token
        if message:
            resp['message'] = message
        if self.cmdsplit[0] == 'receive-post' and not status:
            resp['post'] = post
        if self.cmdsplit[0] == 'list-invite' and not status:
            resp['invite'] = invite
        if self.cmdsplit[0] == 'list-friend' and not status:
            resp['friend'] = friend

        return json.dumps(resp)

    def createToken(self):
        return uuid4().hex

    def checkToken(self, token):
        user = UserTable.select().where(UserTable.token == token)
        if not user:
            print('WRONG: Not login yet')
            return None
        if len(user) > 1:
            print('MULTIPLE USER: Multiple users')
        return user[0]

    def searchFriend(self, user):
        return PairTable.select(PairTable, UserTable).join(UserTable).where(
            PairTable.friend_1 == user or
            PairTable.friend_2 == user)

    def cmdSpliting(self):
        self.cmdsplit = self.command.split(' ')
        return self.func_mapping.get(self.cmdsplit[0], self.exception)()

    def exception(self):
        print('WRONG: Unknown Command')
        return self.Response(1, message = 'Unknown command '+self.cmdsplit[0])

    def register(self):
        print('COMMAND: register')
        # Usage Error
        if len(self.cmdsplit) != 3:
            print('WRONG: Usage error')
            return self.Response(1, message = 'Usage: register <id> <password>')

        username, password = self.cmdsplit[1:3]
        print('Create user: {0}, {1}'.format(username, password))

        # Check existed user
        if(UserTable.select().where(UserTable.username == username)):
            print('WRONG: Username used')
            return self.Response(1, message = username + ' is already used')

        # Create user to UserTable
        UserTable.create(
            username = username,
            password = hashlib.sha256(password.encode('UTF-8')).hexdigest()
            )
        print('SUCCESS')
        return self.Response(0, message = 'Success!')

    def login(self):
        print('COMMAND: login')
        # Usage Error
        if len(self.cmdsplit) != 3:
            print('WRONG: Usage error')
            return self.Response(1, message = 'Usage: login <id> <password>')

        username, password = self.cmdsplit[1:3]
        print('Login user: {0}, {1}'.format(username, password))

        # Check user
        user = UserTable.select().where(UserTable.username == username)
        if not user:
            print('WRONG: No such user')
            return self.Response(1, message = 'No such user or password error')
        if len(user) != 1:
            print('MULTIPLE USER: Multiple users')
        user = user[0]

        # Check password
        if hashlib.sha256(password.encode('UTF-8')).hexdigest() != user.password:
            print('WRONG: Password error')
            return self.Response(1, message ='No such user or password error')

        # Create and send Token
        if(not user.token):
            user.token = self.createToken()
            user.save()
        print('SUCCESS: token = ' + user.token)
        return self.Response(
            0,
            token = user.token,
            message = 'Success!')

    def delete(self):
        print('COMMAND: delete')
        try:
            token = self.cmdsplit[1]
        except:
            token = ''

        # Check if user exitsted
        user = self.checkToken(token)
        if not user:
            return self.Response(1, message = 'Not login yet')

        # Usage Error
        if len(self.cmdsplit) != 2:
            print('WRONG: Usage error')
            return self.Response(1, message = 'Usage: delete <user>')

        # Delete user-related data
        user.delete_instance(recursive = True)
        print('SUCCESS')
        return self.Response(0, message = 'Success!')

    def logout(self):
        print('COMMAND: logout')
        try:
            token = self.cmdsplit[1]
        except:
            token = ''

        # Check user
        user = self.checkToken(token)
        if not user:
            return self.Response(1, message = 'Not login yet')

        # Usage Error
        if len(self.cmdsplit) != 2:
            print('WRONG: Usage error')
            return self.Response(1, message = 'Usage: logout <user>')


        # Clear token
        user.token = None
        user.save()
        print('SUCCESS')
        return self.Response(0, message = 'Bye!')

    def invite(self):
        print('COMMAND: invite')
        try:
            sender_token = self.cmdsplit[1]
        except:
            sender_token = ''

        # Check sender token
        sender = self.checkToken(sender_token)
        if not sender:
            print('WRONG: Not login yet')
            return self.Response(1, message = 'Not login yet')

        # Usage error
        if len(self.cmdsplit) != 3:
            print('WRONG: Usage error')
            return self.Response(1, message = 'Usage: invite <user> <id>')


        recver_name = self.cmdsplit[2]
        # Check receiver
        recver = UserTable.select().where(UserTable.username == recver_name)
        if not recver:
            print('WRONG: No such recver ')
            return self.Response(1, message = recver_name + ' does not exist')
        recver = recver[0]

        # Who is receiver?
        if recver == sender:
            print('WRONG: Invite self')
            return self.Response(1, message = 'You cannot invite yourself')

        # Already friend?
        is_sender_smaller = sender.id < recver.id
        friends = sender.friends_1 if is_sender_smaller else sender.friends_2
        for pair in friends:
            tar = pair.friend_2 if is_sender_smaller else pair.friend_1
            if tar == recver:
                print('WRONG: Already friends')
                return self.Response(
                    1,
                    message = recver.username + ' is already your friend'
                )

        # Already invited?
        old_invites = sender.send_invites
        for invite in old_invites:
            if invite.receiver == recver:
                print('WRONG: Already invited')
                return self.Response(1, message = 'Already invited')

        # Already received?
        old_invites = sender.recv_invites
        for invite in old_invites:
            if invite.sender == recver:
                print('WRONG: Already received invitation')
                return self.Response(
                    1,
                    message = recver.username + ' has invited you'
                )

        FriendInvite.create(sender = sender, receiver = recver)
        print('SUCCESS')
        return self.Response(0, message = 'Success!')

    def listInvite(self):
        print('COMMAND: listInvite')
        # Check user
        try:
            user = self.checkToken(self.cmdsplit[1])
        except:
            user = None

        if not user:
            print('WRONG: Not login yet')
            return self.Response(1, message='Not login yet')

        # Usage error
        if len(self.cmdsplit) != 2:
            print('WRONG: Usage error')
            return self.Response(1, message='Usage: list-invite <user>')

        # List
        invites = list(map(lambda x:x.sender.username, user.recv_invites))
        print('SUCCESS')
        return self.Response(0, invite=invites)

    def acceptInvite(self):
        print('COMMAND: acceptInvite')
        try:
            token = self.cmdsplit[1]
        except:
            token = ''

        # Check UserTable
        user = self.checkToken(token)
        if not user:
            print('WRONG: Not login yet')
            return self.Response(1, message='Not login yet')

        # Usage error
        if len(self.cmdsplit) != 3:
            print('WRONG: Usage error')
            return self.Response(1, message='Usage: accept-invite <user> <id>')

        sender_name = self.cmdsplit[2]
        # Check if invited
        invite = FriendInvite.select().where(
            FriendInvite.sender.username == sender_name
            and FriendInvite.receiver == user
        )
        if not invite:
            print('WRONG: Not invited')
            return self.Response(1, message=sender_name+' did not invite you')
        invite = invite[0]
        sender = invite.sender

        # Create friend and Remove invitation
        if sender.id < user.id:
            PairTable.create(friend_1=sender, friend_2=user)
        else:
            PairTable.create(friend_1=user, friend_2=sender)
        invite.delete_instance()
        print('SUCCESS')
        return self.Response(0, message='Success!')

    def listFriend(self):
        print('COMMAND: listFriend')
        # Check token
        try:
            user = self.checkToken(self.cmdsplit[1])
        except:
            user = None
        if not user:
            print('WRONG: Not login yet')
            return self.Response(1, message = 'Not login yet')

        # Usage error
        if len(self.cmdsplit) != 2:
            print('WRONG: Usage error')
            return self.Response(1, message = 'Usage: list-friend <user>')

        # List
        friends = list(map(lambda x: x.friend_2.username, user.friends_1))\
            + list(map(lambda x: x.friend_1.username, user.friends_2))
        print('SUCCESS')
        return self.Response(0, friend=friends)

    def post(self):
        print('COMMAND: post')
        # Check token
        try:
            user = self.checkToken(self.cmdsplit[1])
        except:
            user = None
        if not user:
            print('WRONG: Not login yet')
            return self.Response(1, message='Not login yet')

        # Usage error
        if len(self.cmdsplit) < 3:
            print('WRONG: Usage error')
            return self.Response(1, message = 'Usage: post <user> <message>')

        # Create post
        PostTable.create(user = user, text = ' '.join(self.cmdsplit[2:]))
        print('SUCCESS')
        return self.Response(0, message = 'Success!')

    def recvPost(self):
        print('COMMAND: recvPost')
        # Check token
        try:
            user = self.checkToken(self.cmdsplit[1])
        except:
            user = None
        if not user:
            print('WRONG: Not login yet')
            return self.Response(1, message = 'Not login yet')

        # Usage error
        if len(self.cmdsplit) != 2:
            print('WRONG: Usage error')
            return self.Response(1, message = 'Usage: receive-post <user>')

        # List
        friends = list(map(lambda x: x.friend_2, user.friends_1))\
            + list(map(lambda x: x.friend_1, user.friends_2))
        posts = []
        for f in friends:
            for post in f.posts:
                posts.append(
                    {
                        'id': f.username,
                        'message': post.text
                    }
                )
        print('SUCCESS: {0} posts'.format(len(posts)))
        return self.Response(0, post=posts)

