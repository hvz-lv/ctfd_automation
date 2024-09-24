import sys
import os

# Adjust the Python path to include CTFd module directory
sys.path.append('/opt/CTFd')  # Update this path if necessary

from CTFd.models import UserTokens, db

import os
import binascii
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

def hexencode(data):
    return binascii.hexlify(data).decode('utf-8')

DATABASE_URL = "mysql+pymysql://ctfd:ctfd@db:3306/ctfd"
engine = create_engine(DATABASE_URL)
db_session = scoped_session(sessionmaker(bind=engine))

def generate_user_token(user_id, expiration=None, description=None):
    temp_token = True
    while temp_token is not None:
        value = "ctfd_" + hexencode(os.urandom(32))
        temp_token = db_session.query(UserTokens).filter_by(value=value).first()

    token = UserTokens(
        user_id=user_id, expiration=expiration, description=description, value=value
    )
    db_session.add(token)
    db_session.commit()
    return token

if __name__ == "__main__":
    user_id = 1  # Replace with the actual user ID
    token = generate_user_token(user_id)
    print(f"Generated Token: {token.value}")

