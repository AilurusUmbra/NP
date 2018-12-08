from peewee import *

mysql_db = MySQLDatabase(
    'NP3',
    user='ailurus',
    passwd='c2727283',
    host='127.0.0.1',
    port=3306
)


def InitTables(tablelist):
    mysql_db.connect()
    mysql_db.create_tables(tablelist)


class BaseModel(Model):
    class Meta:
        database = mysql_db


class UserTable(BaseModel):
    # Charfield is varchar in MySQL
    username = CharField(unique=True)
    token = CharField(null=True)
    password = CharField()


class PairTable(BaseModel):
    friend_1 =ForeignKeyField(UserTable, related_name='friends_1', on_delete='CASCADE')
    friend_2 =ForeignKeyField(UserTable, related_name='friends_2', on_delete='CASCADE')


class FriendInvite(BaseModel):
    receiver = ForeignKeyField(UserTable, related_name='recv_invites', on_delete='CASCADE')
    sender = ForeignKeyField(UserTable, related_name='send_invites', on_delete='CASCADE')


class PostTable(BaseModel):
    user = ForeignKeyField(UserTable, related_name='posts', on_delete='CASCADE')
    text = TextField()

