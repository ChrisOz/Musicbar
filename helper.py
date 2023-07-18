from enum import Enum 
import subprocess

class Command(Enum):

    START_PLAYLIST = 'play playlist "{}"'
    PLAYPAUSE = 'playpause playlist "{}"'
    PLAY_NEXT_TRACK = 'play next track'
    PLAY_PREVIOUS_TRACK = 'play previous track'
    IS_PLAYING = 'get player state is playing'
    IS_TRACK_DISLIKED = 'get {{disliked}} of current track'
    STOP_TRACK = 'stop'
    DUPLICATE_TRACK_NAME_TO_LIB = 'duplicate current track to source "Library"'
    DUPLICATE_TRACK_NAME_TO_PLAYLIST = 'duplicate {{name}}'
    GET_CURRENT_TRACK_NAME = 'get {{name}} of current track'
    GET_CURRENT_TRACK = 'get current track'
    GET_CURRENT_ARTIST_NAME = 'get {{artist}} of current track'
    GET_CURRENT_GENRE_NAME = 'get {{genre}} of current track'
    GET_TRACK_POSITION = 'player position'
    GET_TRACK_NAME_BY_ID = 'get {{name}} of track id {}'
    PLAY_TRACK_BY_ID = 'play track id {}'
    SEARCH_IN_PLAYLIST = 'search playlist {} for "{}"'
    GET_PLAYLIST_NAME_BY_ID = 'get {{name}} of playlist {}'
    GET_CURRENT_PLAYLIST_NAME = 'get {{name}} of current playlist'
    GET_PLAYLIST_COUNT = 'count playlist'
    SET_TRACK_LOVE = 'set loved of current track to true'
    SET_TRACK_DISLIKE = 'set disliked of current track to true'
    QUIT = 'quit'

    def __str__(self):
        return str(self.value)

    def __int__(self):
        return int(self.value)


def exec_command(command: Command, *args) -> str:

    SHELL_ARGS = ['osascript', '-e', 'tell app "Music" to {}']
    SHELL_ARGS[2] = SHELL_ARGS[2].format(
            str(command).format(*args)
        )
    output = subprocess.run(SHELL_ARGS, capture_output=True)
    output = output.stdout.decode("utf-8")
    return output.strip()