## JavascriptSubtitlesOctopus
## From https://github.com/emscripten-core/emscripten/blob/c834ef7d69ccb4100239eeba0b0f6573fed063bc/tools/tempfiles.py

# Copyright 2013 The Emscripten Authors.  All rights reserved.
# Emscripten is available under two separate licenses, the MIT license and the
# University of Illinois/NCSA Open Source License.  Both these licenses can be
# found in the LICENSE file.

import os
import shutil
import tempfile
import atexit
import stat
import sys


# Attempts to delete given possibly nonexisting or read-only directory tree or filename.
# If any failures occur, the function silently returns without throwing an error.
def try_delete(pathname):
  try:
    os.unlink(pathname)
  except OSError:
    pass
  if not os.path.exists(pathname):
    return
  try:
    shutil.rmtree(pathname, ignore_errors=True)
  except IOError:
    pass
  if not os.path.exists(pathname):
    return

  # Ensure all files are readable and writable by the current user.
  permission_bits = stat.S_IWRITE | stat.S_IREAD

  def is_writable(path):
    return (os.stat(path).st_mode & permission_bits) != permission_bits

  def make_writable(path):
    os.chmod(path, os.stat(path).st_mode | permission_bits)

  # Some tests make files and subdirectories read-only, so rmtree/unlink will not delete
  # them. Force-make everything writable in the subdirectory to make it
  # removable and re-attempt.
  if not is_writable(pathname):
    make_writable(pathname)

  if os.path.isdir(pathname):
    for directory, subdirs, files in os.walk(pathname):
      for item in files + subdirs:
        i = os.path.join(directory, item)
        make_writable(i)

  try:
    shutil.rmtree(pathname, ignore_errors=True)
  except IOError:
    pass


class TempFiles:
  def __init__(self, tmpdir, save_debug_files):
    self.tmpdir = tmpdir
    self.save_debug_files = save_debug_files
    self.to_clean = []

    atexit.register(self.clean)

  def note(self, filename):
    self.to_clean.append(filename)

  def get(self, suffix):
    """Returns a named temp file with the given prefix."""
    named_file = tempfile.NamedTemporaryFile(dir=self.tmpdir, suffix=suffix, delete=False)
    self.note(named_file.name)
    return named_file

  def get_file(self, suffix):
    """Returns an object representing a RAII-like access to a temp file
    that has convenient pythonesque semantics for being used via a construct
      'with TempFiles.get_file(..) as filename:'.
    The file will be deleted immediately once the 'with' block is exited.
    """
    class TempFileObject:
      def __enter__(self_):
        self_.file = tempfile.NamedTemporaryFile(dir=self.tmpdir, suffix=suffix, delete=False)
        self_.file.close() # NamedTemporaryFile passes out open file handles, but callers prefer filenames (and open their own handles manually if needed)
        return self_.file.name

      def __exit__(self_, type, value, traceback):
        if not self.save_debug_files:
          try_delete(self_.file.name)
    return TempFileObject()

  def get_dir(self):
    """Returns a named temp directory with the given prefix."""
    directory = tempfile.mkdtemp(dir=self.tmpdir)
    self.note(directory)
    return directory

  def clean(self):
    if self.save_debug_files:
      print(f'not cleaning up temp files since in debug-save mode, see them in {self.tmpdir}', file=sys.stderr)
      return
    for filename in self.to_clean:
      try_delete(filename)
    self.to_clean = []
