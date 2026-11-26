from flask import Flask, render_template, send_file, abort
from pathlib import Path
import os

app = Flask(__name__, template_folder='templates', static_folder='static')
sport_map = {
    "badminton": "badminton-shuttle",
    "pickleball": "tennis-ball"
}
calendar_ids = {
    "badminton": "NDI2ODljYmIyZDEwZTY4N2RjNTA1NmM2NTFlMzk3ZWI0YTdiYWNiYzBkMGNiOWRhNmY4ZmY1ZWJiYTZjOWY1Y0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t",
    "pickleball": "MjU3MzczNjVmYjdmYjM3ZDgyZDgwYzBiYmE2OGM0ZDk5YmJhZDVlNWU3NDdlMTVlOTg2M2ZiNmU3OTc4NDk5MEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t"
}

@app.route('/')
def index():
    links = []
    for calendar in Path("calendar").iterdir():
        if calendar.is_file() and calendar.suffix == ".ics":
            links.append({ "text": calendar.stem, 
                          "url": f"/{calendar.stem}", 
                          "sport": sport_map.get(calendar.stem, "workout-run") })
    links.sort(key=lambda link: {"badminton": 0, "pickleball": 1}.get(link["text"].lower(), 2))
    return render_template(
        'index.html',
        links=links,
        calendar_ids=calendar_ids,
        initial_sport="badminton"
    )

@app.route('/<path:subpath>')
def browse(subpath=''):
    calendar_path = Path("calendar")
    requested_path = calendar_path / f"{subpath}.ics"
    
    # Security check
    try:
        requested_path.relative_to(calendar_path)
    except ValueError:
        abort(403)  # Forbidden
        
    if not requested_path.exists():
        abort(404)
        
    if requested_path.is_file():
        return send_file(requested_path)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)