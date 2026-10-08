AIFLOWED renderer
=================

Makes the carousel slides, the Reel and the Reel cover from a JSON spec, straight into your repo folders.

One-time setup (macOS)
  pip3 install pillow
  brew install ffmpeg
  Install the Poppins font (Google Fonts: Poppins Bold, Medium, Regular). Double-click the .ttf files and choose Install Font.

Daily use
  Claude writes a spec file into this folder, for example:
    aiflowed/tools/specs/2026-10-08.json

  Then run, from the repo root (dieter_ig_ai_pages):

    python3 aiflowed/tools/render.py aiflowed/tools/specs/2026-10-08.json /tmp/aiflowed_out

  Output:
    /tmp/aiflowed_out/posts/slide_01.jpg ...
    /tmp/aiflowed_out/reels/reel.mp4 and cover.jpg

  To render directly into the final folders, run each part with its own target:

    python3 aiflowed/tools/render.py SPEC.json aiflowed/_tmp
    mv aiflowed/_tmp/posts/* aiflowed/posts/2026-10-08_<slug>/
    mv aiflowed/_tmp/reels/* aiflowed/reels/2026-10-08_<slug>/
    rmdir aiflowed/_tmp/posts aiflowed/_tmp/reels aiflowed/_tmp

  (Claude creates the empty dated folders and the caption.txt files for you.)
  Then git add, commit and push, and tell Claude "gepusht".

Test it once
  python3 aiflowed/tools/render.py aiflowed/tools/example_spec.json /tmp/aiflowed_test
  Check that /tmp/aiflowed_test contains 8 slides and a reel.mp4 of about 32 seconds.

Notes
  - The script prints WARNING lines if text may not fit. Shorten the text in the spec and run again.
  - The Reel is silent (on-screen text only).
  - Spec format: see example_spec.json. Slide types: hook, mistake, step, list, cta. Reel scenes: hook, mistake, prompt, checklist, cta.
