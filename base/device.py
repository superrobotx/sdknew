from threading import Thread, Lock
import queue, time
import sounddevice as sd
import sys
import numpy as np
from queue import Queue


class SoundDevice(Thread):
  ''' 
  local audio player, pipe numpy wave data into audio device,
  sounddevice wrapper,
  '''
  QUEUE_SIZE = 20
  def __init__(self, sample_rate, channels, blocksize, dtype):
    super().__init__()
    print('init sounddevice', f'{sample_rate}HZ', channels, blocksize)
    self.daemon = True
    self.is_playing = True
    self.queue = Queue(self.QUEUE_SIZE)
    print(sample_rate, channels)

    self.sample_rate = sample_rate
    self.channels = channels
    self.blocksize = blocksize
    self.dtype = dtype
    self.lock = Lock()
    self.lock.acquire()
    self.start()

  _volume = 0.1

  @property
  def volume(self):
    return self._volume

  @volume.setter
  def volume(self, vol):
    self._volume = max(min(vol, 1), 0)

  def close(self):
    try:
      self.is_playing = True
      self.lock.release()
      self.lock.release()
    except:
      pass

  def run(self):
    import sounddevice as sd
    outstream = sd.OutputStream(
        samplerate=self.sample_rate, 
        channels=self.channels, 
        callback=self._callback,
        blocksize=self.blocksize, 
        finished_callback=self._finish_stream,
        dtype=self.dtype,
      )

    with outstream:
      self.lock.acquire()

  def _get_audio_data(self, af):
    data = af.arr
    x, y = data.shape
    if x < y:
      data.shape = (y, x)
    #assert data.shape[0] == self.blocksize, f'{data.shape[0]} {self.blocksize}'
    return data * self.volume
  
  def clear(self):
    while True:
      try:
        self.queue.get_nowait()
      except queue.Empty:
        return

  def feed(self, af):
    self.queue.put(af)

  def _finish_stream(self):
    print('end')

  def _callback_(self, outdata, frames, time_, status):
    if status.output_underflow:
      print('Output underflow: increase blocksize?')
      #raise sd.CallbackAbort
    data = self.queue.get()
    
    if len(data) < len(outdata):
      assert False, (data.shape, outdata.shape)
      outdata[:data.shape[0], :] = data
      outdata[data.shape[0]:, :].fill(0)
      #outdata[len(data):, 1].fill(0)
      #raise sd.CallbackStop
    else:
      outdata[:] = data

  time_pos = None

  def hold(self):
    self.is_playing = False

  def release(self):
    self.is_playing = True

  def _get_silent_data(self):
    return np.zeros((self.blocksize, self.channels), dtype=self.dtype)

  def _callback(self, outdata, frames, time_, status):
    assert frames == self.blocksize
    if status.output_underflow:
        print('Output underflow: increase blocksize?')
        time.sleep(0.001)
        return self._get_silent_data()
        print('Output underflow: increase blocksize?', file=sys.stderr)
        raise sd.CallbackAbort
    assert not status
    while not self.is_playing:
      time.sleep(0.001)
    try:
      af = self.queue.get_nowait()
    except queue.Empty:
      print('sounddevice empty queue')
      af = self.queue.get()

    self.time_pos = af.time_pos
    data = self._get_audio_data(af)
    if len(data) < len(outdata):
        print('data less than expected')
        outdata[:len(data)] = data
        outdata[len(data):] = b'\x00' * (len(outdata) - len(data))
        #raise sd.CallbackStop
    else:
        outdata[:] = data