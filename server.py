#!/usr/bin/env python2

from flask import Flask, request, abort, jsonify

import youtube_to_gmusic

youtube_to_gmusic.VERBOSE = True

app = Flask(__name__)


@app.route("/download", methods=['POST'])
def download():
    if not request.json or 'link' not in request.json:
        abort(400)
    try:
        youtube_to_gmusic.process_link(request.json['link'])
        return jsonify({}), 201
    except Exception as e:
        return jsonify({'error': e.message}), 500


@app.route("/search", methods=['POST'])
def search():
    if not request.json or 'search' not in request.json:
        abort(400)
    try:
        youtube_to_gmusic.process_search(request.json['search'])
        return jsonify({}), 201
    except Exception as e:
        return jsonify({'error': e.message}), 500


if __name__ == "__main__":
    app.run(debug=True)
