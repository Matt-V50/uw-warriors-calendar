from pathlib import Path
from flask_frozen import Freezer
from app import app

freezer = Freezer(app)

@freezer.register_generator
def browse():
    paths = []
    for calendar in Path("calendar").iterdir():
        if calendar.is_file() and calendar.suffix == ".ics":
            paths.append(calendar.stem)
    for path in paths:
        yield {'subpath': path}

if __name__ == '__main__':
    freezer.freeze()
