from flask import Flask, render_template, redirect, url_for, request, session
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from flask_cors import CORS
from dotenv.main import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Replace with your secret key
CORS(app)


# Spotify OAuth configuration
sp_oauth = SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback"),
    scope="playlist-read-private"
)


@app.route('/')
def index():
    return "Welcome to your app! Go to /login to authenticate with Spotify."

@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect(url_for('get_playlists'))  # Use the name of the function, not a variable

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
    
    # Process tracks
    track_info = []
    for track in tracks['items']:
        track_name = track['track']['name']
        artist_names = [artist['name'] for artist in track['track']['artists']]
        track_info.append({'name': track_name, 'artists': artist_names})
    
    return render_template('tracks.html', tracks=track_info)



if __name__ == '__main__':
    app.run(debug=True, port=8888)






