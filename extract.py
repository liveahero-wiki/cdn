#! python3

import argparse
import os
import json
import sys
import re
from pathlib import PureWindowsPath

import UnityPy

print("Encoding:", sys.getdefaultencoding())

CLASSES = ["MonoBehaviour", "Sprite", "TextAsset"]

DRIVE_PATTERN = re.compile(r"^[a-zA-Z]:$")

RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", 
    "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", 
    "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}

PROHIBITED_CHARS_PATTERN = re.compile(r'[<>:"|?*]')
CONTROL_CHARS_PATTERN = re.compile(r'[\x00-\x1f\x7f-\x9f]')

def native_sanitize_windows_path(unsafe_path: str) -> str:
    """Sanitizes an unsafe string into a valid Windows file path."""
    path_obj = PureWindowsPath(unsafe_path)
    sanitized_parts = []
    
    # Process each segment of the path individually to preserve the drive configuration
    for i, part in enumerate(path_obj.parts):
        # Do not modify Windows drive letters like 'C:' if it's the first part
        if i == 0 and DRIVE_PATTERN.match(part):
            sanitized_parts.append(part)
            continue
            
        # 1. Remove Windows prohibited characters: < > : " | ? *
        cleaned = PROHIBITED_CHARS_PATTERN.sub('', part)
        
        # 2. Strip unprintable/control characters
        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
        
        # 3. Windows ignores spaces and periods at the end of directory/file names
        cleaned = cleaned.strip(". ")
        
        # 4. Check against Windows reserved device names
        # If the file base name matches a device name, alter it to make it safe
        base_name = cleaned.split('.')[0].upper()
        if base_name in RESERVED_NAMES:
            cleaned = f"safe_{cleaned}"
            
        # Keep the cleaned component if it isn't completely empty
        if cleaned:
            sanitized_parts.append(cleaned)
            
    # Reconstruct the path using Windows path syntax structure
    return str(PureWindowsPath(*sanitized_parts))

def unpack_all_assets(src_folder: str, dest_folder: str, includeTexture2D: bool):
  if includeTexture2D:
    CLASSES.append("Texture2D")
  for c in CLASSES:
    os.makedirs(os.path.join(dest_folder, c), exist_ok=True)

  for root, dirs, files in os.walk(src_folder):
    for filename in files:
      file_path = os.path.join(root, filename)
      env = UnityPy.load(file_path)

      for obj in env.objects:
        if obj.type.name not in CLASSES:
          continue

        try:
          data = obj.read()
        except Exception as e:
          print(f"::warning file={file_path}::{e}")
          continue

        paths = [dest_folder, obj.type.name]

        if hasattr(data, "name"):
          paths.append(getattr(data, "name"))
        elif hasattr(data, "m_Name"):
          paths.append(getattr(data, "m_Name"))

        dest = os.path.join(*paths)
        dest = native_sanitize_windows_path(dest)
        #print(f"::debug::{dest}")

        if obj.type.name in ["Texture2D", "Sprite"]:
          dest, ext = os.path.splitext(dest)
          dest = dest + ".png"
          data.image.save(dest)

        elif obj.type.name == "MonoBehaviour":
          dest, ext = os.path.splitext(dest)
          if ext in [".book", ".chapter"]:
            dest = dest + ext
          dest = dest + ".json"

          if obj.serialized_type.nodes:
            try:
              tree = obj.read_typetree()
              with open(dest, "w", encoding="utf8") as f:
                json.dump(tree, f, ensure_ascii=False, indent=2)
            except Exception as e:
              print(f"::warning file={file_path}::{e}")

        elif obj.type.name == "TextAsset":
          data = obj.read()
          #print("Text:", dest)
          if not dest.endswith(".atlas") and not dest.endswith(".skel"):
            dest, ext = os.path.splitext(dest)
          dest = dest + ".txt"
          with open(dest, "wb") as f:
            f.write(data.m_Script.encode("utf-8", "surrogateescape"))

        #elif obj.type.name == "AudioClip":
        #  for name, raw in data.samples.items():
        #    dest = os.path.join(dest_folder, obj.type.name, name)
        #    with open(dest, "wb") as f:
        #      f.write(raw)

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument("src", help="asset bundles folder")
  parser.add_argument("dest", help="output folder")
  parser.add_argument("--texture2d", action='store_true', default=False, help="Include Texture2D")

  args = parser.parse_args()
  unpack_all_assets(args.src, args.dest, args.texture2d)
