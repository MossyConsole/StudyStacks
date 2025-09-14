import json
from os import environ as env
from urllib.parse import quote_plus, urlencode
import pymongo
from bson.objectid import ObjectId

from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, url_for, request, jsonify
from datacompression import Deck, Flashcard
from ai_cards import getResponseFromPrompt

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

app = Flask(__name__)
app.secret_key = env.get("APP_SECRET_KEY")

# MongoDB connection
try:
    mongo = pymongo.MongoClient(
        host='localhost', 
        port=27017,
        serverSelectionTimeoutMS = 1000
    )
    db = mongo.studystack
    mongo.server_info() # Triggers the exception if connection to the database is unsuccessful
    print("Connected to MongoDB successfully")
except Exception as ex:
    print(f"ERROR - Cannot connect to MongoDB: {ex}")
    db = None

# In-memory storage for decks (fallback if MongoDB is not available)
user_decks = {}

# MongoDB helper functions
def get_user_decks(user_id):
    """Get all decks for a user from MongoDB or fallback to in-memory storage"""
    if db is not None:
        try:
            decks_data = list(db.decks.find({"user_id": user_id}))
            decks = []
            for deck_data in decks_data:
                # Convert MongoDB document to Deck object
                flashcards = []
                for card_data in deck_data.get('flashcards', []):
                    flashcard = Flashcard(
                        card_data['question'],
                        card_data['answer'],
                        card_data.get('correct_answers', 0),
                        card_data.get('reversible', False)
                    )
                    flashcards.append(flashcard)
                
                deck = Deck(deck_data['name'], flashcards)
                deck.experience = deck_data.get('experience', 0)
                decks.append(deck)
            return decks
        except Exception as ex:
            print(f"Error getting decks from MongoDB: {ex}")
    
    # Fallback to in-memory storage
    return user_decks.get(user_id, [])

def save_user_decks(user_id, decks):
    """Save all decks for a user to MongoDB or fallback to in-memory storage"""
    if db is not None:
        try:
            # Clear existing decks for this user
            db.decks.delete_many({"user_id": user_id})
            
            # Save new decks
            for deck in decks:
                flashcards_data = []
                for card in deck.flashcards:
                    flashcards_data.append({
                        'question': card.question,
                        'answer': card.answer,
                        'correct_answers': card.correct_answers,
                        'reversible': card.reversible
                    })
                
                deck_data = {
                    'user_id': user_id,
                    'name': deck.name,
                    'experience': deck.experience,
                    'flashcards': flashcards_data
                }
                db.decks.insert_one(deck_data)
            return True
        except Exception as ex:
            print(f"Error saving decks to MongoDB: {ex}")
    
    # Fallback to in-memory storage
    user_decks[user_id] = decks
    return True

def generate_ai_cards(deck, num_cards=5):
    print("Got here first tho")
    """Generate AI cards for a deck, avoiding duplicates with existing cards."""
    existing_questions = [card.question.lower() for card in deck.flashcards]
    existing_answers = [card.answer.lower() for card in deck.flashcards]
    
    # Create context about existing cards
    existing_cards_text = ""
    if deck.flashcards:
        existing_cards_text = "\n\nExisting cards in this deck (DO NOT create duplicates):\n"
        for card in deck.flashcards[:10]:  # Show up to 10 existing cards for context
            existing_cards_text += f"Q: {card.question} | A: {card.answer}\n"
    
    prompt = f"""Generate {num_cards} flashcards for the deck "{deck.name}".
Each line should be formatted EXACTLY as:
Q: <question> | A: <answer>

Requirements:
- Make cards that fit the theme/subject of the deck name
- Each card should be educational and useful for studying
- Questions should be clear and concise
- Answers should be accurate and brief
- DO NOT create any duplicates of existing cards{existing_cards_text}

Generate {num_cards} new unique flashcards now:"""

    try:
        response = getResponseFromPrompt(prompt)
        print("Got it!")
        return parse_ai_response(response, existing_questions, existing_answers)
    except Exception as e:
        print(f"Error generating AI cards: {e}")
        return []

def parse_ai_response(response, existing_questions, existing_answers):
    """Parse AI response and return list of Flashcard objects."""
    cards = []
    lines = response.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or not ('Q:' in line and 'A:' in line and '|' in line):
            continue
            
        try:
            # Split on | to get question and answer parts
            parts = line.split('|', 1)
            if len(parts) != 2:
                continue
                
            question_part = parts[0].strip()
            answer_part = parts[1].strip()
            
            # Remove Q: and A: prefixes
            if question_part.startswith('Q:'):
                question = question_part[2:].strip()
            else:
                continue
                
            if answer_part.startswith('A:'):
                answer = answer_part[2:].strip()
            else:
                continue
            
            # Check for duplicates (case insensitive)
            if question.lower() not in existing_questions and answer.lower() not in existing_answers:
                cards.append(Flashcard(question, answer, 0, False))
                existing_questions.append(question.lower())
                existing_answers.append(answer.lower())
                
        except Exception as e:
            print(f"Error parsing line '{line}': {e}")
            continue
    
    return cards


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
    decks = get_user_decks(user_id)
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
    decks = get_user_decks(user_id)
    
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
    decks = get_user_decks(user_id)
    
    if deck_index < len(decks):
        card_index = int(request.form.get('card_index', 0))
        correct = request.form.get('correct') == 'true'
        
        # Update card's correct answers if answered correctly
        if correct and card_index < len(decks[deck_index].flashcards):
            decks[deck_index].flashcards[card_index].correct_answers += 1
            decks[deck_index].experience += 1
            save_user_decks(user_id, decks)
    
    return redirect(f'/study/{deck_index}')

@app.route('/manage-decks')
def manage_decks():
    user = session.get('user')
    if not user:
        return redirect('/login')
    
    user_id = user['userinfo']['sub']
    decks = get_user_decks(user_id)
    return render_template('manage-decks.html', user=user, decks=decks)

@app.route('/create-deck', methods=['POST'])
def create_deck():
    user = session.get('user')
    if not user:
        return redirect('/login')
    
    user_id = user['userinfo']['sub']
    deck_name = request.form.get('deck_name')
    
    if deck_name:
        decks = get_user_decks(user_id)
        new_deck = Deck(deck_name, [])
        decks.append(new_deck)
        save_user_decks(user_id, decks)
    
    return redirect('/manage-decks')

@app.route('/deck/<int:deck_index>')
def view_deck(deck_index):
    user = session.get('user')
    if not user:
        return redirect('/login')
    
    user_id = user['userinfo']['sub']
    decks = get_user_decks(user_id)
    
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
    decks = get_user_decks(user_id)
    
    if deck_index < len(decks):
        question = request.form.get('question')
        answer = request.form.get('answer')
        reversible = 'reversible' in request.form
        
        if question and answer:
            new_card = Flashcard(question, answer, 0, reversible)
            decks[deck_index].flashcards.append(new_card)
            save_user_decks(user_id, decks)
    
    return redirect(f'/deck/{deck_index}')

@app.route('/deck/<int:deck_index>/expand', methods=['POST'])
def expand_deck(deck_index):
    user = session.get('user')
    if not user:
        return redirect('/login')
    
    user_id = user['userinfo']['sub']
    decks = get_user_decks(user_id)
    
    if deck_index < len(decks):
        deck = decks[deck_index]
        
        # Get number of cards to generate (default 5)
        num_cards = request.form.get('num_cards', 5)
        try:
            num_cards = int(num_cards)
            num_cards = max(1, min(num_cards, 10))  # Limit between 1-10 cards
        except (ValueError, TypeError):
            num_cards = 5
        
        # Generate AI cards
        new_cards = generate_ai_cards(deck, num_cards)
        
        # Add generated cards to the deck
        deck.flashcards.extend(new_cards)
        save_user_decks(user_id, decks)
    
    return redirect(f'/deck/{deck_index}')

@app.route('/deck/<int:deck_index>/delete-card/<int:card_index>', methods=['POST'])
def delete_card(deck_index, card_index):
    user = session.get('user')
    if not user:
        return redirect('/login')
    
    user_id = user['userinfo']['sub']
    decks = get_user_decks(user_id)
    
    if deck_index < len(decks) and card_index < len(decks[deck_index].flashcards):
        decks[deck_index].flashcards.pop(card_index)
        save_user_decks(user_id, decks)
    
    return redirect(f'/deck/{deck_index}')

@app.route('/delete-deck/<int:deck_index>', methods=['POST'])
def delete_deck(deck_index):
    user = session.get('user')
    if not user:
        return redirect('/login')
    
    user_id = user['userinfo']['sub']
    decks = get_user_decks(user_id)
    
    if deck_index < len(decks):
        decks.pop(deck_index)
        save_user_decks(user_id, decks)
    
    return redirect('/manage-decks')

@app.route('/explore-decks')
def explore_decks():
    return render_template('explore-decks.html')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=3000, debug=True)
