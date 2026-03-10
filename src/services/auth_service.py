from src import mysql, bcrypt
from src.models import User

def register_acc(username, email, password):

    hashed_password =  bcrypt.generate_password_hash(password).decode('utf-8')

    cur = mysql.connection.cursor()
    cur.execute(
        "INSERT INTO Users (username, email, password) VALUES (%s, %s, %s)",
        (username, email, hashed_password)
        )
    mysql.connection.commit()
    cur.close()

def check_acc(username):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM Users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()

    return user

def authenticate_user(username, password):

    user_data = check_acc(username)

    if user_data and bcrypt.check_password_hash(user_data[4], password):
        return User(user_data[0], user_data[1], user_data[2], user_data[3])
    return None

def get_user(user_id):

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT user_id, username, email, password FROM Users WHERE user_id = %s",
        (user_id,)
    )
    user = cur.fetchone()
    cur.close()

    return user