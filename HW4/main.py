# Database class
from dbclass import InitTables, UserTable, PairTable, FriendInvite, PostTable

# Socket Server class
from server import ServerClass

# Argument Parser
import argparse
parser = argparse.ArgumentParser(description='TCP connection: ')
parser.add_argument('--host', type=str, help='server host', required=True, default='127.0.0.1')
parser.add_argument('-p', '--port', type=int, help='server port', required=True, default=3036)
args = parser.parse_args()

server = ServerClass(args.host, args.port)
