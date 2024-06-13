from flask import Flask, render_template, redirect, url_for, request, session, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from flask_cors import CORS
from dotenv import load_dotenv
import psycopg2

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
CORS(app)

# Spotify OAuth configuration
sp_oauth = SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback"),
    scope="playlist-read-private user-library-read"
)

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn

@app.route('/')
def index():
    return "Welcome to Spotify Data Visualizer! Go to /login to authenticate with Spotify."

@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect(url_for('get_playlists'))

@app.route('/playlists')
def get_playlists():
    token = session.get('token_info')
    if token is None:
        return "Session error"

    sp_user = spotipy.Spotify(auth=token['access_token'])
    playlists = sp_user.current_user_playlists()
    return render_template('playlists.html', playlists=playlists['items'])

@app.route('/tracks', methods=['POST'])
def get_tracks():
    token = session.get('token_info')
    if token is None:
        return "Session error"

    playlist_id = request.form['playlist_id']

    sp_user = spotipy.Spotify(auth=token['access_token'])
    tracks = sp_user.playlist_tracks(playlist_id)

    # Process tracks and store in database
    track_info = []
    conn = get_db_connection()
    cur = conn.cursor()
    for item in tracks['items']:
        track = item['track']
        track_name = track['name']
        artist_names = ', '.join([artist['name'] for artist in track['artists']])
        
        # Fetch audio features
        audio_features = sp_user.audio_features(track['id'])[0]
        tempo = audio_features['tempo']
        energy = audio_features['energy']
        danceability = audio_features['danceability']
        mood = "upbeat" if energy > 0.5 else "calm"

        track_info.append({
            'name': track_name,
            'artists': artist_names,
            'tempo': tempo,
            'energy': energy,
            'danceability': danceability,
            'mood': mood
        })

        # Insert track information into the database
        cur.execute(
            "INSERT INTO tracks (track_name, artist_names, spotify_playlist_id, tempo, energy, danceability, mood) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (track_name, artist_names, playlist_id, tempo, energy, danceability, mood)
        )

    conn.commit()
    cur.close()
    conn.close()

    return render_template('tracks.html', tracks=track_info)

@app.route('/data')
def get_data():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT track_name, artist_names, tempo, energy, danceability, mood FROM tracks")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    tracks_data = []
    for row in rows:
        tracks_data.append({
            'track_name': row[0],
            'artist_names': row[1],
            'tempo': row[2],
            'energy': row[3],
            'danceability': row[4],
            'mood': row[5]
        })
    
    return jsonify(tracks_data)

if __name__ == '__main__':
    app.run(debug=True, port=8888)






