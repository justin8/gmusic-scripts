#!/usr/bin/env python2

# TODO: Cover up download, conversion and upload unless set to verbose

from __future__ import unicode_literals, print_function

import argparse
import re
import shutil
import tempfile
import requests

import acoustid
import youtube_dl
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
import mutagen.id3

from gmwrapper import MusicManagerWrapper


requests.packages.urllib3.disable_warnings()
ACOUSTID_API_KEY = 'TjNRZRtM'
VERBOSE = False


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
    print("Tagging...")

    mp3file['artist'] = artist
    mp3file['title'] = title
    mp3file['album'] = album
    mp3file.save()


def get_song_info(file_path, title, artist, album, link):
    album = 'Youtube' if album is None else album
    if not title or not artist:
        match = acoustid.match(ACOUSTID_API_KEY, file_path)
        try:
            result = match.next()
            artist = result[3] if artist is None else artist
            title = result[2] if title is None else title
        except:
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


def upload(file_path):
    if not hasattr(upload, 'mmw'):
        upload.mmw = MusicManagerWrapper()
        upload.mmw.login()
    upload.mmw.upload(file_path)


def main(link, artist, title, album):
    album = 'Youtube Uploads'
    try:
        temp_path = tempfile.mkdtemp()
        downloaded_file = download(link, temp_path)
        title, artist, album = get_song_info(downloaded_file, title, artist, album, link)
        tag_file(downloaded_file, title, artist,  album)
        upload(downloaded_file)
    finally:
        pass
        shutil.rmtree(temp_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.description = ('Import the provided youtube link/ID to your Google Music account\n' +
                          'Default album will be "Youtube"\n' +
                          'Default artist/title will be discovered via acoustID.\n' +
                          'If no match is found via acoustID the Youtube title will be used\n' +
                          'with "Unknown" as the artist')
    parser.add_argument('-v', '--verbose',
                        help='Increase verbosity of output',
                        action='count')
    parser.add_argument('link', help='Link (or just the ID) to youtube video to be used')
    parser.add_argument('-a', '--artist')
    parser.add_argument('-b', '--album')
    parser.add_argument('-t', '--title')

    args = parser.parse_args()

    if args.verbose > 0:
        VERBOSE = True

    main(args.link, args.artist, args.title, args.album)
