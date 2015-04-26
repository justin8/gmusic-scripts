#!/usr/bin/env python2

from __future__ import unicode_literals, print_function

import argparse
import json
import shutil
import tempfile
import requests
import sys
from exceptions import IOError

import acoustid
import mutagen.id3
import youtube_dl
from apiclient.discovery import build
from gmusicapi import CallFailure
from gmusicapi.clients import Musicmanager, OAUTH_FILEPATH
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3


requests.packages.urllib3.disable_warnings()
VERBOSE = False
try:
    with file('settings', 'r') as f:
        settings = json.load(f)
        # Load to local variables directly so that any missing settings are detected at the start
        acoustid_api_key = settings['acoustid_api_key']
        google_api_key = settings['google_api_key']
except Exception as e:
    print('Error loading settings file!')
    raise(e)


def vprint(line):
    if VERBOSE:
        print(line)


def download(link, temp_path):
    print('Downloading...')
    ydl_opts = {'format': 'bestaudio/best',
                'outtmpl': temp_path + '/%(autonumber)s.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }],
                'quiet': not VERBOSE,
                }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([link])
    # TODO: Check file extension!
    return temp_path + '/00001.mp3'


def tag_file(file_path, title, artist, album):
    print("Tagging...")
    mp3file = MP3(file_path, ID3=EasyID3)
    try:
        mp3file.add_tags(ID3=EasyID3)
    except mutagen.id3.error:
        pass

    if isinstance(artist, str):
        artist = artist.decode('utf-8')
    if isinstance(title, str):
        title = title.decode('utf-8')
    if isinstance(album, str):
        album = album.decode('utf-8')

    mp3file['artist'] = artist
    mp3file['title'] = title
    mp3file['album'] = album
    mp3file.save()


def get_song_info(file_path, title, artist, album, link):
    album = 'Youtube' if album is None else album
    if not title or not artist:
        match = acoustid.match(acoustid_api_key, file_path)
        try:
            result = match.next()
            artist = result[3] if artist is None else artist
            title = result[2] if title is None else title
        except:
            print("Unable to match via AcoustID! Falling back to video title")
            artist = 'Unknown' if artist is None else artist
            title = get_youtube_title(link) if title is None else title
    vprint("Found song info:\n" +
           "    Artist: %s\n" % artist +
           "    Title: %s\n" % title +
           "    Album: %s" % album)
    return [title, artist, album]


def get_youtube_title(link):
    ydl = youtube_dl.YoutubeDL({'quiet': not VERBOSE})
    result = ydl.extract_info(link, download=False)
    return result['title']


def gm_login(credentials):
    if not hasattr(gm_login, 'api'):
        # Stored api connection for multiple upload support without re-authing every time
        gm_login.api = Musicmanager(debug_logging=VERBOSE)
    # Credential pass through is working here
    if not gm_login.api.is_authenticated():
        if not gm_login.api.login(OAUTH_FILEPATH if not credentials else credentials):
            try:
                gm_login.api.perform_oauth()
            except:
                print("Unable to login with specified oauth code.")
            gm_login.api.login(OAUTH_FILEPATH if not credentials else credentials)
    return gm_login.api


def upload(file_path, credentials):
    # TODO: Report song being uploaded? 'artist - title'?
    print("Uploading...")
    api = gm_login(credentials)

    try:
        # Can set enable_matching on the api.upload call but apparently requires avconv
        # matching appears to suck. acoustID is more accurate
        uploaded, matched, not_uploaded = api.upload(file_path, enable_matching=False)
    except CallFailure as e:
        print("Failed to upload: %s" % e)
    else:
        if uploaded:
            print("Uploaded successfully!")
        else:
            if 'ALREADY_EXISTS' in not_uploaded[file_path]:
                raise Exception("Failed to upload file. Already exists.")


def process_link(link, artist=None, title=None, album=None, credentials=None):
    album = 'Youtube Uploads'
    try:
        temp_path = tempfile.mkdtemp()
        downloaded_file = download(link, temp_path)
        title, artist, album = get_song_info(downloaded_file, title, artist, album, link)
        tag_file(downloaded_file, title, artist,  album)
        upload(downloaded_file, credentials)
    except Exception as e:
        raise e
    finally:
        shutil.rmtree(temp_path)


def search_for_id(search):
    print('Searching for video...')

    youtube = build('youtube', 'v3', developerKey=google_api_key)
    search_response = youtube.search().list(q=search, part='id,snippet', maxResults=1).execute()

    video_id = search_response['items'][0]['id']['videoId']
    title = search_response['items'][0]['snippet']['title']

    print("Found video '%s'" % title)
    vprint("Video ID: %s\n" % video_id)

    return video_id


def process_search(search, artist=None, title=None, album=None):
    video_id = search_for_id(search)
    process_link(video_id, artist, title, album)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.description = ('Import the provided youtube link/ID to your Google Music account ' +
                          'Default album will be "Youtube" ' +
                          'Default artist/title will be discovered via acoustID. ' +
                          'If no match is found via acoustID the Youtube title will be used ' +
                          'with "Unknown" as the artist. Either link or search must be specified.')
    parser.add_argument('-v', '--verbose',
                        help='Increase verbosity of output',
                        action='count')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-l', '--link', help='Link (or just the ID) to youtube video to be used')
    group.add_argument('-s', '--search')
    parser.add_argument('-a', '--artist')
    parser.add_argument('-b', '--album')
    parser.add_argument('-t', '--title')

    args = parser.parse_args()

    if args.verbose > 0:
        VERBOSE = True

    if args.link:
        process_link(args.link, args.artist, args.title, args.album)
    elif args.search:
        process_search(args.search, args.artist, args.title, args.album)
