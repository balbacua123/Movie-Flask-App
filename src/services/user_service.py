from src import mysql, bcrypt

def update_user_account(user_id, username, currentPassword, current_hashed_password, newPassword):

    if not bcrypt.check_password_hash(current_hashed_password, currentPassword):
            return False, 'Current Password is Incorrect!'
    
    hashed_password = bcrypt.generate_password_hash(newPassword).decode('utf-8')

    cur = mysql.connection.cursor()
    cur.execute(
        "UPDATE Users SET username=%s, password=%s WHERE user_id=%s",
        (username, hashed_password, user_id)
    )

    mysql.connection.commit()
    cur.close()

    return True, 'Account updated successfully!'
