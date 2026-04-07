from flask import Flask
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from dotenv import load_dotenv
load_dotenv()
import os
import asyncio


app = Flask(__name__, template_folder='templates')

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['API_TOKEN'] = os.getenv('API_TOKEN')

 
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')
app.config['MYSQL_PORT'] = 27397
app.config['MYSQL_SSL_CA'] = os.getenv('MYSQL_SSL_CA', None)
app.config['MYSQL_SSL_VERIFY_CERT'] = False

mysql = MySQL(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"

from src import routes
