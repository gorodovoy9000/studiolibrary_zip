# Copyright 2020 by Kurt Rathjen. All Rights Reserved.
#
# This library is free software: you can redistribute it and/or modify it 
# under the terms of the GNU Lesser General Public License as published by 
# the Free Software Foundation, either version 3 of the License, or 
# (at your option) any later version. This library is distributed in the 
# hope that it will be useful, but WITHOUT ANY WARRANTY; without even the 
# implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
# See the GNU Lesser General Public License for more details.
# You should have received a copy of the GNU Lesser General Public
# License along with this library. If not, see <http://www.gnu.org/licenses/>.

import re
import os
from zipfile import ZipFile, is_zipfile
from io import BytesIO

from studiovendor.Qt import QtGui
from studiovendor.Qt import QtCore

__all__ = ['ImageSequence', 'ImageSequenceWidget']


class ImageSequence(QtCore.QObject):
    DEFAULT_FPS = 24

    frameChanged = QtCore.Signal(int)

    def __init__(self, path, *args):
        QtCore.QObject.__init__(self, *args)

        self._fps = self.DEFAULT_FPS
        self._timer = None
        self._frame = 0
        self._frames = []
        self._dirname = None
        self._paused = False
        self._bytes = BytesIO()
        self._bytes_read = None

        if path:
            self.setPath(path)

    def firstFrame(self):
        """
        Get the path to the first frame.

        :rtype: str
        """
        if self._frames:
            return self._frames[0]
        return ""

    def setPath(self, path):
        """
        Set a single frame or a zip or a directory to an image sequence.
        :type path: str
        """
        if is_zipfile(path):
            self.setZipfile(path)
        elif os.path.isfile(path):
            self._frame = 0
            self._frames = [path]
        elif os.path.isdir(path):
            self.setDirname(path)

    def setZipfile(self, zip_sequence):
        """
        Set the location to the image sequence in zip.

        :type zip_sequence: str
        :rtype: None
        """

        def setBytes(zip_file):
            """
            Fill BytesIO object buffer from zip file
            for reading the sequence from memory.
            """
            with ZipFile(zip_file, 'r') as zip_file:
                self._frames = [filename for filename in zip_file.namelist()]
                with ZipFile(self._bytes, 'a') as mem:
                    for name_file in self._frames:
                        mem.writestr(name_file, zip_file.read(name_file))
            self._bytes_read = ZipFile(self._bytes, 'r')

        self._dirname = zip_sequence
        setBytes(zip_sequence)
        self.naturalSortItems(self._frames)

    def setDirname(self, dirname):
        """
        Set the location to the image sequence in directory.
        :type dirname: str
        :rtype: None
        """
        self._dirname = dirname
        if os.path.isdir(dirname):
            self._frames = [dirname + "/" + filename for filename in os.listdir(dirname)]
            self.naturalSortItems(self._frames)

    def naturalSortItems(self, items):
        """
        Sort the given list in the way that humans expect.
        :type items: list
        :rtype: None
        """
        convert = lambda text: int(text) if text.isdigit() else text
        alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
        items.sort(key=alphanum_key)

    def dirname(self):
        """
        Return the location to the image sequence.

        :rtype: str
        """
        return self._dirname

    def reset(self):
        """
        Stop and reset the current frame to 0.

        :rtype: None
        """
        if not self._timer:
            self._timer = QtCore.QTimer(self.parent())
            self._timer.setSingleShot(False)
            self._timer.timeout.connect(self._frameChanged)

        if not self._paused:
            self._bytes.close()
            self._bytes = BytesIO()
            self._bytes_read = None
            self._frame = 0
        self._timer.stop()

    def pause(self):
        """
        ImageSequence will enter Paused state.

        :rtype: None
        """
        self._paused = True
        self._timer.stop()

    def paused(self):
        """
        Return paused state of the image sequence playing.

        :rtype: bool
        """
        return self._paused

    def resume(self):
        """
        ImageSequence will enter Playing state.

        :rtype: None
        """
        if self._paused:
            self._paused = False
            self._timer.start()

    def stop(self):
        """
        Stops the movie. ImageSequence enters NotRunning state.

        :rtype: None
        """
        self._bytes.close()
        self._bytes = BytesIO()
        self._bytes_read = None
        self._timer.stop()

    def start(self):
        """
        Starts the movie. ImageSequence will enter Running state

        :rtype: None
        """
        self.reset()
        if self._dirname:
            self.setPath(self._dirname)
        if self._timer:
            self._timer.start(1000.0 / self._fps)

    def frames(self):
        """
        Return all the filenames in the image sequence.

        :rtype: list[str]
        """
        return self._frames

    def _frameChanged(self):
        """
        Triggered when the current frame changes.

        :rtype: None
        """
        if not self._frames:
            return

        frame = self._frame
        frame += 1
        self.jumpToFrame(frame)

    def percent(self):
        """
        Return the current frame position as a percentage.

        :rtype: None
        """
        if len(self._frames) == self._frame + 1:
            _percent = 1
        else:
            _percent = float((len(self._frames) + self._frame)) / len(self._frames) - 1
        return _percent

    def frameCount(self):
        """
        Return the number of frames.

        :rtype: int
        """
        return len(self._frames)

    def currentIcon(self):
        """
        Returns the current frame as a QIcon.

        :rtype: QtGui.QIcon
        """
        return QtGui.QIcon(self.currentPixmap())

    def currentPixmap(self):
        """
        Return the current frame as a QPixmap.

        :rtype: QtGui.QPixmap
        """
        if self._dirname and is_zipfile(self._dirname):
            read = self._bytes_read.read(self.currentFilename())
            pixmap = QtGui.QPixmap()
            pixmap.loadFromData(read)
            return pixmap
        else:
            pixmap = QtGui.QPixmap()
            pixmap.load(self.currentFilename())
            return pixmap

    def currentFilename(self):
        """
        Return the current file name.

        :rtype: str or None
        """
        try:
            return self._frames[self.currentFrameNumber()]
        except IndexError:
            pass

    def currentFrameNumber(self):
        """
        Return the current frame.

        :rtype: int or None
        """
        return self._frame

    def jumpToFrame(self, frame):
        """
        Set the current frame.

        :rtype: int or None
        """
        if frame >= self.frameCount():
            frame = 0
        self._frame = frame
        self.frameChanged.emit(frame)
