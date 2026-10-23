"""Create the immutable nearly-silent browser carrier for the K1 live engine."""
from pathlib import Path
import wave,struct
FRAMES=144019
SIGNATURE=0xb1e70a5c
def make(path):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 pcm=struct.pack('<32h',*[1 if SIGNATURE&(1<<i) else -1 for i in range(32)])+bytes((FRAMES-32)*2)
 with wave.open(str(path),'wb') as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes(pcm)
 with wave.open(str(path),'rb') as w:
  assert (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())==(1,2,48000,FRAMES)
  assert w.readframes(FRAMES)==pcm
 return path
