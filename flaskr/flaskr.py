# -*- coding: utf-8 -*-
# all the imports
import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash
from flask_oauth import OAuth

app = Flask(__name__)  # create the application instance :)
app.config.from_object(__name__)  # load config from this file , flaskr.py

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'flaskr.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

FACEBOOK_APP_ID = '730221753751149'
FACEBOOK_APP_SECRET = '83d73c49ed7946f3db6060fbfef18106'

oauth = OAuth()

facebook = oauth.remote_app('facebook',
                            base_url='https://graph.facebook.com/',
                            request_token_url=None,
                            access_token_url='/oauth/access_token',
                            authorize_url='https://www.facebook.com/dialog/oauth',
                            consumer_key=FACEBOOK_APP_ID,
                            consumer_secret=FACEBOOK_APP_SECRET,
                            request_token_params={'scope': ('email, user_work_history, user_education_history')}
                            )


@facebook.tokengetter
def get_facebook_token():
    return session.get('facebook_token')


def pop_login_session():
    session.pop('logged_in', None)
    session.pop('facebook_token', None)


@app.route("/facebook_login")
def facebook_login():
    return facebook.authorize(callback=url_for('facebook_authorized',
                                               next=request.args.get('next'), _external=True))


@app.route("/facebook_authorized")
@facebook.authorized_handler
def facebook_authorized(resp):
    next_url = request.args.get('next') or url_for('show_entries')
    if resp is None or 'access_token' not in resp:
        return redirect(next_url)

    session['logged_in'] = True
    session['facebook_token'] = (resp['access_token'], '')

    data = facebook.get('/me?fields=id, name, email, work, education').data
    if 'id' in data and 'name' in data and 'email' in data and 'work' in data and 'education' in data:
        user_id = data['id']
        user_name = data['name']
        user_email = data['email']
        user_work_history = data['work']
        user_education_history = data['education']

    db = get_db()
    db.execute('insert into user_data (name, email) values (?, ?)', [user_name, user_email])
    cur = db.execute('select id from user_data where name = ?', [user_name])
    u_id = cur.fetchone()['id']
    session['user_id'] = u_id
    result = db.execute('SELECT COUNT(*) FROM user_diploma WHERE user_id=?', [u_id])
    if result > 0:
        db.execute('DELETE FROM user_diploma WHERE user_id=?', [u_id])
    for education in user_education_history:
        if "year" in education:
            year = education["year"]["name"]
        else:
            year = None
        db.execute('insert into user_diploma (id, school, year, user_id) values (?, ?, ?, ?)',
                    (education["school"]["id"],
                    education["school"]["name"], year, u_id))

    result = db.execute('SELECT COUNT(*) FROM user_experiences WHERE user_id=?', [u_id])
    if result > 0:
        db.execute('DELETE FROM user_experiences WHERE user_id=?', [u_id])
    for experience in user_work_history:
        if "year" in experience:
            year = experience["start_date"]
        else:
            year = None
        db.execute('insert into user_experiences (id, title, corporation, location, year, user_id) values (?, ?, ?, ?, ?, ?)',
                       [experience["position"]["id"],
                        experience["position"]["name"], experience["employer"]["name"], experience["location"]["name"], year, u_id])
    db.commit()
    return redirect(next_url)


@app.route("/logout_fb")
def logoutFB():
    pop_login_session()
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))


# Connection à la db
def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


# Initialise la db quand on utilise la commande "initdb"
@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print('Initialized the database.')


# Ouvre la db
def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    # Crée une nouvelle connectoin à la db
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


# Ferme la db
@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


# Montre les entrées déjà existantes
@app.route('/')
def show_entries():
    db = get_db()
    cur = db.execute('select * from entries order by id desc')
    entries = cur.fetchall()
    cur = db.execute('select * from replies order by id')
    replies = cur.fetchall()
    cur = db.execute('select * from user_data where id = ?', [session.get('user_id', None)])
    user_data = cur.fetchone()
    cur = db.execute('select * from user_diploma order by id')
    user_diploma = cur.fetchall()
    cur = db.execute('select * from user_experiences order by id')
    user_experiences = cur.fetchall()
    return render_template('show_entries.html', entries=entries, replies=replies, user_data=user_data,
                           user_diploma=user_diploma, user_experiences=user_experiences)


# Permet de créer de nouvelles entrées
@app.route('/add', methods=['POST'])
def add_entry():
    # Verifier que l'utilisateur est login
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    db.execute('insert into entries (title, text) values (?, ?)',
               [request.form['title'], request.form['text']])
    db.commit()
    # Affiche un message après avoir crée une nouvelle entrée
    flash('New entry was successfully posted')
    return redirect(url_for('show_entries'))


@app.route('/add_reply/<id>', methods=['POST'])
def add_reply(id):
    reply = request.form.get('reply')
    db = get_db()
    db.execute('insert into replies (reply, entry_id) values (?, ?)', [request.form['reply'], id])
    db.commit()
    return redirect(url_for('show_entries'))


# Verifie que les identifiants entrées sont corrects
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        # Mauvais username
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        # Mauvais password
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        # Identifiants corrects
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)


# Permet de logout l'utilisateur
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))


@app.route('/delete/<id>')
def delete(id):
    db = get_db()
    db.execute('DELETE FROM entries WHERE id=?', (id,))
    db.commit()
    return redirect(url_for('show_entries'))


if __name__ == "__main__":
    app.run()
