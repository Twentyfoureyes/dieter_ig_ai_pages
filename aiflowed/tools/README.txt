AIFLOWED renderer
=================

Makes the carousel slides, the Reel and the Reel cover from a JSON spec, straight into the dated repo folders.

One-time setup (macOS)
  python3 -m venv ~/aiflowed_venv
  ~/aiflowed_venv/bin/pip install pillow
  brew install ffmpeg
  Poppins font in ~/Library/Fonts: Poppins-Bold.ttf, Poppins-Medium.ttf, Poppins-Regular.ttf

Daily use
  1. Claude writes the spec to aiflowed/tools/specs/<date>.json and the caption.txt files to the dated folders.
     The spec names its own output folders ("output" key), so nothing has to be moved afterwards.
  2. Run, from the repo root (dieter_ig_ai_pages):

       ~/aiflowed_venv/bin/python aiflowed/tools/render.py aiflowed/tools/specs/<date>.json

  3. git add, commit and push, then tell Claude "gepusht".

Options
  --only carousel | --only reel     render just one part
  Output folders: the spec's "output" key (paths relative to the repo root, resolved from the script's own location, so it works from any folder).
  Without an "output" key the files go to aiflowed/posts/<spec name> and aiflowed/reels/<spec name> in the repo.
  python render.py SPEC.json OUT_DIR   ignores all of that and writes OUT_DIR/posts and OUT_DIR/reels
  The example spec writes to aiflowed/tools/example_out/ (safe to delete, do not commit).

Notes
  - The script prints WARNING lines if text may not fit. Send them to Claude; the spec gets shortened and you run it again.
  - The Reel is silent (on-screen text only).
  - Slide types: hook, mistake, step, list, cta. Reel scenes: hook, mistake, prompt, checklist, cta. See example_spec.json.
