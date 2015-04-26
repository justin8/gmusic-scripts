#!/usr/bin/env python2

import json
import oauth2client.client
import oauth2client.multistore_file
from flask import Flask, request, abort, jsonify, session, redirect
from oauth2client.client import OAuth2WebServerFlow, TokenRevokeError
from oauth2client.multistore_file import get_credential_storage
import requests
import httplib2

import youtube_to_gmusic

try:
    with file('settings', 'r') as f:
        settings = json.load(f)
        # Load to local variables directly so that any missing settings are detected at the start
        app_secret_key = settings['app_secret_key']
        client_secret = settings['client_secret']
        client_id = settings['client_id']
except Exception as e:
    print('Error loading settings file!')
    raise(e)

youtube_to_gmusic.VERBOSE = True

app = Flask(__name__)
app.secret_key = app_secret_key



#@app.route("/download", methods=['POST'])
#def download():
#    if not request.json or 'link' not in request.json:
#        abort(400)
#    try:
#        # youtube_to_gmusic.process_link(request.json['link'])
#        return jsonify({}), 201
#    except Exception as e:
#        return jsonify({'error': e.message}), 500


@app.route("/process", methods=['POST', 'GET'])
def process():
    if 'user' not in session or not session['user']:
        session['redirect'] = True
        session['request'] = request.form
        return redirect('/login', code=301)
    if session['redirect']:
        print('%r' % session['request'])
        session['redirect'] = False
        data = session['request']
    else:
        data = request.form
    if 'link' not in data:
        return 'No link was specified!', 400
        abort(400)

    store = get_credential_storage(credential_store,
                                   session['user'],
                                   oauth_app_creds['user_agent'],
                                   oauth_app_creds['scope'])
    credentials = store.get()
    if not credentials:
        return jsonify({'result': 'Error',
                        'details': 'No user credentials found'})

    try:
        youtube_to_gmusic.process_link(data['link'], credentials=credentials)
        return jsonify({'result': 'Success',
                        'details': None}), 200
    except Exception as e:
        return jsonify({'result': 'Error',
                        'details': e.message}), 400


#@app.route("/search", methods=['POST'])
#def search():
#    if not request.json or 'search' not in request.json:
#        abort(400)
#    try:
#        youtube_to_gmusic.process_search(request.json['search'])
#        return jsonify({}), 201
#    except Exception as e:
#        return jsonify({'error': e.message}), 500


# Oauth Testing
oauth_app_creds = {
    "client_secret": client_secret,
    "redirect_uri": "http://afzelia.dray.be:5000/oauth2callback",
    "client_id": client_id,
    "scope": ["https://www.googleapis.com/auth/musicmanager",
              "https://www.googleapis.com/auth/userinfo.email",
              "https://www.googleapis.com/auth/userinfo.profile"],
    "user_agent": "afzelia/1.0",
    "access_type": "offline",
}

flow = OAuth2WebServerFlow(**oauth_app_creds)
authorize_url = flow.step1_get_authorize_url()
credential_store = 'credentials'


def is_valid_state(state):
    return True


@app.route("/test", methods=['POST'])
def test():
    return '%r' % request.form['test']


@app.route("/get_session")
def get_session():
    return '%r' % session


@app.route("/logout")
def logout():
    if 'user' in session:
        session.clear()
        text = "You've been logged out!"
    else:
        text = "You were already logged out!"
    return text


@app.route("/login")
def login():
    if 'user' in session and session['user']:
        out = "Hi %s. You're already logged in" % session['user']
    else:
        out = redirect(authorize_url, code=301)
    return out


@app.route("/oauth2callback")
def oauth2callback():
    error = request.args.get('error', '')
    if error:
        return 'Error: ' + error

    state = request.args.get('state', '')
    if not is_valid_state(state):
        # Request not started by us?
        abort(403)

    credentials = flow.step2_exchange(code=request.args)
    user = credentials.id_token['email']
    store = get_credential_storage(credential_store,
                                   user,
                                   oauth_app_creds['user_agent'],
                                   oauth_app_creds['scope'])
    old_credentials = store.get()
    if old_credentials:
        ort = old_credentials.refresh_token
        nrt = old_credentials.refresh_token
        credentials.refresh_token = ort if not nrt else nrt

    # Clean up old credentials before writing new ones.
    # For some reason it sometimes ends up with duplicates?
    store.delete()
    store.put(credentials)
    http = httplib2.Http()
    http = credentials.authorize(http)
    credentials.refresh(http)
    session['user'] = user
    if 'redirect' in session and session['redirect']:
        return redirect('/process', code=301)
    return redirect('/login', code=301)


# Check if credentials are stored by email address
# if they aren't, redirect to login. (is there a way to redirect again after?)
# if they exist, attempt to process link
# if they are no longer valid, redirect back to login


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
