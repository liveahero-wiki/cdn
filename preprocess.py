import os.path
import json
import re
from PIL import Image

def dumpJson(filename, obj, **kwargs):
  with open(filename, "w", encoding="utf-8", newline="\n") as f:
    json.dump(obj, f, ensure_ascii=False, indent="", **kwargs)

def parseJson(filename):
  with open(filename, "r", encoding="utf-8") as f:
    return json.load(f)

def forAllCwd(root, pattern, callback):
  root = os.path.abspath(root)
  files = next(os.walk(root))[2]

  for f in files:
    if pattern.search(f):
      callback(os.path.join(root, f))

def processAtlasJson(f):
  print("atlas:", f)
  obj = parseJson(f)
  obj.pop("m_GameObject", None)
  obj.pop("m_Enabled", None)
  obj.pop("m_Script", None)
  obj.pop("atlasTextures", None)
  dumpJson(f, obj)

class Book:
  def __init__(self, book_type, list_name):
    self.book_type = book_type
    self.list_name = list_name
  
  def __call__(self, f):
    print(self.book_type, f)
    obj = parseJson(f)

    if self.list_name not in obj:
      return

    result = {}
    for scenario in obj[self.list_name]:
      S = []
      for row in scenario["rows"]:
        if row["isEmpty"] == 0:
          S.append(row["strings"])
      header = S[0]
      x = []
      HL = len(header)
      for s in S[1:]:
        o = {}
        for i in range(min(len(s), HL)):
          a = s[i]
          if a != "":
            o[header[i]] = a
        x.append(o)

      result[scenario["name"]] = x

    dumpJson(f, result)

def processMinify(f):
  print("minify:", f)
  im = Image.open(f)
  bg = Image.new("RGBA", im.size, (250, 250, 250, 255))
  bg.paste(im, (0, 0), im)
  bg.convert("RGB").save(f.replace(".png", ".jpg"), optimize=True)

if __name__ == '__main__':
  forAllCwd("MonoBehaviour", re.compile(r"fg_(\w+)\.json"), processAtlasJson)
  forAllCwd("MonoBehaviour", re.compile(r"\w+\.book\.json"), Book("book:", "importGridList"))
  forAllCwd("MonoBehaviour", re.compile(r"\w+\.chapter\.json"), Book("chapter:", "settingList"))

  forAllCwd("Sprite", re.compile(r"^banner_\w+\.png"), processMinify)
