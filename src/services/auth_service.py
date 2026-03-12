from src import get_db_connection, bcrypt
from src.models import User

def register_acc(username, email, password):
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    db = get_db_connection()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO Users (username, email, password) VALUES (%s, %s, %s)",
        (username, email, hashed_password)
    )
    db.commit()
    cur.close()
    db.close() # Always close the connection in serverless!

def get_user(user_id):
    db = get_db_connection()
    cur = db.cursor()
    cur.execute(
        "SELECT user_id, username, email, password FROM Users WHERE user_id = %s",
        (user_id,)
    )
    user = cur.fetchone()
    cur.close()
    db.close()
    return user
