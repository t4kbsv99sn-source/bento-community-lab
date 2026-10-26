"""Exact K15 browser carriers. These identify live synths; they are not samples."""
from pathlib import Path
import argparse,wave,struct
FRAMES={'BENTO_Kick_K2.wav':144019,'BENTO_Synth_Snare.wav':144021,'BENTO_Synth_HiHat.wav':144023,'BENTO_Synth_Clap.wav':144025,'BENTO_Synth_Tom.wav':144027,'BENTO_Synth_Subtractive.wav':144029}
SIGNATURE=0xb1e70a5c

def make(directory):
 directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
 for name,frames in FRAMES.items():
  pcm=struct.pack('<32h',*[1 if SIGNATURE&(1<<i) else -1 for i in range(32)])+bytes((frames-32)*2)
  p=directory/name
  with wave.open(str(p),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes(pcm)
  with wave.open(str(p),'rb') as w:
   assert (w.getnframes(),w.getframerate(),w.getnchannels(),w.getsampwidth())==(frames,48000,1,2)
   assert w.readframes(frames)==pcm
 return directory
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();print(make(a.directory))
