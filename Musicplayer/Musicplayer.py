import sqlite3
import os
from mutagen import File
from PyQt6.QtWidgets import QApplication, QPushButton, QWidget, QMainWindow, QHBoxLayout, QSlider, QLabel
from PyQt6.QtWidgets import QGridLayout, QVBoxLayout,  QRadioButton, QSizePolicy, QFrame, QButtonGroup,QLineEdit
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QIntValidator
import pygame

###################
# Global Variables
###################

paused = False
current_song_index = 0
songlist = []
songs_loaded = False
current_song_path = None
current_song_duration = 0.0


####################
# GUI CODE
####################

class TitleBar(QWidget):
    displaychanged = pyqtSignal(str)
    def __init__(self):
        super().__init__()
       
        self.setFixedHeight(30)
        self.setStyleSheet("background-color: #333; color: white;  border-bottom: 2px solid #222;")

        # Title label
        self.title_label = QLabel("Music Player")
        self.title_label.setStyleSheet("font-weight: bold;")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # Dropdown button
        self.dropdown_button = QPushButton("=")
        self.dropdown_button.setStyleSheet("background: None; color: white; border: none; font-size: 18px;")
        self.dropdown_button.setFixedSize(30, 30)
        self.dropdown_button.clicked.connect(self.toggle_dropdown)
        
        self.dropdown_button.setStyleSheet("""  
        QPushButton {
          background: none;
          color: white;
          border: none;
          font-size: 18px;
          font-weight: bold;
          padding: 5px;
          border-top-left-radius: 6px;
         }
        
        QPushButton:hover {
         background-color: #505050;
        }

       QPushButton:pressed {
         background-color: #2e2e2e;
       }
       """)

        layout = QHBoxLayout()
        layout.addWidget(self.dropdown_button)
        layout.addWidget(self.title_label, 10, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        layout.setContentsMargins(0, 0, 0, 0)
        

        self.dropdown = QWidget(self, flags=Qt.WindowType.Popup)
        self.dropdown.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.dropdown.setStyleSheet("background-color: None; border: 1px solid black;")
        
        vbox = QVBoxLayout()

        self.radio1 = QRadioButton("Small Display")
        self.radio2 = QRadioButton("Full Display")
      
        
        self.radio1.toggled.connect(self.radio1toggled)
        self.radio2.toggled.connect(self.radio2toggled)
      
        
        

        self.radio1.setChecked(True)
        
        vbox.addWidget(self.radio1)
        vbox.addWidget(self.radio2)
       
        self.dropdown.setLayout(vbox)
        self.dropdown.setFixedSize(150, 100)
        
        self.radio_group = QButtonGroup(self)
        self.radio_group.addButton(self.radio1)
        self.radio_group.addButton(self.radio2)
     
        
        
        
        self.min_button = QPushButton("–")
        self.min_button.setFixedSize(30, 30)
        layout.addWidget(self.min_button)
        
        self.min_button.setStyleSheet("""
        QPushButton {
          background: none;
          color: white;
          border: none;
          font-size: 18px;
          font-weight: bold;
          padding: 5px;
         }
        QPushButton:hover {
         background-color: #505050;
        }

       QPushButton:pressed {
         background-color: #2e2e2e;
       }
       """)

   
        # Close button
        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(30, 30)
        layout.addWidget(self.close_button)
        self.close_button.setStyleSheet("""
        QPushButton {
          background: none;
          color: white;
          border: none;
          font-size: 18px;
          font-weight: bold;
          padding: 5px;
          border-top-right-radius: 6px;
         }
        QPushButton:hover {
          background-color: red;
         }
        
        QPushButton:pressed {
            background-color: red;
        }
        """)

        self.min_button.clicked.connect(self.minimize_window)
       
        self.close_button.clicked.connect(self.close_window)

        self.setLayout(layout)
        
        
    def toggle_dropdown(self):
        if self.dropdown.isVisible():
            self.dropdown.hide()
        else:
            btn_pos = self.dropdown_button.mapToGlobal(QPoint(0, self.dropdown_button.height()))
            self.dropdown.move(btn_pos)
            self.dropdown.show()
            
    def toggle_max_restore(self):
        window = self.window()
        if window.isMaximized():
            window.showNormal()
        else:
            window.showMaximized()
    def minimize_window(self):
        window = self.window()
        window.showMinimized()

    def close_window(self):
        window = self.window()
        window.close()
        
    def radio1toggled(self, checked):
     if checked:
        self.displaychanged.emit("small")

    def radio2toggled(self, checked):
     if checked:
        self.displaychanged.emit("full")


class MainWindow(QMainWindow):
    displaymin = 0
    displaymax = 10
    windowsize =(0,0)
    def __init__(self):
       
        
        super().__init__()
        
        self.user_is_seeking = False
        self.seek_cooldown = 0
        self.playback_offset = 0.0 

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        
        mainwidget = QWidget()
        mainlayout = QVBoxLayout()
        mainlayout.setContentsMargins(0, 0, 0, 0) 
        mainlayout.setSpacing(0)
        
        self.windowttitle = TitleBar()
        mainlayout.addWidget(self.windowttitle)
        self.windowttitle.displaychanged.connect( self.handle_displaychanged)
        
        self.currenttime = QLabel("")
        self.totaltime = QLabel("")
        
        self.currentsong = QLabel("")
        self.currentsong.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.currentsong.setStyleSheet("font-size: 14px")
        
        self.pausebutton = QPushButton(">")
        prevbutton = QPushButton("<<")
        skipbutton = QPushButton(">>")
        
        button_style = """
          QPushButton {
          background-color: #333;
          color: white;
          border: 1px solid #444;
          border-radius: 2px;
          padding: 2px;
          font-size: 16px;
          }

          QPushButton:hover {
           background-color: #505050;
          }

          QPushButton:pressed {
            background-color: #2e2e2e;
          }"""

        self.pausebutton.setStyleSheet(button_style)
        prevbutton.setStyleSheet(button_style)
        skipbutton.setStyleSheet(button_style)
        
        volumeslide = QSlider(Qt.Orientation.Vertical, self)
        volumeslide.setRange(0, 100)
        volumeslide.setSingleStep(5)
        volumeslide.setPageStep(10)
        volumeslide.setValue(int(getsongvolume()*100))
        volumeslide.valueChanged.connect(self.changevolume)
        volumeslide.setFixedSize(50, 100)
        
        self.songprogress = QSlider(Qt.Orientation.Horizontal)
        self.songprogress.setRange(0,100)
        self.songprogress.setValue(10)
        self.songprogress.setSingleStep(1)
        self.songprogress.sliderPressed.connect(self.seekstarted)
        self.songprogress.sliderReleased.connect(self.seekreleased)
        self.songprogress.sliderMoved.connect(self.slidermoved)
        self.songprogress.setFixedSize(280, 60)
        
        self.databasedisplay = QLabel()
        self.databasedisplay.setMinimumSize(0, 0)
        self.databasedisplay.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.databasedisplay.setStyleSheet("border: 1px solid #444; background-color: #1c1c1c;")
        self.databasedisplay.setScaledContents(True)
        self.databasedisplay.setMinimumSize(0, 0)
        self.databasedisplay.setMaximumSize(400,200)
        self.databasedisplay.setFixedSize(400, 200)
        self.databasedisplay.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.databasedisplay.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.databasedisplay.setWordWrap(True)
        self.databasedisplay.hide()
        
        self.Prev10 = QPushButton()
        self.Next10 = QPushButton()
        self.Skipto = QPushButton()
        self.Next10.setText(">")
        self.Prev10.setText("<")
        self.Skipto.setText("Skip to:")
        displaycontrols = """
          QPushButton {
          background-color: #333;
          color: white;
          border: 1px solid #444;
          border-radius: 2px;
          padding: 2px;
          font-size: 12px;
          }

          QPushButton:hover {
           background-color: #505050;
          }

          QPushButton:pressed {
            background-color: #2e2e2e;
          }"""
        self.Next10.setStyleSheet(displaycontrols)
        self.Prev10.setStyleSheet(displaycontrols)
        self.Skipto.setStyleSheet(displaycontrols)
        self.Prev10.hide()
        self.Next10.hide()
        self.Skipto.hide()

        volumeslider_layout = QVBoxLayout()
        self.volume_label = QLabel(f"{volumeslide.value()}%")
        self.volume_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        volumeslider_layout.addWidget(volumeslide, 0, alignment=Qt.AlignmentFlag.AlignCenter)
        volumeslider_layout.addWidget(self.volume_label)
        volumeslider_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.skiptonum = QLineEdit(self)
        self.skiptonum.setPlaceholderText("Song ID to Jump To")
        self.skiptonum.adjustSize()

        
        onlyInt = QIntValidator()
        onlyInt.setRange(0, 1000000)
        self.skiptonum.setValidator(onlyInt)
        self.skiptonum.hide()
      
        
        layout = QHBoxLayout()
        layout.setContentsMargins(1, 0, 0, 1)
        layout.addWidget(prevbutton)
        layout.addWidget(self.pausebutton)
        layout.addWidget(skipbutton)
        
        timedlayout = QHBoxLayout()
        timedlayout.addWidget(self.currenttime)
        timedlayout.addWidget(self.songprogress)
        timedlayout.addWidget(self.totaltime)
     
        
        groupedlayout = QVBoxLayout()
        groupedlayout.setContentsMargins(0, 0, 0, 0) 
        groupedlayout.setSpacing(0)
        groupedlayout.addWidget(self.currentsong,alignment=Qt.AlignmentFlag.AlignCenter)
        groupedlayout.addLayout(timedlayout)
        groupedlayout.addLayout(layout)
       
        volandtimecontrols = QHBoxLayout()
        volandtimecontrols.addLayout(groupedlayout)
        volandtimecontrols.addLayout(volumeslider_layout)
        
        
        skipcontrols = QHBoxLayout()
        skipcontrols.addWidget(self.Skipto)
        skipcontrols.addWidget(self.skiptonum)
        
        displaylayout = QGridLayout()
        displaylayout.setContentsMargins(0,0,0,0)
        displaylayout.setSpacing(2)
        displaylayout.addWidget(self.databasedisplay,0,1,alignment=Qt.AlignmentFlag.AlignCenter)
        displaylayout.addWidget(self.Prev10, 1,0,alignment=Qt.AlignmentFlag.AlignLeft)
        displaylayout.addLayout(skipcontrols, 1,1,alignment=Qt.AlignmentFlag.AlignCenter)
        displaylayout.addWidget(self.Next10, 1,2,alignment=Qt.AlignmentFlag.AlignRight)
        
        outerlayout = QVBoxLayout()
        outerlayout.setContentsMargins(10, 10, 10, 10) 
        outerlayout.setSpacing(10)
        outerlayout.addLayout(displaylayout)
        outerlayout.addLayout(volandtimecontrols)
        
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: #2b2b2b; color: white;")
        self.content_widget.setLayout(outerlayout)
        
        self.pausebutton.clicked.connect(self.start)
        skipbutton.clicked.connect(self.skip)
        prevbutton.clicked.connect(self.prevsong)
        self.Prev10.clicked.connect(self.displayprev)
        self.Next10.clicked.connect(self.displaynext)
        self.Skipto.clicked.connect(self.skipping)
        
        mainlayout.addWidget(self.content_widget)
        mainwidget.setLayout(mainlayout)
       
        
        border_frame = QFrame()
        border_frame.setObjectName("BorderFrame")
        border_frame.setStyleSheet("""
          #BorderFrame {
           border: 1px solid #333;
           border-radius: 6px;  
          }
         """)
        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.addWidget(mainwidget)
        border_frame.setLayout(border_layout)
        
        self.setCentralWidget(border_frame)

        self.timer = QTimer()
        self.timer.timeout.connect(self.getprogress)
        self.timer.start(200)
        self.last_song_path = None
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        
      

        
    def displayprev(self):
        if self.displaymin <= 0: 
            return
        self.displaymin = self.displaymin - 10
        self.displaymax = self.displaymax -10
        self.databasedisplay.setText(datadisplay(self.displaymin,self.displaymax))
        
        
    def displaynext(self):
        global songlist
        if self.displaymax > len(songlist):
            return
        self.displaymin = self.displaymin + 10
        self.displaymax = self.displaymax + 10
        self.databasedisplay.setText(datadisplay(self.displaymin,self.displaymax))
    
    def handle_displaychanged(self, mode):
     if mode == "full":
        self.showdatadisplay(True)
        self.databasedisplay.setText(datadisplay(self.displaymin,self.displaymax))
     else:
        self.showdatadisplay(False)
        self.databasedisplay.setText("")
     self.updateGeometry() 
     self.adjustSize()
      
        
    def showdatadisplay(self, visible):
     self.databasedisplay.setVisible(visible)
     self.Prev10.setVisible(visible)
     self.Next10.setVisible(visible)
     self.skiptonum.setVisible(visible)
     self.Skipto.setVisible(visible)
     if not visible:
        self.databasedisplay.clear()
     
    def skipping(self):
        if  self.skiptonum.text() != "":
         try:
          num = int(self.skiptonum.text())
          self.skiptonum.clear()
          if num != 0:
           playspecificsong(num - 1 )
         
         except ValueError:
             print(f"Invalid input: {self.skiptonum.text()}")
        return
     
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
               
    def start(self):
       global paused, songlist,current_song_index
       if not pygame.mixer.music.get_busy() and not paused:
           playsongs()
           self.pausebutton.setText("||")
           if songlist:
            self.currentsong.setText(songlist[current_song_index][1] + " by " +songlist[current_song_index][4])
           else:
            self.pausebutton.setText(">")
           self.songprogress.setValue(0)
           self.playback_offset = 0.0 
       elif paused:
          unpausesong()
          self.pausebutton.setText("||")
       else:
           pausesong()
           self.pausebutton.setText(">")
    
    def skip(self):
        global songlist, current_song_index
        movetonextsong()
        window.update_ui_for_current_song()
    
    def prevsong(self):
        global songlist, current_song_index
        if current_song_index > 0:
         skiptoprevsong()
         window.update_ui_for_current_song()
    
    def changevolume(self,value):
        setvolume(value)
        self.volume_label.setText(f"{value}%")
    
    
    def getprogress(self):
     global songs_loaded, songlist, current_song_index, paused, current_song_path
     if not pygame.mixer.music.get_busy() and not paused:
      return
    # Check for end of song if not paused
     if songs_loaded and not pygame.mixer.music.get_busy() and not paused:
        if current_song_index + 1 < len(songlist):
            current_song_index += 1
            filepath = songlist[current_song_index][2]
            musicplayer(filepath)
            self.currentsong.setText(songlist[current_song_index][1] + " by " + songlist[current_song_index][4])
            self.songprogress.setValue(0)
            self.playback_offset = 0.0
            self.last_song_path = filepath

            if current_song_index + 1 < len(songlist):
                musicaddtoqueue(songlist[current_song_index + 1][2])
        else:
            stopsong()
            self.currentsong.setText("")
            self.last_song_path = None
        paused = False
        return

    # Skip progress update while seeking or cooling down
     if self.user_is_seeking or self.seek_cooldown > 0:
        if self.seek_cooldown > 0:
            self.seek_cooldown -= 1
        return

     if not songlist or not songs_loaded:
        self.songprogress.setValue(0)
        return

    # Update progress slider
     position = self.getsongposition()
     duration = self.getsongduration()

     if duration <= 0 or position < 0:
        self.songprogress.setValue(0)
    
     if not paused and songs_loaded and duration > 0 and (duration - position) <= 1.0:
      movetonextsong()
      return
     
     value = int((position / duration) * 100)
     self.songprogress.setValue(value)
         
     self.currenttime.setText(self.sTOm(position))
     self.totaltime.setText(self.sTOm(duration))
         
         
    def sTOm(self,seconds):
        if seconds < 0:
            seconds = 0
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}:{s:02}"
         
    def seekstarted(self):
     self.timer.stop()  
     self.was_paused = paused  
     self.user_is_seeking = True

    def seekreleased(self):
     global paused
     value = self.songprogress.value()
     duration = self.getsongduration()
     new_position = (value / 100) * duration
     
     if new_position < 0:
      new_position = 0
     elif new_position > duration:
      new_position = duration
     self.setsongposition(new_position)  
     if self.was_paused:
        paused = True
        pygame.mixer.music.pause()
     else:
        paused = False
     self.user_is_seeking = False
     self.timer.start(200)

    def getsongduration(self):
        global songlist, current_song_duration, current_song_index
        if not songlist:
            return 0
        if 0<= current_song_index < len(songlist):
            try:
                 duration = songlist[current_song_index][3]
                 if duration is not None:
                    return float(duration)
            except IndexError:
             print(f"Error: songlist[{current_song_index}] has no duration.")
            except ValueError:
             print("Error: duration is not a float.")
        return 0


        
    def getsongposition(self):
      if pygame.mixer.music.get_busy() and songlist:
        pos_ms = pygame.mixer.music.get_pos()  # returns milliseconds
        if pos_ms == -1:
         return self.playback_offset  # Not playing
        return self.playback_offset + pos_ms / 1000.0 
      return self.playback_offset
    
    def setsongposition(self, seconds: float):
        global paused
        if songlist:
         self.playback_offset = seconds 
         pygame.mixer.music.play(start=seconds)
         self.seek_cooldown = 5
         if paused:
             pygame.mixer.music.pause()
             
    def update_ui_for_current_song(self):
     global songlist, current_song_index
     if not songlist:
        return
     self.currentsong.setText(songlist[current_song_index][1] + " by " + songlist[current_song_index][4])
     self.songprogress.setValue(0)
     self.playback_offset = 0.0
     self.last_song_path = songlist[current_song_index][2]
         
    def slidermoved(self, value):
     duration = self.getsongduration()
     new_time = (value / 100) * duration
     self.currenttime.setText(self.sTOm(new_time))
    
#creates the instance of the window and begins the music player functions    
def createwindow():
    global window
    setup()
    app = QApplication([])
    window = MainWindow()
    window.show()
    last_size = {'width': 0, 'height': 0}  # Store last size hint to compare
    def print_size():                                                               #tracks the hieght and width of the music player if it changes the GUI updates to new size
         size_hint = window.sizeHint()
         if size_hint.height() != last_size['height'] or size_hint.width() != last_size['width']:
            window.resize(size_hint)
            last_size['width'] = size_hint.width()
            last_size['height'] = size_hint.height()
    timer = QTimer()
    timer.timeout.connect(print_size)
    timer.start(100) 
    app.exec()


        
##########################
#  Music Player Code
##########################

#takes in a song index and then jumps to it if it is within the songlist
def playspecificsong(songid):
    global songlist, current_song_index,window
    if not songlist:
        return
    if 0 <= songid < len(songlist):                    #if the index is within the songlist bounds jump to it and set current song to it
        current_song_index = songid
        songtoplay = songlist[songid][2]
        musicplayer(songtoplay)                        #immediately stop the player and switch songs
        window.update_ui_for_current_song()            #update on screen ui to show the new song
    
#plays a passed in songfile if the file path exists    
def musicplayer(filepath):                             
   global current_song_path
   current_song_path = filepath
   
   try:                                               #try to load the file passed in into the music player and start
    pygame.mixer.music.load(filepath)
    pygame.mixer.music.play()
    
    if window:                                       #sets the last played song and updates the ui
        window.last_song_path = filepath
        window.update_ui_for_current_song()
   except Exception as e:
        print(f"Error playing song: {e}")

#skips to next song based on index within the songlist
def movetonextsong():
    global current_song_index, songlist,window
    if not songlist:
        return
    if current_song_index + 1 < len(songlist):       #if the next song is without the bounds of the songlist moved to it and update variables
        current_song_index += 1
        next_path = songlist[current_song_index][2]
        musicplayer(next_path)
        window.songprogress.setValue(0)
        window.playback_offset = 0.0
    else:
        stopsong()                                  #if at the end of the playlist stop playing
    
#allows for the volume of the of the player to be set based on a passed in double
def setvolume(loudness):                            
    volume = max(0.0,loudness/100)
    pygame.mixer.music.set_volume(volume)

#stops the music player  
def stopsong():
    pygame.mixer.music.stop()
    
#pauses the current song but allows for it to be restarted at the current position later pm    
def pausesong():
    global paused, window
    paused = True
    if pygame.mixer.music.get_busy():
        pos_ms = pygame.mixer.music.get_pos()
        if pos_ms != -1:
            window.playback_offset += pos_ms / 1000.0
    pygame.mixer.music.pause()

#if the song is paused resumes it if not does nothing    
def unpausesong():
    global paused
   
    if paused:
        pygame.mixer.music.unpause()
        paused = False
    else:
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.play()

#restarts the current song
def restartsong():
    pygame.mixer.music.rewind()

#ends to song    
def endsongs():
    pygame.mixer.music.unload()
    
#gets the current value of the volume slider    
def getsongvolume():
    return pygame.mixer.music.get_volume()

#addes the next song to a queue
def musicaddtoqueue(nextname):
    pygame.mixer.music.queue(nextname)


#currently fetches from the database all songs at once -> may take time to load if large amount of songs
#goal is to change ot load one song at a time based on the current index and queue
def loadsongsfromdatabase(db_name='songdatabase.db'):
    musicfile = sqlite3.connect(db_name)
    cursor = musicfile.cursor()
    cursor.execute("SELECT id, songname, filepath, songduration, artist FROM files")
    songs = cursor.fetchall()
    musicfile.close()
    return songs

#when the previous button is pressed changes the current index by decrementation and then plays the new current song
def skiptoprevsong():
    global current_song_index, songlist
    if not songlist:
        return

    if current_song_index > 0:
     current_song_index -= 1
     filepath = songlist[current_song_index][2]
     
    if paused:
     pygame.mixer.music.load(filepath)
    else:
     musicplayer(filepath)

#function that controls most of the music player action -> calls almost all of the above music player control functions
def playsongs():
    global current_song_index, songlist, paused,songs_loaded,window
    songlist = loadsongsfromdatabase()
    
    if songlist:
        current_song_index = 0
        filepath = songlist[current_song_index][2]
        musicplayer(filepath)
        songs_loaded = True 
        window.songprogress.setValue(0)
        window.playback_offset = 0.0

#prepares for the music player to be startd ->must be called before songs can be played
def setup():
    global songs_loaded
    pygame.init()
    pygame.mixer.init()
    pygame.mixer.music.set_volume(0.2)
    


############################
#  Database Code
############################

#creates a database if it doesnt already exist
def create_file_database(db_name='songdatabase.db'): 
 musicfiles = sqlite3.connect(db_name)                                  #connects to database file
 cursor = musicfiles.cursor()                                           #creates cursor to commit CRUD
                                                                        #creates table named files if it does not exist
 cursor.execute('''                                                    
    CREATE TABLE IF NOT EXISTS files(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        filepath TEXT NOT NULL,
        songduration REAL,
        artist TEXT,
        songname TEXT
    )         
''')
 musicfiles.commit()                                                     #commits/saves changes to database file
 musicfiles.close()                                                      #closes connection to confirm changes

#prints out information about the songs in the database
def showdatabase(db_name='songdatabase.db'):                           
    musicfiles = sqlite3.connect(db_name)                                #connects to database
    cursor = musicfiles.cursor()                                         #creates  cursor to move/select items
    cursor.execute("SELECT id, songname, artist, songduration FROM files") #fetches id, songname, artist and duration from the table
    table = cursor.fetchall()                                            #returns all items from the table/ database
    for row in table:                                                    #prints every row of data 
        print(row) 
    musicfiles.close()                                                   #closes connection to database/table without any changes

#adds songs to the database if theyre not already in it
def addtodatabase(filename, filepathname, duration, artist, songname, db_name='songdatabase.db'):
    musicfiles = sqlite3.connect(db_name)                                #connects to database file
    cursor = musicfiles.cursor()                                         #creates cursor to do changes to db
    
    cursor.execute(                                                      #fetches filepath and name from database if already in it
        "SELECT id FROM files WHERE filename = ? AND filepath = ?",
        (filename, filepathname)
    )
    exists = cursor.fetchone()                                           #fetches the passsed in item if present in database
    
    if not exists:                                                       #if item is not in the database adds it to table
      cursor.execute("INSERT INTO files (filename , filepath, songduration, artist, songname) VALUES ( ?, ?, ?,?,?)", (filename, filepathname, duration, artist,songname))
      
    musicfiles.commit()                                                   #commits changes
    musicfiles.close()                                                    #closes connnection to confirm changes

#if the songs are no longer in the folder removes them from the database
def removefromdatabase(db_name='songdatabase.db'):                     
    musicfiles = sqlite3.connect(db_name)                                 #connects to the database file
    cursor = musicfiles.cursor()                                          #creates a cursor to select items from database
    cursor.execute("SELECT id, filepath FROM files")                      #fetches the id and filepath of items within table
    all_rows = cursor.fetchall()                                          #gets all items from within the table

    for file_id,  filepath in all_rows:                                   #loops through all items within the table and checks if theyre accessable
        if not os.path.exists(filepath):                                  #checks if path to file exists
            cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))  #if the path is not available removes the item based on selected id
            
    musicfiles.commit()                                                    #commits changes to the database 
    musicfiles.close()                                                     #closes connection to confirm changes
    
    vacuum_conn = sqlite3.connect(db_name)                                 #reconnects to database file
    vacuum_conn.execute("VACUUM")                                          #garbage collection of empty or unused space within table/database
    vacuum_conn.commit()                                                   #commits changes to database file
    vacuum_conn.close()                                                    #closes connection to confirm changes


def resetdatabase(db_name='songdatabase.db'):                              #resets the file and add the files back in 
    musicfiles = sqlite3.connect(db_name)                                  #connects to the current database
    cursor = musicfiles.cursor()                                           #creates a cursor to allow items to be pulled from the database
    
    cursor.execute("SELECT filename, filepath, songduration, artist, songname FROM files") #tells cursor to pull all information other than index
    all_entries = cursor.fetchall()                                        #pulls information from database
    
    cursor.execute("DROP TABLE IF EXISTS files")                           #drops/deletes the table if it exists
    musicfiles.commit()                                                    #commits changes
    musicfiles.close()                                                     #closes connection to the database
    
    musicfiles = sqlite3.connect(db_name)                                  #reconnects to the databse file
    cursor = musicfiles.cursor()                                           #creates cursor to travel through file
    create_file_database()                                                 #creates database since it was delted
    
    cursor.executemany(
        "INSERT INTO files (filename, filepath, songduration, artist, songname) VALUES (?, ?, ?, ?,?)",all_entries #adds all items back into the new database
    )
    musicfiles.commit()                                                    #commits changes to the database
    musicfiles.close()                                                     #closes connection to the database
    

def getfilesfromfolder(db_name='songdatabase.db'): 
    currentdirectory = os.getcwd()                                         #gets the current working directory
    placetocheckforsongs = os.path.join(currentdirectory, "library","SONG")#adds the library/SONG folder to the string

    if not os.path.exists(placetocheckforsongs):                           #checks for the folder directory
        return                                                             #throws error if folder is not found

    supported_extensions = ('.mp3', '.flac')                               #creates a type of file extension to check for
    files_os = [
        f for f in os.listdir(placetocheckforsongs)                        #reads songs from folder and adds them to a list if end in the right file types
        if f.lower().endswith(supported_extensions) and os.path.isfile(os.path.join(placetocheckforsongs, f))
    ]

    for file_name in files_os:                                             #creates a filepath and other information need to add a file to the database
        file_path = os.path.join(placetocheckforsongs, file_name)
        duration_seconds = None
        artist = None
        songname = None
        try:
            audio = File(file_path, easy=True)
            if audio and audio.info:
                duration_seconds = round(audio.info.length, 2)
            if audio:
                artist = audio.get("artist", [None])[0]
            if audio:
                songname = audio.get("title", [None])[0]
        except Exception as e:                                             #if not song infromation is found throws an error
            print(f"Could not read metadata for {file_name}: {e}")

        addtodatabase(file_name, file_path, duration_seconds, artist, songname, db_name=db_name) #adds the songs/files into the database
        
def datadisplay(min: int, max: int, db_name='songdatabase.db'):            #creates the string that is displayed in the full window
     musicfiles = sqlite3.connect(db_name)                                 #creates connection to the database
     cursor = musicfiles.cursor()                                          #creates a cursor within the database
     limit = max - min                                                     #calculates the range of data to show
     offset = min
     cursor.execute("SELECT id, songname, artist, songduration FROM files LIMIT ? OFFSET ?", (limit,offset,)) #fetches the data from the table
     table = cursor.fetchall()                             
     output = []
     for row in table:                                                     #loops through all items pulled from database till all are in a single string
        time =""
        if row[3] < 0:                                                     #makes sure that the duraction is not 0
           row[3] = 0
        m = int(row[3] // 60)                                              #converts the duration into the expectic typical format
        s = int(row[3] % 60)
        time = f"{m}:{s:02}"
        line = f"ID: {row[0]} {row[1]} By: {row[2]} Duration {time}"       #creates the lines to display
        output.append(line)
     musicfiles.close() 
     return "\n".join(output)                                              #converts all the lines into a single long string

def main():
#   resetdatabase()                                                        #rebuilds database if issue
    create_file_database()                                                 #checks for database and builds if not present
    removefromdatabase()                                                   #checks database and removes files not present in folder
    getfilesfromfolder()                                                   #checks database and adds song from folder into it
    createwindow()                                                         #creates the GUI and resoureces needed
    
main()