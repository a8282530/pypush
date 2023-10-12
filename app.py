# coding: utf-8
from urllib3 import disable_warnings
from base64 import b64encode
from cryptography.fernet import Fernet
from emulated.nac import generate_validation_data
import apns
import ids

disable_warnings()

def encrypt(message):
    cipher_suite = Fernet(key = b'msD2gIlzrmg6iQ9E-RPN8Nz4A2vpqoFu3QEZ3UbEFuI=')
    return cipher_suite.encrypt(message.encode()).decode()

def decrypt(encrypted_text):
    cipher_suite = Fernet(key = b'msD2gIlzrmg6iQ9E-RPN8Nz4A2vpqoFu3QEZ3UbEFuI=')
    return cipher_suite.decrypt(encrypted_text).decode()

def userlogin(user:str, pwd:str)->(apns.APNSConnection, ids.IDSUser):
    conn = apns.APNSConnection(None, None)
    conn.connect(token=None)
    conn.set_state(1)
    conn.filter(["com.apple.madrid"])
    users = ids.IDSUser(conn)
    users.authenticate(user, pwd)
    users.encryption_identity = ids.identity.IDSIdentity(None, None)
    vd = generate_validation_data()
    vd = b64encode(vd).decode()
    users.register(vd)
    # im = imessage.iMessageUser(conn, user)
    # print(users.user_id)
    return conn,users
if __name__ == '__main__':
    _,user = userlogin('hmthsdk@hotmail.com', 'Qa221123')
    l = ['tel:+8617706336930', 'tel:+13473571632', 'tel:+13473571765', 'tel:+13473571105', 'tel:+13473571470']
    res = user.lookup(l)
    print(res)