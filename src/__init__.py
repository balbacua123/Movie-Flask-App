from flask import Flask
import pymysql
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__, template_folder='templates')
app.config["SECRET_KEY"] = os.getenv('SECRET_KEY')

def get_db_connection():
    return pymysql.connect(
        host=os.getenv('MYSQL_HOST'),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DB'),
        port=27397,
        ssl={'ca': os.getenv('MYSQL_SSL_CA')} if os.getenv('MYSQL_SSL_CA') else None,
        cursorclass=pymysql.cursors.DictCursor
    )

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"

from . import routes

