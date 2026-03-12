from src import get_db_connection
from collections import defaultdict
from flask import flash
import requests

def search_movies(movie_title):
    movies = []
    if movie_title and len(movie_title) > 100:
        return None, 'Title is invalid or too long'
    if movie_title:
        response = requests.get(
            "https://imdb.iamidiotareyoutoo.com/justwatch",
            params={"q": movie_title}
        )
        result = response.json()
        if result.get("description"):
            for item in result["description"]:
                photos = item.get("photo_url", [])
                poster = photos[0] if photos else "N/A"
                movies.append({
                    "movie_title": item.get('title'),
                    "year": item.get('year'),
                    "poster": poster,
                    "runtime": item.get('runtime'),
                    "url": item.get('url')
                })
    return movies, None

def get_movies():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT movie_title, year, poster, year FROM Movies")
    movies_carousel = cur.fetchall()
    cur.close()
    conn.close()
    return movies_carousel

def get_user_recently_added(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """SELECT u.username, m.movie_title, m.year, m.runtime, m.url, m.poster, f.date_added AS added_at
           FROM Users u
           JOIN Favorites f ON u.user_id = f.user_id
           JOIN Movies m ON m.movie_id = f.movie_id
           WHERE u.user_id = %s
           UNION ALL
           SELECT u.username, m.movie_title, m.year, m.runtime, m.url, m.poster, w.date_added AS added_at
           FROM Users u
           JOIN WatchList w ON u.user_id = w.user_id
           JOIN Movies m ON m.movie_id = w.movie_id
           WHERE u.user_id = %s
           ORDER BY added_at DESC
           LIMIT 10;""", (user_id, user_id)
    )
    recent_movies = cur.fetchall()
    cur.close()
    conn.close()
    return recent_movies

def count_movies(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM Favorites WHERE user_id = %s", (user_id,))
    favorites_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM WatchList WHERE user_id = %s", (user_id,))
    watchlist_count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return {"fav_count": favorites_count, "watchlist_count": watchlist_count}

def movie_addition(user_id, add_type, movie_title, year, runtime, url, poster, folder_name):
    if add_type == "favorites":
        table, other_table = "Favorites", "WatchList"
    elif add_type == "watchlist":
        table, other_table = "WatchList", "Favorites"
    else:
        return "Invalid type!", "danger"

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT movie_id FROM Movies WHERE movie_title = %s", (movie_title,))
    movie = cur.fetchone()
    if movie:
        movie_id = movie[0]
    else:
        cur.execute(
            "INSERT INTO Movies (movie_title, year, runtime, url, poster) VALUES (%s, %s, %s, %s, %s)",
            (movie_title, year, runtime, url, poster)
        )
        conn.commit()
        movie_id = cur.lastrowid

    cur.execute(f"SELECT 1 FROM {other_table} WHERE user_id = %s AND movie_id = %s", (user_id, movie_id))
    if cur.fetchone():
        flash(f"Movie already exist in your {other_table}", "warning")
    else:
        try:
            folder_id = get_folder_id(folder_name, user_id, table)
            cur.execute(f"INSERT INTO {table} (user_id, movie_id, folder_id) VALUES (%s, %s, %s)",
                        (user_id, movie_id, folder_id))
            conn.commit()
            return f"{movie_title} added to {folder_name} in {table}!", "success"
        except:
            return f"'{movie_title}' is already in your {table}.", "warning"
    cur.close()
    conn.close()
    return None

def remove_movie(user_id, remove_from, folder_name, movie_title):
    movie_id = get_movie_id_by_title(movie_title)
    table = "Favorites" if remove_from.lower() == "favorites" else "WatchList"
    endpoint = remove_from.lower()
    folder_id = get_folder_id(folder_name, user_id, table)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {table} WHERE user_id = %s AND movie_id = %s AND folder_id = %s",
                (user_id, movie_id, folder_id))
    conn.commit()
    cur.close()
    conn.close()
    return endpoint

def get_movie_id_by_title(title):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT movie_id FROM Movies WHERE movie_title = %s", (title,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else None

def get_folder_id(name, user_id, table):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT folder_id FROM Folder WHERE folder_name = %s AND user_id = %s AND folder_type = %s",
        (name, user_id, table.lower())
    )
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else None

def create_folder(user_id, folder_name, folder_type):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO Folder (user_id, folder_name, folder_type) VALUES (%s, %s, %s)",
                    (user_id, folder_name, folder_type))
        conn.commit()
    except:
        flash("Folder name already exist!", "error")
    cur.close()
    conn.close()

def folder_deletion(user_id, table, folder_id, folder_name):
    table = "WatchList" if table.lower() == "watchlist" else table
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {table} WHERE folder_id = %s", (folder_id,))
    cur.execute("DELETE FROM Folder WHERE user_id = %s AND folder_id = %s AND folder_type = %s",
                (user_id, folder_id, table.lower()))
    conn.commit()
    cur.close()
    conn.close()

def get_grouped_folders(table, user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT f.folder_id, f.folder_name, m.poster
        FROM Folder f
        LEFT JOIN {table} t ON f.folder_id = t.folder_id
        LEFT JOIN Movies m ON t.movie_id = m.movie_id
        WHERE f.user_id = %s AND f.folder_type = %s
    """, (user_id, table.lower()))
    grouped = defaultdict(list)
    for row in cur.fetchall():
        grouped[row[1]].append(row[2])
    cur.close()
    conn.close()
    return grouped

def folder_opening(user_id, folder_name, table):
    table = "WatchList" if table.lower() == "watchlist" else table
    folder_id = get_folder_id(folder_name, user_id, table)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT m.movie_title, m.year, m.runtime, m.poster, m.url 
        FROM {table} t
        JOIN Folder f ON f.folder_id = t.folder_id
        JOIN Movies m ON m.movie_id = t.movie_id
        WHERE t.user_id = %s AND t.folder_id = %s
    """, (user_id, folder_id))
    movies = cur.fetchall()
    cur.close()
    conn.close()
    return movies
