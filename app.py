from distutils.ccompiler import gen_lib_options
from helper import Command, exec_command
import concurrent.futures
import rumps
import time
import re
from peewee import *
import datetime
import ScriptingBridge

# Initialize database.
db = PostgresqlDatabase(None)
db.init('chrisdrew', host='localhost', user='chrisdrew')

class BaseModel(Model):
    class Meta:
        database = db

class Genre(BaseModel):
    name = CharField()
    disliked = BooleanField(default = False)
    liked = BooleanField(default = False)

class Artist(BaseModel):
    name = CharField()
    disliked = BooleanField(default = False)
    liked = BooleanField(default = False)

class Song(BaseModel):
    databaseID = IntegerField()
    name = CharField()
    dateAdded = DateField(default = datetime.datetime.now)
    dateLast = DateField(null=True)
    artist = ForeignKeyField(Artist, null=True)
    genre = ForeignKeyField(Genre, null=True)
    disliked = BooleanField(default = False)
    liked = BooleanField(default = False)

def getGenre(name):
    try:
        return Genre.select().where(Genre.name == name).get()
    except DoesNotExist:
        genre = Genre(name = name)
        genre.save()
        return genre

def getArtist(name):
    try:
        return Artist.select().where(Artist.name == name).get()
    except DoesNotExist:
        artist = Artist(name = name)
        artist.save()
        return artist

def getSong(track, artist, genre):
    try:
        return Song.get(Song.name == track.name(), Song.artist == artist.id)
    except DoesNotExist:
        song = Song(databaseID = track.databaseID(), name = track.name(), artist = artist.id, genre = genre.id, \
                liked = track.loved(), disliked = track.disliked())
        song.save()
        return song

#Connect to database and create tables
db.connect()
db.create_tables([Genre, Artist, Song])

class AppleMusicController(rumps.App):
    def __init__(self):
        super(AppleMusicController, self).__init__(name="Music")
        self.music = ScriptingBridge.SBApplication.applicationWithBundleIdentifier_('com.apple.Music')
        self.icon = "AppIcon.icns"
        self.menu = ['Play/Pause','Next','Previous','Stop',None,'Like Song', 'Like Artist', 'Dislike Song','Dislike Artist', None]
        self.playing = exec_command(Command.IS_PLAYING)

    def startPlaylist(self, sender):
        exec_command(Command.START_PLAYLIST, sender.title.strip())
        self.playing = True

    def playTrackById(self, trackID):
        exec_command(Command.PLAY_TRACK_BY_ID, trackID)
        self.playing = True

    @rumps.clicked('Play/Pause')
    def playPause(self, sender):
        exec_command(Command.PLAYPAUSE, Command.GET_CURRENT_PLAYLIST_NAME)
        self.playing = exec_command(Command.IS_PLAYING)

    @rumps.clicked('Next')
    def nextTrack(self, sender):
        exec_command(Command.PLAY_NEXT_TRACK)
        self.playing = exec_command(Command.IS_PLAYING)

    @rumps.clicked('Previous')
    def previousTrack(self, sender):
        exec_command(Command.PLAY_PREVIOUS_TRACK)
        self.playing = True

    @rumps.clicked('Stop')
    def stopTrack(self, sender):
        exec_command(Command.STOP_TRACK)
        exec_command(Command.QUIT)
        self.menu['Play/Pause'].set_callback(None)
        self.title = None   
        self.playing = False

    @rumps.clicked('Like Song')
    def likeTrack(self, sender):
        track = self.music.currentTrack()
        artist = getArtist(track.artist())
        genre = getGenre(track.genre())
        song = getSong(track, artist, genre)
        exec_command(Command.SET_TRACK_LOVE)
        song.liked = True
        song.save()

    @rumps.clicked('Dislike Song')
    def dislikeTrack(self, sender):
        track = self.music.currentTrack()
        artist = getArtist(track.artist())
        genre = getGenre(track.genre())
        song = getSong(track, artist, genre)
        song.disliked = True
        song.liked = False
        exec_command(Command.SET_TRACK_DISLIKE)
        song.save()
        self.nextTrack(sender)


    @rumps.timer(1)
    def updateTitle(self, sender):
        if self.playing:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                executor.submit(self.getPosition)

    def getPosition(self):
        pos = exec_command(Command.GET_TRACK_POSITION)
        if pos!='missing value':
            pos = time.strftime("%M:%S", time.gmtime(float(pos)))

            self.menu['Play/Pause'].set_callback(self.playPause)
            #title = exec_command(Command.GET_CURRENT_TRACK_NAME).replace('(','').replace(')','').replace('.','').replace('\'','').strip()
            #self.title = f"{title} • {pos}"
            self.title = f'{pos}'


if __name__ == '__main__':
    AppleMusicController().run()







