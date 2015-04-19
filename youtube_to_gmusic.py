#!/usr/bin/env python2

# TODO: Cover up download, conversion and upload unless set to verbose

from __future__ import unicode_literals, print_function

import argparse
import re
import shutil
import subprocess
import tempfile

import youtube_dl
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
import mutagen.id3

from gmwrapper import MusicManagerWrapper


def download(link, temp_path):
    ydl_opts = {'format': '141/140/171',
                'outtmpl': temp_path + '/%(autonumber)s.%(ext)s'}

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([link])
    # TODO: Check file extension!
    return temp_path + '/00001.m4a'


def convert_to_mp3(temp_path, input_file):
    converted_file = temp_path + '/' + re.findall('.*/(.*)\..*$', input_file)[0] + '.mp3'
    result = subprocess.call(['ffmpeg', '-y', '-i', input_file, '-ab', '320k', converted_file])
    if result is not 0:
        print("Failed to convert file to mp3!")
        raise Exception('Failed to convert mp3')

    return converted_file


def tag_file(file_path, title, artist, album):
    mp3file = MP3(file_path, ID3=EasyID3)

    try:
        mp3file.add_tags(ID3=EasyID3)
    except mutagen.id3.error:
        pass

    artist = artist.decode('unicode-escape').encode('ascii', 'replace')
    title = title.decode('unicode-escape').encode('ascii', 'replace')

    mp3file['artist'] = artist
    mp3file['title'] = title
    mp3file['album'] = album
    mp3file.save()


def upload(file_path):
    if not hasattr(upload, 'mmw'):
        upload.mmw = MusicManagerWrapper()
        upload.mmw.login()
    upload.mmw.upload(file_path)


def get_title(link):
    # TODO: Find 'get-title' option in youtube_dl
    pass


def main(link, artist, title):
    album = 'Youtube Uploads'
    try:
        temp_path = tempfile.mkdtemp()
        downloaded_file = download(link, temp_path)
        converted_file = convert_to_mp3(temp_path, downloaded_file)
        if title is None:
            title = get_title(link)
        tag_file(converted_file, title, artist,  album)
        upload(converted_file)
    finally:
        shutil.rmtree(temp_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
#    parser.add_argument('-v', '--verbose',
#                        help='Increase verbosity of output',
#                        action='count')
    parser.add_argument('link', help='Link to youtube video to be used')
    parser.add_argument('-a', '--artist',
                        default='Unknown',
                        help='Default: Unknown')
    parser.add_argument('-t', '--title',
                        help='Default: Video title')

    args = parser.parse_args()

    main(args.link, args.artist, args.title)
