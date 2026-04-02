from src import mysql, app
from MySQLdb.cursors import DictCursor
from collections import defaultdict
from flask import flash
from concurrent.futures import ThreadPoolExecutor
import requests

API_TOKEN = app.config.get('API_KEY')
BASE_IMG_URL = "https://image.tmdb.org/t/p/w500"
COMING_SOON_URL = "https://img.freepik.com/free-vector/coming-soon-background-with-focus-light-effect-design_1017-27277.jpg?semt=ais_incoming&w=740&q=80"

def fetch_trailer_for_movie(item, headers):
    movie_id = item.get('id')
    if not movie_id:
        return "N/A"
        
    video_url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos"
    try:
        video_response = requests.get(video_url, headers=headers, timeout=2)
        video_response.raise_for_status()
        video_data = video_response.json().get("results", [])

        for vid in video_data:
            if vid.get("type") == "Trailer" and vid.get("site") == "YouTube":
                return f"https://www.youtube.com/watch?v={vid.get('key')}"
    except Exception:
        pass
    
    return "N/A"

def search_movies(movie_title):
    movies = []

    if not movie_title:
        return [], None

    if len(movie_title) > 100:
        return None, 'Title is invalid or too long'
    
    url = "https://api.themoviedb.org/3/search/movie"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {API_TOKEN}"
    }
    params = {"query": movie_title}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        result = response.json()
        movie_results = result.get("results", [])
    except Exception as e:
        return None, f"Search failed: {str(e)}"

    if not movie_results:
        return [], None

 
    with ThreadPoolExecutor(max_workers=10) as executor:
        trailer_links = list(executor.map(lambda item: fetch_trailer_for_movie(item, headers), movie_results))

    for item, trailer_link in zip(movie_results, trailer_links):
        poster_path = item.get("poster_path")
        full_poster = BASE_IMG_URL + poster_path if poster_path else COMING_SOON_URL

        release_date = item.get('release_date')
        year = release_date[:4] if release_date else "N/A"

        movies.append({
            "movie_title": item.get('title'),
            "year": year,
            "poster": full_poster,
            "overview": item.get('overview'),
            "original_language": item.get('original_language'),
            "trailer": trailer_link,
        })

    return movies, None

def get_movies():

    cur = mysql.connection.cursor(DictCursor)
    cur.execute(
        "SELECT movie_title, year, poster, year FROM Movies"
    )
    movies_carousel = cur.fetchall()
    cur.close()

    return movies_carousel

def get_user_recently_added(user_id):

    cur = mysql.connection.cursor(DictCursor)
    cur.execute(
        """SELECT u.username, m.movie_title, m.year, m.original_language, m.trailer, m.poster, f.date_added AS added_at
            FROM Users u
            JOIN Favorites f ON u.user_id = f.user_id
            JOIN Movies m ON m.movie_id = f.movie_id
            WHERE u.user_id = %s

            UNION ALL

            SELECT u.username, m.movie_title, m.year, m.original_language, m.trailer, m.poster, w.date_added AS added_at
            FROM Users u
            JOIN WatchList w ON u.user_id = w.user_id
            JOIN Movies m ON m.movie_id = w.movie_id
            WHERE u.user_id = %s

            ORDER BY added_at DESC
            LIMIT 10;""", (user_id, user_id)
    )

    recent_movies = cur.fetchall()
    cur.close()

    return recent_movies


def count_movies(user_id):

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM Favorites WHERE user_id = %s",
        (user_id,)
    )
    favorites_count = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM WatchList WHERE user_id = %s",
        (user_id,)
    )
    watchlist_count = cur.fetchone()[0]

    return {"fav_count": favorites_count, "watchlist_count": watchlist_count}

def movie_addition(user_id, add_type, movie_title, year, overview, original_language, trailer, poster, folder_name):
    valid_tables = {"favorites": "Favorites", "watchlist": "WatchList"}
    if add_type not in valid_tables:
        return "Invalid type!", "danger"
    
    table = valid_tables[add_type]
    other_table = "WatchList" if table == "Favorites" else "Favorites"

    cur = mysql.connection.cursor()
    try:
        cur.execute("SELECT movie_id FROM Movies WHERE movie_title = %s AND year = %s", (movie_title, year))
        movie = cur.fetchone()

        if movie:
            movie_id = movie[0]
        else:
            cur.execute(
                "INSERT INTO Movies (movie_title, year, overview, original_language, trailer, poster) VALUES (%s, %s, %s, %s, %s, %s)",
                (movie_title, year, overview, original_language, trailer, poster)
            )
            mysql.connection.commit()
            movie_id = cur.lastrowid

        cur.execute(f"SELECT 1 FROM {other_table} WHERE user_id = %s AND movie_id = %s", (user_id, movie_id))
        if cur.fetchone():
            return f"Movie already exists in your {other_table}", "warning"

        folder_id = get_folder_id(folder_name, user_id, table)
        if not folder_id:
             return "Folder not found", "danger"

        cur.execute(f"INSERT INTO {table} (user_id, movie_id, folder_id) VALUES (%s, %s, %s)", (user_id, movie_id, folder_id))
        mysql.connection.commit()
        return f"{movie_title} added successfully!", "success"

    except Exception as e:
        mysql.connection.rollback()
        return f"Error: {str(e)}", "danger"
    finally:
        cur.close()
        

def remove_movie(user_id, remove_from, folder_name, movie_title):

    movie_id = get_movie_id_by_title(movie_title)

    if remove_from.lower() == 'favorites':
        table = "Favorites"
        endpoint = "favorites"
    elif remove_from.lower() == 'watchlist':
        table = "WatchList"
        endpoint = "watchlist"

    folder_id = get_folder_id(folder_name, user_id, table)

    cur = mysql.connection.cursor()
    cur.execute(
        f"DELETE FROM {table} WHERE user_id = %s AND movie_id = %s AND folder_id = %s",
        (user_id, movie_id, folder_id)
    )
    mysql.connection.commit()
    cur.close()

    return endpoint


def get_movie_id_by_title(title):
    cur = mysql.connection.cursor()
    cur.execute("SELECT movie_id FROM Movies WHERE movie_title = %s", (title,))
    result = cur.fetchone()
    cur.close()
    
    return result[0] if result else None

def get_folder_id(name, user_id, table):

    if table.lower() == "watchlist":
        table = "WatchList"
    
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT folder_id FROM Folder WHERE folder_name = %s AND user_id = %s AND folder_type = %s",
        (name, user_id, table.lower())
    )
    result = cur.fetchone()
    cur.close()
    return result[0] if result else None

def create_folder(user_id, folder_name, folder_type):
    
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO Folder (user_id, folder_name, folder_type) VALUES (%s, %s, %s)",
            (user_id, folder_name, folder_type)
        )
        mysql.connection.commit()
        cur.close()
    except Exception as e:
        flash("Folder name already exist!", "error")

def folder_deletion(user_id, table, folder_id, folder_name):

    if table.lower() == "watchlist":
        table = "WatchList"

    cur = mysql.connection.cursor()
    cur.execute(f"DELETE FROM {table} WHERE folder_id = %s", (folder_id,))
    cur.execute("DELETE FROM Folder WHERE user_id = %s AND folder_id = %s AND folder_type = %s", (user_id, folder_id, table.lower()))
    
    mysql.connection.commit()
    cur.close()

def get_grouped_folders(table, user_id):
    cur = mysql.connection.cursor(DictCursor)
    cur.execute(f"""
        SELECT f.folder_id, f.folder_name, m.poster
        FROM Folder f
        LEFT JOIN {table} t ON f.folder_id = t.folder_id
        LEFT JOIN Movies m ON t.movie_id = m.movie_id
        WHERE f.user_id = %s AND f.folder_type = %s
    """, (user_id, table.lower()))

    grouped = defaultdict(list)
    for row in cur.fetchall():
        grouped[row['folder_name']].append(row['poster'])

    cur.close()
    return grouped

def folder_opening(user_id, folder_name, table):

    if table.lower() == "watchlist":
        table = "WatchList"

    folder_id = get_folder_id(folder_name, user_id, table)

    cur = mysql.connection.cursor(DictCursor)
    cur.execute(f"SELECT m.movie_title, m.year, m.original_language, m.poster, m.trailer FROM {table} t " \
    "JOIN Folder f ON f.folder_id = t.folder_id " \
    "JOIN Movies m  ON m.movie_id = t.movie_id " \
    "WHERE t.user_id = %s AND t.folder_id = %s", (user_id, folder_id))

    movies = cur.fetchall()
    cur.close()

    return movies