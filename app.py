import os
import time
from flask import Flask, redirect, request, session, render_template, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model=genai.GenerativeModel('gemini-2.0-flash')

def get_spotify_oauth():
    return SpotifyOAuth(
        client_id=os.getenv('SPOTIFY_CLIENT_ID'),
        client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
        redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI'),
        scope='user-top-read'
    )


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    sp_oauth=get_spotify_oauth()
    auth_url=sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    sp_oauth=get_spotify_oauth()
    code=request.args.get('code')
    try:
        token_info=sp_oauth.get_access_token(code)
        session['token_info']=token_info
    except:
        return redirect(url_for('index', error="Auth failed"))
    return redirect(url_for('roast'))

@app.route('/roast')
def roast():
    token_info=session.get('token_info', None)

    if not token_info:
        return redirect('/')
    now=int(time.time())
    is_expired=token_info['expires_at'] - now < 60
    if is_expired:
        sp_oauth=get_spotify_oauth()
        token_info=sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info']=token_info
    sp=spotipy.Spotify(auth=token_info['access_token'])

    try:
        top_artists=sp.current_user_top_artists(limit=5, time_range='medium_term')['items']
        top_tracks=sp.current_user_top_tracks(limit=5, time_range='short_term')['items']

        artists_names=[a['name'] for a in top_artists]
        tracks_names=[f"{t['name']} by {t['artists'][0]['name']}" for t in top_tracks]

        top_artist_img=top_artists[0]['images'][0]['url'] if top_artists else None

        prompt=f"""Roast this person specifically and ruthlessly based on their Spotify history. 
        Be sarcastic, referencing pop culture stereotypes about these artists. 
        Don't write a generic intro, jump straight into the insult.
        Top Artists: {', '.join(artists_names)}
        Top Tracks: {', '.join(tracks_names)}
        
        """

        response=model.generate_content(prompt)
        roast_text=response.text

        return render_template('roast.html', roast=roast_text, artists=artists_names, image=top_artist_img)
    except Exception as e:
        print(f"Error: {e}")
        return redirect(url_for('index'))
    

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':  
    app.run(debug=True)
    
