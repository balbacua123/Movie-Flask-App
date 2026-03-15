from flask import render_template, url_for, redirect, flash, request
import traceback
import logging
from src import app, mysql, bcrypt, login_manager
from flask_login import login_user, login_required, current_user, logout_user
from src.forms import RegistrationForm, LoginForm
from src.models import User
from src.services.movie_service import search_movies, get_movies, movie_addition, remove_movie, folder_deletion, count_movies, get_user_recently_added, get_movie_id_by_title, create_folder, get_folder_id, get_grouped_folders, folder_opening
from src.services.auth_service import register_acc, authenticate_user, get_user
from src.services.user_service import update_user_account


@app.route('/')
@app.route('/home')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('auth_user'))
    
    movies_carousel = get_movies()

    return render_template('layout_temp/first_page.html', title='Home', movies_carousel = movies_carousel)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    
    form = LoginForm()
    if form.validate_on_submit():
        
        user_obj = authenticate_user(form.username.data, form.password.data)

        if user_obj:
            login_user(user_obj, remember=form.remember.data)
            return redirect(url_for('auth_user'))
        else:
            flash("Login failed. Check username and password.", "danger")
    return render_template('layout_temp/login.html', title='Login', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            register_acc(form.username.data, form.email.data, form.password.data)
            flash('Your account has been created!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            logging.error(traceback.format_exc())
            flash(str(e), 'danger')
    
    return render_template('layout_temp/register.html', title='Register', form=form)


@login_manager.user_loader
def load_user(user_id):
    
    user = get_user(user_id)

    if user:
        return User(user[0], user[1], user[2], user[3])
    return None

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

    
@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():

    if request.method == 'POST':
        
        username = request.form.get('username')
        currentPassword = request.form.get('currentPassword')
        newPassword = request.form.get('newPassword')
        confirmNewPassword = request.form.get('confirmNewPassword')

        if newPassword != confirmNewPassword:
            flash('New password does not match!', 'warning')
            return redirect(url_for('account'))

        success, message = update_user_account(current_user.id, username, currentPassword, current_user.password, newPassword)

        flash(message, 'success' if success else 'warning')
        return redirect(url_for('account'))
    
    return render_template('loggedIn_temp/account.html', title='Account')


@app.route('/movies')
@login_required
def movies():

    movie_title = request.args.get("title")
    
    movie_list, error = search_movies(movie_title)

    if error:
        flash(error, 'warning')
        return redirect(url_for('movies'))

    fav_folders = get_grouped_folders("Favorites", current_user.id)
    watch_folders = get_grouped_folders("WatchList", current_user.id)

    all_folders = {
        "favorites": fav_folders,
        "watchlist": watch_folders
    }

    return render_template("loggedIn_temp/movies.html", title="Search", movie_list=movie_list or [], folders=all_folders)

@app.route('/user')
@login_required
def auth_user():
    movies_count = count_movies(current_user.id)

    recent_movies = get_user_recently_added(current_user.id)

    return render_template('loggedIn_temp/dashboard.html', title='Welcome', movies_count=movies_count, recent_movies=recent_movies)


@app.route('/add_movie/<add_type>', methods=['POST'])
@login_required
def add_movie(add_type):
    
    movie_title = request.form.get('title')
    year = request.form.get('year')
    runtime = request.form.get('runtime')
    url = request.form.get('url')
    poster = request.form.get('poster')
    folder_name = request.form.get("folder")

    message, result = movie_addition(current_user.id, add_type, movie_title, year, runtime, url, poster, folder_name)
    
    flash(message, result)

    return redirect(request.referrer)

@app.route('/favorites')
@login_required
def favorites():
    
    groupedFolder = get_grouped_folders("Favorites", current_user.id)

    return render_template('loggedIn_temp/favorites.html', title = 'Favorites', groupedFolder=groupedFolder)

@app.route('/watchlist')
@login_required
def watchlist():
    
    wgroupedFolder = get_grouped_folders("WatchList", current_user.id)

    return render_template('loggedIn_temp/watchlist.html', title = 'WatchList', wgroupedFolder=wgroupedFolder)

@app.route('/remove/<remove_from>/<folder_name>', methods=['POST'])
@login_required
def remove(remove_from, folder_name):

    movie_title = request.form.get('movie_title')

    endpoint = remove_movie(current_user.id, remove_from, folder_name, movie_title)

    flash(f"{movie_title} has been removed from {folder_name}.")
    return redirect(url_for(endpoint))

@app.route('/add_folder/<add_in>', methods=['POST'])
@login_required
def add_folder(add_in):

    folder_name = request.form.get('folder_name')

    if add_in == 'favorites':
        table = 'Favorites'
    elif add_in == 'watchlist':
        table = 'WatchList'

    create_folder(current_user.id, folder_name, table)
    folder_id = get_folder_id(folder_name, current_user.id, table)
    
    flash(f"{folder_name} has been created!", "success")

    return redirect(url_for(add_in))

@app.route('/delete_folder/<folder_name>', methods=['POST'])
@login_required
def delete_folder(folder_name):
    
    table = request.form.get('table')

    folder_id = get_folder_id(folder_name, current_user.id, table)

    folder_deletion(current_user.id, table, folder_id, folder_name)

    flash(f"{folder_name} has been deleted.", "warning")
    
    return redirect(url_for(table.lower()))


@app.route('/open_folder/<table>/<folder_name>', methods=['POST'])
@login_required
def open_folder(table, folder_name):

    movies = folder_opening(current_user.id, folder_name, table)

    return render_template('loggedIn_temp/display_movie.html', title=table.capitalize(), movies=movies, folder_name=folder_name)
