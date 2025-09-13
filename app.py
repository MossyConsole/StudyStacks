import json
from os import environ as env
from urllib.parse import quote_plus, urlencode

from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, url_for, request, jsonify
from datacompression import Deck, Flashcard

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

app = Flask(__name__)
app.secret_key = env.get("APP_SECRET_KEY")

# In-memory storage for decks (will be replaced with MongoDB)
user_decks = {}

oauth = OAuth(app)

oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration'
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )

@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect("/logged-in")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://" + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("index", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )

@app.route('/logged-in')
def logged_in():
    user = session.get('user')
    if not user:
        return redirect('/login')
    return render_template('logged-in.html', user=user)

@app.route('/study')
def study():
    user = session.get('user')
    if not user:
        return redirect('/login')
    
    user_id = user['userinfo']['sub']
    decks = user_decks.get(user_id, [])
    return render_template('study.html', user=user, decks=decks)

@app.route('/study/select', methods=['POST'])
def study_select():
    user = session.get('user')
    if not user:
        return redirect('/login')

    idx = request.form.get('selected_deck_index')
    if idx is None:
        return redirect('/study')
    try:
        deck_index = int(idx)
    except (TypeError, ValueError):
        return redirect('/study')
    return redirect(f'/study/{deck_index}')

@app.route('/study/<int:deck_index>')
def study_deck(deck_index):
    user = session.get('user')
    if not user:
        return redirect('/login')
    
    user_id = user['userinfo']['sub']
    decks = user_decks.get(user_id, [])
    
    if deck_index < len(decks):
        deck = decks[deck_index]
        if not deck.flashcards:
            return redirect('/study')
        return render_template('study-session.html', user=user, deck=deck, deck_index=deck_index)
    
    return redirect('/study')

@app.route('/study/<int:deck_index>/answer', methods=['POST'])
def submit_answer(deck_index):
    user = session.get('user')
    if not user:
        return redirect('/login')
    
    user_id = user['userinfo']['sub']
    decks = user_decks.get(user_id, [])
    
    if deck_index < len(decks):
        card_index = int(request.form.get('card_index', 0))
        correct = request.form.get('correct') == 'true'
        
        # Update card's correct answers if answered correctly
        if correct and card_index < len(decks[deck_index].flashcards):
            decks[deck_index].flashcards[card_index].correct_answers += 1
            decks[deck_index].experience += 1
    
    return redirect(f'/study/{deck_index}')

@app.route('/manage-decks')
def manage_decks():
    user = session.get('user')
    if not user:
        return redirect('/login')
    
    user_id = user['userinfo']['sub']
    decks = user_decks.get(user_id, [])
    return render_template('manage-decks.html', user=user, decks=decks)

@app.route('/create-deck', methods=['POST'])
def create_deck():
    user = session.get('user')
    if not user:
        return redirect('/login')
    
    user_id = user['userinfo']['sub']
    deck_name = request.form.get('deck_name')
    
    if deck_name:
        new_deck = Deck(deck_name, [])
        if user_id not in user_decks:
            user_decks[user_id] = []
        user_decks[user_id].append(new_deck)
    
    return redirect('/manage-decks')

@app.route('/deck/<int:deck_index>')
def view_deck(deck_index):
    user = session.get('user')
    if not user:
        return redirect('/login')
    
    user_id = user['userinfo']['sub']
    decks = user_decks.get(user_id, [])
    
    if deck_index < len(decks):
        deck = decks[deck_index]
        return render_template('deck-detail.html', user=user, deck=deck, deck_index=deck_index)
    
    return redirect('/manage-decks')

@app.route('/deck/<int:deck_index>/add-card', methods=['POST'])
def add_card(deck_index):
    user = session.get('user')
    if not user:
        return redirect('/login')
    
    user_id = user['userinfo']['sub']
    decks = user_decks.get(user_id, [])
    
    if deck_index < len(decks):
        question = request.form.get('question')
        answer = request.form.get('answer')
        reversible = 'reversible' in request.form
        
        if question and answer:
            new_card = Flashcard(question, answer, 0, reversible)
            decks[deck_index].flashcards.append(new_card)
    
    return redirect(f'/deck/{deck_index}')

@app.route('/explore-decks')
def explore_decks():
    return render_template('explore-decks.html')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=3000, debug=True)
