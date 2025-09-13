# File used for 
#     - storing flashcards as structs with question, answer, number of correct answers
#     - storing decks as structs with name, flashcard list, and overall experience of the deck
#     - encoding decks to csv and decoding csv to decks
#     - also encoding without exp, so others who download the deck don't already have it completed


class Flashcard:
    def __init__(self, question, answer, correct_answers=0, reversible=False):
        self.question = question
        self.answer = answer
        self.correct_answers = correct_answers or 0
        self.reversible = reversible or False


class Deck:
    def __init__(self, name, flashcards, experience=0):
        self.name = name
        self.flashcards = flashcards or []
        self.experience = experience or 0

def encode_deck(deck):
    deckAsString = deck.name + "," + str(deck.experience) + "\n"
    for flashcard in deck.flashcards:
        deckAsString += flashcard.question + "," + flashcard.answer + "," + str(flashcard.correct_answers) + "," + str(flashcard.reversible) + "\n"
    return deckAsString

def decode_deck(deckAsString):
    lines = deckAsString.strip().split("\n")
    header = lines[0].split(",")
    deck = Deck(header[0], [], int(header[1]))
    
    for line in lines[1:]:
        if line.strip():  # Skip empty lines
            parts = line.split(",")
            deck.flashcards.append(Flashcard(parts[0], parts[1], int(parts[2]), bool(parts[3])))
    return deck


#create new deck to test. 
deck = Deck("Spanish Vocab", [Flashcard("Hola", "Hello",2), Flashcard("Adios", "Goodbye", 1)],12)

print(encode_deck(deck))
print(encode_deck(decode_deck(encode_deck(deck))))
