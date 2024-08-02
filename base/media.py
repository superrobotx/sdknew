from PIL import Image as PILImage
import librosa
import asstosrt, ass, srt
import logging, av
from scipy.io import wavfile 
from pydub import AudioSegment
from pydub.silence import split_on_silence
import soundfile as sf
import matplotlib.pyplot as plt
import librosa, signal, cv2
from bs4 import BeautifulSoup
import _queue

from .utils import *

class Image:
  '''
  image wrapper
  '''
  _exts = ['.jpg', '.gif', '.jpeg', '.png']
  
  @classmethod
  def is_image(cls, fpath):
    return os.path.splitext(fpath)[1].lower() in cls._exts
  
  @property
  def height(self):
    return self.data.height
  
  @property
  def width(self):
    return self.data.width
    
  def __init__(self, data) -> None:
    self.data = data
      
  def from_base64(data):
    data = base64.b64decode(data)
    data = PILImage.open(io.BytesIO(data))
    return Image(data)
  
  def from_bytes(data):
    data = PILImage.open(io.BytesIO(data))
    return Image(data)
  
  def from_ndarray(data):
    data = PILImage.fromarray(data)
    return Image(data)
  
  def from_PIL(data):
    return Image(data)
  
  def to_PIL(self):
    return self.data
  
  def from_av_frame(self, data):
    data = data.to_image()
    return Image(data)

  def list_db():
      return list(db.Hash('images').keys())

  def from_file(fpath):
      im = PILImage.open(fpath)
      return Image(im)

  def from_db(name):
      db = Database(decode_responses=False)
      db_images = db.Hash('images')
      img = db_images[name]
      if img is None:
          return

      return Image(pickle.loads(img))

  @property
  def shape(self):
      return self.to_ndarray().shape
      return self.data.width, self.data.height

  def save_to_db(self, name):
      db_images = db.Hash('images')
      db_images[name] = pickle.dumps(self.data)

  def as_wallpaper(self):
      tmpf = '/home/haha/tmp/tmp.{}'.format(self.data.format)
      self.data.save(tmpf)
      os.system(
      f'gsettings set org.gnome.desktop.background picture-uri "{tmpf}"')

  def to_ndarray(self):
      img = np.array(self.data)
      if img.shape[-1] == 4:
          img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
      return img

  def to_jpeg(data):
      data = base64.b64decode(data) if type(data) == str else data  
      if type(data) == bytes:
          return data
      elif type(data) == np.ndarray:
          img = PILImage.fromarray(data)
          return img.tobytes()
      else:
          return data.tobytes()

  def _image_to_bytes(self, format) -> bytes:
      imgByteArr = io.BytesIO()
      self.data.save(imgByteArr, format=format)
      imgByteArr = imgByteArr.getvalue()
      return imgByteArr

  def to_jpeg(self):
      return self._image_to_bytes('jpeg')

  def to_png(self):
      return self._image_to_bytes('png')
  
  def to_file(self, fpath):
    ext = os.path.splitext(fpath)[-1].lower()
    if ext in ['.jpg', '.jpeg']:
      with open(fpath, 'wb') as f:
        f.write(self.to_jpeg())
    elif ext in ['.png']:
      with open(fpath, 'wb') as f:
        f.write(self.to_png())
    else:
      raise Exception('unknown type', fpath)
    
  def to_base64(self, foramt='png'):
    if foramt == 'jpg':
      bytes = self.to_jpeg()
    else:
      bytes = self.to_png()
    return base64.b64encode(bytes).decode('utf8')
  

  def display(self):
      from IPython import display
      display.display(self.data)

  def _ipython_display_(self):
      self.display()
      
  def resize(self, w, h):
      return Image.from_PIL(self.to_PIL().resize((w,h)))

  def reshape(self, size):
      size = (size[1], size[0])
      return Image.from_PIL(self.to_PIL().resize(size))

  ''' 
  def resize(self, area):
      w = self.data.width
      h = self.data.height
      rate = np.sqrt(area/(w*h))
      data = self.data.resize((int(w*rate), int(h*rate)))
      return Image(data)
  '''

  def save(self, fpath):
      try:
          self.data.save(fpath)
      except KeyError:
          p, ext = os.path.splitext(fpath)
          self.data.save(p + ".png")

  def to_thumbnail(self, size=(100,100)):
      data = self.data.copy()
      data.thumbnail(size)
      return Image(data)

class Wave:
  ''' 
  wave file utils
  '''
  def _resample(self, wave, fs1, fs2):
    resampling_ratio = fs2 / fs1
    # Resample the wave to the new sample rate
    resampled_wave = signal.resample(wave, int(len(wave) * resampling_ratio))
    return resampled_wave
  
  def normalize(self):
    tmp_file = tempfile.mkstemp(suffix='.wav')[1]
    self.to_file(tmp_file)

    waveform, self.fs = librosa.load(tmp_file, sr=self.sampler_rate)
    normalized_waveform = librosa.util.normalize(waveform)
    self.data = normalized_waveform

  @property
  def sampler_rate(self):
    return self.sr

  @sampler_rate.setter
  def sampler_rate(self, fs):
    fpath = tempfile.mkstemp(suffix='.wav')[1]
    self.to_file(fpath)
    self.data, self.sr = librosa.load(fpath, sr=fs)
    assert self.sr == fs

  def plot(self):
    if len(self.data.shape) > 1:
      x, y =  self.data.shape
      if x > y:
        data = self.data[:, 0]
      else:
        data = self.data[0, :]
    else:
      data = self.data
    time = np.arange(len(data)) / self.sampler_rate
    plt.plot(time, data,  color=(0.5, 0.5, 0.5))
  
  @property
  def dtype(self):
    return self.data.dtype
  
  
  @dtype.setter
  def dtype(self, dtype):
    if self.dtype == dtype:
      return
    
    if dtype == np.float32:
      import librosa 
      audio_file = io.BytesIO()
      sf.write(audio_file, self.data, self.sampler_rate, format='wav')
      audio_file.seek(0)
      wav, _ = librosa.load(audio_file, sr=self.sampler_rate, dtype=dtype, mono=True)
      self.data = wav
    
    elif dtype == np.int16:
      self.data = (self.data* 32767).astype(np.int16)

    else:
      raise Exception('only support float32 int16')
        

  def __init__(self, data, sr):
    self.data = data
    self.sr = sr

  def __len__(self):
    return self.data.shape[0]
  
  def play(self):
    sd.play(*self.to_ndarray())
  
  def sum( waves):
    if not waves:
      print('funck')
      return
    
    wave = waves[0]
    for i in range(1, len(waves)):
      wave += waves[i]
    return wave

  def slice(self, st, ed):
    sr = self.sr
    st_i = max(0, int(sr*st))
    ed_i = min(int(sr*ed),  len(self)-1)
    return Wave.from_ndarray(self.data[st_i:ed_i, :], self.sr)
 
  def from_mp3_file(fpath) :
    audio = AudioSegment.from_mp3(fpath)
    
    fs = audio.frame_rate
    ff = io.BytesIO()
    audio.export(ff, format='wav')
    ff.seek(0)
    
    return Wave.from_bytes(ff.read())
  
  def from_audio_segment(segment):
    return Wave.from_bytes(segment.export(format='wav').read())
  
  def from_mp3_bytes(bytes):
    f = io.BytesIO()
    f.write(bytes)
    
    f.seek(0)
    audio = AudioSegment.from_mp3(f)
    
    ff = io.BytesIO()
    audio.export(ff, format='wav')
    ff.seek(0)
    
    return Wave.from_bytes(ff.read())

  def from_file(fpath, ext=None):
    if os.path.splitext(fpath)[-1] == '.mp3' or ext == '.mp3':
      return Wave.from_mp3_file(fpath)
    else:
      sr, wav = wavfile.read(fpath)
      return Wave(wav ,sr)

  def from_base64(code):
    f = io.BytesIO()
    bs = base64.b64decode(code.encode('utf8'))
    f.write(bs)
    f.seek(0)
    sr, data = wavfile.read(f)
    return Wave(data, sr)

  def from_bytes(bs):
    f = io.BytesIO()
    f.write(bs)
    f.seek(0)
    sr, data = wavfile.read(f)
    f.close()
    return Wave(data, sr)

  def from_ndarray(data, sr):
    if len(data.shape) == 1:
      data.shape = (-1, 1)
    x,y = data.shape
    if x < y:
      data.shape = y,x
    return Wave(data, sr)
  
  def to_audio_segment(self):
    return AudioSegment(self.to_bytes())

  def to_ndarray(self):
    return self.data, self.sampler_rate

  def to_file(self, fpath):
    if os.path.splitext(fpath)[-1] == '.mp3':
      with open(fpath, 'wb') as f:
        f.write(self.to_mp3_bytes())
    else:
      wavfile.write(fpath, self.sr, self.data)

  def to_base64(self):
    bs = self.to_bytes()
    return base64.b64encode(bs).decode('utf8')

  def to_mp3_bytes(self):
    wave_data = self.data.astype(np.int16)
    if len(wave_data.shape) == 1:
      channels = 1
    else:
      channels=min(min(*wave_data.shape),2)
    with tempfile.NamedTemporaryFile(suffix='.wav') as f:
      sf.write(f, wave_data, self.sampler_rate)
      f.seek(0)
    
      audio_segment = AudioSegment.from_wav(
          f,
          #sample_width=2,  # 2 bytes per sample (16-bit audio)
          #frame_rate=self.sampler_rate,
          #channels=channels
      )
      
    with tempfile.NamedTemporaryFile(suffix='.mp3') as f:
      audio_segment.export(f, format="mp3")
      f.seek(0)
      mp3_bytes = f.read()
    return mp3_bytes

  def to_bytes(self):
    f = io.BytesIO()
    wavfile.write(f, self.sr, self.data)
    f.seek(0)
    bs = f.read()
    f.close()
    return bs
  
  def __add__(self, other):
    #if isinstance(other, Wave):
    if other.__class__.__name__ == self.__class__.__name__:
      np1, fs1 = self.to_ndarray()
      np2, fs2 = other.to_ndarray()
      np1 = np.squeeze(np1)
      np2 = np.squeeze(np2)
      
      assert fs1 == fs2
      assert len(np1.shape) == len(np2.shape)
      if len(np1.shape) > 1:
        x, y = np1.shape
        if x < y:
          np1 = np1.T
        x, y = np2.shape
        if x < y:
          np2 = np2.T
          
      np_add = np.concatenate([np1, np2], axis=0)
      np_add = np.squeeze(np_add)
      return Wave.from_ndarray(np_add, fs1)
      
    else:
      return NotImplemented


class Video:
  ''' 
  pyav wrapper, video utils,
  '''
  class AudioFrame:
    def __init__(self, frame, *args, **argv):
      #super().__init__(*args, **argv)
      self.type = 'audio'
      arr = frame.to_ndarray()
      x, y = arr.shape
      if x < y:
        arr = arr.T


      '''
      if x > y:
        arr = arr.T
      arr = librosa.resample(arr, frame.sample_rate, 16000)
      if x < y:
        arr = arr.T
      self.arr = arr
      self.sample_rate = 16000
      self.time_pos = frame.pts * frame.time_base.numerator / frame.time_base.denominator
      self.n_blocksize, self.n_channel = arr.shape
      self.dtype = arr.dtype
      self.frame = frame
      ''' 



      self.arr = arr
      self.sample_rate = frame.sample_rate
      self.time_pos = frame.pts * frame.time_base.numerator / frame.time_base.denominator
      self.n_blocksize, self.n_channel = arr.shape
      self.dtype = arr.dtype
      self.frame = frame

  class VideoFrame:
    def __init__(self, frame:av.video.frame.VideoFrame, *args, **argv):
      #super().__init__(*args, **argv)
      self.type = 'video'
      self.frame = frame

      ''' 
      imgByteArr = io.BytesIO()
      self.img.save(imgByteArr, format='jpeg')
      self.base64 = base64.b64encode(imgByteArr.getvalue()).decode('utf8')
      '''
        

    _time_pos = None
    @property
    def time_pos(self):
      if self._time_pos is None:
        frame = self.frame
        try:
          self._time_pos = frame.pts * frame.time_base.numerator / frame.time_base.denominator
        except Exception as e:
          print(e)
          self._time_pos = 0
      return self._time_pos
    
    _image = None
    @property
    def image(self):
      if self._image is None:
        frame = self.frame
        img = frame.to_image()
        self._image = Image.from_PIL(img)
      return self._image
    
    _jpgBase64 = None
    @property
    def jpgBase64(self):
      if self._jpgBase64 is None:
        self._jpgBase64 = base64.b64encode(self.image.to_jpeg()).decode('utf8')
      return self._jpgBase64
    

      

      
  def __init__(self, fpath):
    # this will silence ffmpeg output
    self.lock = Lock()
    av.logging.set_level(logging.INFO)
    
    self.container:av.InputContainer = av.open(fpath)
    self.time_base = self.audio_stream.time_base.denominator
    self.duration  = self.container.duration/1000000

  _audio_stream = None  
  @property
  def audio_stream(self):
    container = self.container
    if self._audio_stream is None:
      self.lock.acquire()
      for s in container.streams:  
        if s.type == 'audio':
          self._audio_stream = s
          break
      self.lock.release()
    return self._audio_stream
      

  _video_stream = None  
  @property
  def video_stream(self):
    container = self.container
    if self._video_stream is None:
      self.lock.acquire()
      for s in container.streams:
        if s.type == 'video':
          self._video_stream = s
          break
      self.lock.release()
    return self._video_stream

  @property
  def next_audio_frame(self):
    stream = self.audio_stream
    self.lock.acquire()
    frame = self.AudioFrame(next(self.container.decode(stream)))
    self.lock.release()
    return frame

  @property
  def next_video_frame(self):
    stream = self.video_stream
    self.lock.acquire()
    frame = self.VideoFrame(next(self.container.decode(stream)))
    self.lock.release()
    return frame

  @property
  def video_time_pos(self):
    return self.next_video_frame.time_pos

  @video_time_pos.setter
  def video_time_pos(self, time_pos):
    stream = self.video_stream
    frame = self.next_video_frame.frame

    pts = time_pos / frame.time_base.numerator * frame.time_base.denominator
    self.lock.acquire()
    self.container.seek(int(pts), stream=stream)
    self.lock.release()
    

  @property
  def audio_time_pos(self):
    return self.next_audio_frame.time_pos

  @audio_time_pos.setter
  def audio_time_pos(self, time_pos):
    self.lock.acquire()
    self.container.seek(int(self.time_base*time_pos),
              stream=self.audio_stream)
    self.lock.release()

  @property
  def fps(self):
    fps = self.video_stream.average_rate
    a, b = fps.as_integer_ratio()
    fps = a/b
    return fps

  def __len__(self):
    return self.container.size

  def _decode(self):
    ''' 
    generate audio in {'audio': ndarray} or video in {'video': Image}
    '''
    #resampler = av.AudioResampler(format=av.AudioFormat('flt'), layout=self.next_audio_frame.frame.layout_name, rate=16000)
    for packet in self.container.demux():
      try:
        for frame in packet.decode():
          if type(frame) == av.audio.frame.AudioFrame:
            ''' 
            for frame in resampler.resample(frame):
              data = self.AudioFrame(frame)
              yield data
            '''
            data = self.AudioFrame(frame)
          if type(frame) == av.video.frame.VideoFrame:
            data = self.VideoFrame(frame)
          yield data
      except Exception as e:
        print(e)
        traceback.print_exc()

  _stream = None
  @property
  def stream(self): 
    if self._stream is None:
      self._stream = self._decode()
    return self._stream

  def decode(self):
    while True:
      try:
        self.lock.acquire()
        x = next(self.stream)
        self.lock.release()
        yield x
      except StopIteration:
        print('iteration stop')
        break
        

class Subtitle:
  ''' 
  subtitle extracting and parsing
  '''
  subpath = '/media/haha/cerulean/tmp/test.{}'

  def _get_sub_type(self, fpath):
    container =av.open(fpath)
    for s in container.streams:
      if s.type == 'subtitle':
        return s.codec_context.name

  def parse(self, fpath): 
    subpath = self.subpath.format(self._get_sub_type(fpath))
    assert os.path.exists(fpath)

    if os.path.splitext(fpath)[1].lower() in ['.ass', '.srt']:
      return self._parse(fpath)
    else:

      #if os.path.exists(subpath):
        #os.remove(subpath)
      #ret = os.system(f'ffmpeg -y -i "{fpath}" -map 0:s:0 {subpath} 1>/dev/null 2>/dev/null')
      subpath = '/tmp/x.ass'
      ret = os.system(f'ffmpeg -y -i "{fpath}"  {subpath} 1>/dev/null 2>/dev/null')
      if ret == 0:
        return self._parse(subpath)

  def _parse(self, fpath) -> None:
    if os.path.splitext(fpath)[1].lower() == '.srt':
      return self.parse_srt(fpath)
    try:
      with open(fpath, 'r') as f:
        sub = self.parse1(f)
        return sub
    except Exception as e:
      print('parse1 fail, try parse2')
      with open(fpath, 'r') as f:
        sub = self.parse2(f)
    #return self.filter(sub)
    return sub

  def filter(self, sub):
    tmp = []
    for k,v in sub:
      if len(v) == 2:
        tmp.append((k,v))
    return tmp

  def parse1(self, f):
    doc = ass.parse(f.read())
    sub = Dict()
    for e in doc.events:
      st = int(e.start.total_seconds())
      ed = int(e.end.total_seconds())
      text = e.text
      if (st,ed) in sub:
        sub[(st,ed)].append(text)
      else:
        sub[(st,ed)] = [text]
    return [(k,v) for k,v in sub.items()]

  def parse2(self, f):
    srt_str = asstosrt.convert(f)

    sub = Dict()
    ext = 0
    for e in srt.parse(srt_str):
      st = e.start.total_seconds()
      ed = e.end.total_seconds()+ext
      text = e.content
      if (st,ed) in sub:
        sub[(st,ed)].append(text)
      else:
        sub[(st,ed)] = [text]
    return [(k,v) for k,v in sub.items()]

  def parse_srt(self, fpath):
    with open(fpath) as f:
      srt_str = f.read()

    sub = Dict()
    ext = 0
    for e in srt.parse(srt_str):
      st = e.start.total_seconds()
      ed = e.end.total_seconds()+ext
      text = self._strip_html_tags(e.content).replace('\n', ' ').strip()
      if (st,ed) in sub:
        sub[(st,ed)].append(text)
      else:
        sub[(st,ed)] = [text]
    return [(k,v) for k,v in sub.items()]

  def _strip_html_tags(self, html_string):
      soup = BeautifulSoup(html_string, 'html.parser')
      return soup.get_text()

  

    