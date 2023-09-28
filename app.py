from distutils.ccompiler import gen_lib_options
from helper import Command, exec_command
import concurrent.futures
import rumps
import time
import re
from peewee import *
import datetime
import os
import ScriptingBridge

# Initialize database
path = os.path.expanduser("~/songs.sql")

if os.path.isfile(path):
    databaseExists = True
else:
    databaseExists = False

#Connect to database and create tables
db = SqliteDatabase(None)
# Initialize database.
db.init(path, pragmas={'journal_mode': 'wal'})

class BaseModel(Model):
    class Meta:
        database = db

class Genre(BaseModel):
    name = CharField()
    disliked = BooleanField(default = False)
    liked = BooleanField(default = False)
    timestamp = DateTimeField(default=datetime.datetime.now)

    def save(self, *args, **kwargs):
        self.timestamp = datetime.datetime.now()
        return super(Genre, self).save(*args, **kwargs)

class Artist(BaseModel):
    name = CharField()
    disliked = BooleanField(default = False)
    liked = BooleanField(default = False)
    timestamp = DateTimeField(default=datetime.datetime.now)

    def save(self, *args, **kwargs):
        self.timestamp = datetime.datetime.now()
        return super(Artist, self).save(*args, **kwargs)

class Song(BaseModel):
    databaseID = IntegerField()
    name = CharField()
    dateAdded = DateField(default = datetime.datetime.now)
    dateLast = DateField(null=True)
    artist = ForeignKeyField(Artist, null=True)
    genre = ForeignKeyField(Genre, null=True)
    disliked = BooleanField(default = False)
    liked = BooleanField(default = False)
    timestamp = DateTimeField(default=datetime.datetime.now)

    def save(self, *args, **kwargs):
        self.timestamp = datetime.datetime.now()
        return super(Song, self).save(*args, **kwargs)

#Connect to database and create tables

if not databaseExists:
    db.connect()
    db.create_tables([Genre, Artist, Song])
    db.close()

#functions for easy access to database
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
                liked = track.favorited(), disliked = track.disliked())
        song.save()
        return song

#playlist scanning and manipulation functions

def findPlayList(playLists, name):
    for plist in playLists:
        if plist.name() == name:
            return plist, True
    return [], False

def copyTrackToPlayList(playlist):
    music = ScriptingBridge.SBApplication.applicationWithBundleIdentifier_('com.apple.Music')
    playList, flag = findPlayList(music.playlists(), playlist)
    if flag:
        music.currentTrack().track.duplicateTo_(playList)

def scanPlayListForNewSongs(srcPlayListName, destPlayListName, weekYear):
    db.connect()
    music = ScriptingBridge.SBApplication.applicationWithBundleIdentifier_('com.apple.Music')
    playLists = music.playlists()

    srcPlayList = None 
    destPlayList = None
    trackList = []
    numberOfSongsAdded = 0
    numberOfSongs = 0
    numberOfSongsExcluded = 0
    
    destPlayList, foundPlaylist = findPlayList(playLists, destPlayListName)    
    if not foundPlaylist:
        #create the destination playlist if it is not found
        p = {'name':destPlayListName}
        playlist = music.classForScriptingClass_('playlist').alloc().initWithProperties_(p)
        music.sources()[0].playlists().insertObject_atIndex_(playlist, 0)
        
        #you need to get the newly created playlist 
        destPlayList, foundPlaylist = findPlayList(playLists, destPlayListName) 
        if not foundPlaylist:   
            db.close()
            return 'Destination playlist {} could not be found.'.format(destPlayListName)
    else:
        #extract any existing tracks in the playlist so you can check for duplicates when adding new songs
        #print(f'Extracting songs from playlist: {srcPlayListName}')
        for track in destPlayList.tracks():
            artist = getArtist(track.artist())
            genre = getGenre(track.genre())
            song = getSong(track, artist, genre)
            trackList.append(song)

    srcPlayList, foundPlaylist = findPlayList(playLists, srcPlayListName)
    if not foundPlaylist:
        return 'Source playlist {} not found.'.format(srcPlayListName)

    # step through tracks in playlist
    for track in srcPlayList.tracks():
        artist = getArtist(track.artist())
        genre = getGenre(track.genre())
        #print(f'Track: {track.name()} - {artist.name}')
        song = getSong(track, artist, genre)
        numberOfSongs = numberOfSongs + 1
        if song.dateAdded.isocalendar()[0]*100 + song.dateAdded.isocalendar()[1] == weekYear:
            #print('   - New song')
            if song.disliked or artist.disliked or (genre.disliked and not artist.liked):
                #print(f'   - Not added to play list. Artist disliked: {artist.disliked}, Song disliked: {song.disliked}, Genere disliked: {genre.disliked} and Artist not explicitly liked')
                numberOfSongsExcluded = numberOfSongsExcluded + 1
            else:
                if not song in trackList:
                    track.duplicateTo_(destPlayList)
                    #print(f'   - Added to playlist')
                    numberOfSongsAdded = numberOfSongsAdded + 1
    db.close()
    return f'Number of songs processed: {numberOfSongs}\n {numberOfSongsAdded} new songs added to:\n\'{destPlayListName}\'\n {numberOfSongsExcluded} excluded.'
  


#rumps menu setup and logic
class AppleMusicController(rumps.App):
    def __init__(self):
        super(AppleMusicController, self).__init__(name="Music",quit_button=None)
        self.icon = "AppIcon.icns"
        
        self.PLAYLIST_COUNT = int(exec_command(Command.GET_PLAYLIST_COUNT))
        self.PLAYLISTS = []
        FORBIDDEN_PLAYLISTS = ['Library', 'Recently Added', 'Top Most Played', 'My Top Rated', 'Music Videos', 
                               'Music', 'Recently Played', 'Top 25 Most Played']
        for n in range(1, self.PLAYLIST_COUNT+1):
            name = exec_command(Command.GET_PLAYLIST_NAME_BY_ID, n)
            if not name in FORBIDDEN_PLAYLISTS:
                self.PLAYLISTS.append(rumps.MenuItem(name, callback=self.searchAndPlay))
        self.menu = ['Play/Pause','Next','Previous',None,'Like Song', 'Like Artist', 'Dislike Song','Dislike Artist', None,
                     ['Scan playlist for new songs', self.PLAYLISTS], None]

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

    @rumps.clicked('Like Song')
    def likeTrack(self, sender):
        db.connect()
        music = ScriptingBridge.SBApplication.applicationWithBundleIdentifier_('com.apple.Music')
        track = music.currentTrack()
        artist = getArtist(track.artist())
        genre = getGenre(track.genre())
        song = getSong(track, artist, genre)
        exec_command(Command.SET_TRACK_LOVE)
        song.liked = True
        song.timestamp = datetime.datetime.now
        song.save()
        db.close()

    @rumps.clicked('Dislike Song')
    def dislikeTrack(self, sender):
        db.connect()
        music = ScriptingBridge.SBApplication.applicationWithBundleIdentifier_('com.apple.Music')
        track = music.currentTrack()
        artist = getArtist(track.artist())
        genre = getGenre(track.genre())
        song = getSong(track, artist, genre)
        song.disliked = True
        song.liked = False
        song.timestamp = datetime.datetime.now
        exec_command(Command.SET_TRACK_DISLIKE)
        song.save()
        db.close()
        self.nextTrack(sender)

    @rumps.clicked('Like Artist')
    def likeArtist(self, sender):
        db.connect()
        music = ScriptingBridge.SBApplication.applicationWithBundleIdentifier_('com.apple.Music')
        track = music.currentTrack()
        artist = getArtist(track.artist())
        artist.disliked = False
        artist.liked = True
        artist.timestamp = datetime.datetime.now
        artist.save()
        db.close()

    @rumps.clicked('Dislike Artist')
    def dislikeArtist(self, sender):
        db.connect()
        music = ScriptingBridge.SBApplication.applicationWithBundleIdentifier_('com.apple.Music')
        track = music.currentTrack()
        artist = getArtist(track.artist())
        artist.disliked = True
        artist.liked = False
        artist.timestamp = datetime.datetime.now
        artist.save()
        db.close()

    @rumps.clicked('Quit')
    def clean_up_before_quit(self, sender):
        rumps.quit_application()
    
    def searchAndPlay(self, sender):
        # generate a year + week number format YYYYWW
        date = datetime.datetime.now()
        now = date.isocalendar()
        weekYear = now[0]*100 + now[1]

        # Open the new song list for the week if one exists or create a new playlist
        playListName = f'New songs {now[1]} - {now[0]}'
        
        result = scanPlayListForNewSongs(sender.title, playListName, weekYear)
        response = rumps.alert(f'Finished Scanning playlist {sender.title}', result)


if __name__ == '__main__':
    AppleMusicController().run()