app = flask(__name__)

@app.route('/')
def index():
    name = request.args.get('name', 'World')
    return render_template('index.html', name=name)

if __name__ == '__main__':
    app.run(debug=True)
