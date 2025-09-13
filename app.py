from flask import Flask, request, render_template

app = Flask(__name__)

@app.route('/')
def index():
    name = request.args.get('name', 'World')
    return render_template('index.html', name=name)

@app.route('/logged-in')
def logged_in():
    return render_template('logged-in.html')

@app.route('/study')
def study():
    return render_template('study.html')

@app.route('/manage-decks')
def manage_decks():
    return render_template('manage-decks.html')

@app.route('/explore-decks')
def explore_decks():
    return render_template('explore-decks.html')

if __name__ == '__main__':
    app.run(debug=True)
