#!/usr/bin/env python2

import httplib2
import json
from flask import Flask, request, abort, jsonify, session, redirect
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.multistore_file import get_credential_storage

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


@app.route("/process", methods=['POST', 'GET'])
def process():
    if 'user' not in session or not session['user']:
        session['redirect'] = True
        session['request'] = request.form
        return redirect('/login', code=301)
    else:
        store = get_credential_storage(credential_store,
                                       session['user'],
                                       oauth_app_creds['user_agent'],
                                       oauth_app_creds['scope'])
        credentials = store.get()

    if not credentials:
        return jsonify({'error': 'No user credentials found'}), 500

    if session['redirect']:
        print('%r' % session['request'])
        session['redirect'] = False
        data = session['request']
    else:
        data = request.form
    if 'link' not in data and 'search' not in data:
        return jsonify({'error': 'No link or search term was specified!'}), 400
        abort(400)

    try:
        if 'link' in data:
            youtube_to_gmusic.process_link(data['link'], credentials=credentials)
        elif 'search' in data:
            youtube_to_gmusic.process_search(data['search'], credentials=credentials)
        else:
            raise(Exception("This shouldn't happen!"))
        return jsonify({}), 200
    except Exception as e:
        return jsonify({'error': e.message}), 400


@app.route("/logout")
def logout():
    if 'user' in session:
        session.clear()
        out = "You've been logged out!"
    else:
        out = "You were already logged out!"
    return jsonify({'details': out})


@app.route("/login")
def login():
    if 'user' in session and session['user']:
        return jsonify({'details': "Hi %s. You're already logged in" % session['user']}), 200
    else:
        return redirect(authorize_url, code=301)


@app.route("/oauth2callback")
def oauth2callback():
    error = request.args.get('error', '')
    if error:
        return jsonify({'error': error})

    try:
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

        # Check that the credentials we have are correct
        http = credentials.authorize(http)
        credentials.refresh(http)
    except Exception as e:
        if 'invalid_grant' in e.message:
            code = 500
        else:
            code = 400
        return jsonify({'error': e.message}), code

    session['user'] = user
    if 'redirect' in session and session['redirect']:
        return redirect('/process', code=301)
    return redirect('/login', code=301)


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
