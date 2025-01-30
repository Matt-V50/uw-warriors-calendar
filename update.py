import json
from pathlib import Path
import pytz
import requests
from lxml import html
from urllib.parse import quote
from dateutil import parser
from pandas import DataFrame as Df
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import uuid
from icalendar import Calendar, Event as ICalEvent
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import os

TIMEZONE = 'US/Eastern'

class Event:
    def __init__(self, title: str, start_date: datetime, end_date: Optional[datetime] = None, 
                 description: Optional[str] = None, location: Optional[str] = None):
        self.id = str(uuid.uuid4())
        self.title = title
        self.start_date = start_date
        self.end_date = end_date or start_date
        self.description = description
        self.location = location

    def to_ical(self) -> ICalEvent:
        event = ICalEvent()
        event.add('summary', self.title)
        event.add('dtstart', self.start_date)
        event.add('dtend', self.end_date)
        event.add('uid', self.id)
        
        if self.description:
            event.add('description', self.description)
        if self.location:
            event.add('location', self.location)
            
        return event

class PublicCalendar:
    def __init__(self, calendar_name: str, description: str = ""):
        self.calendar_name = calendar_name
        self.description = description
        self.events: List[Event] = []
        self.calendar_id = str(uuid.uuid4())
        
    def add_event(self, event: Event):
        """Add a new event to the calendar."""
        self.events.append(event)
        
    def remove_event(self, event_id: str):
        """Remove an event from the calendar."""
        self.events = [e for e in self.events if e.id != event_id]
        
    def get_ical(self) -> str:
        """Generate iCalendar format string."""
        cal = Calendar()
        cal.add('tzid', TIMEZONE)
        # Set calendar properties
        cal.add('prodid', f'-//{self.calendar_name}//EN')
        cal.add('version', '2.0')
        cal.add('name', self.calendar_name)
        cal.add('description', self.description)
        cal.add('x-wr-calname', self.calendar_name)
        
        # Add events
        for event in self.events:
            cal.add_component(event.to_ical())
            
        return cal.to_ical().decode('utf-8')

def load_location():
    facility_file = Path("data/facility.json")
    if facility_file.exists() and (datetime.now() - datetime.fromtimestamp(facility_file.stat().st_mtime)).days < 1:
        with facility_file.open("r") as f:
            print(f"load from facility location map cache")
            return json.load(f)
    print("update facility location map")
    
    url = "https://warrior.uwaterloo.ca/Facility/GetSchedule"
    payload = {}
    headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Cookie': 'ASP.NET_SessionId=23p2jcwuadgf1qzmmejgfxvu; __RequestVerificationToken=WRg5Vebf5z69FfTmkWuUZgghIgZB2rzU2Joq8LrL0V6sm0G4w1Ou7sobCiBNJSpQ6yh6GHYQzr8vguSsA3Xj_sIkDadXIkLGcBQGunI7Afc1'
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    

    tree = html.fromstring(response.text)
    options = tree.xpath('//*[@id="SelectedFacility"]/option')
    data = []
    for option in options:
        value = option.attrib["value"]
        text = option.text
        data.append(dict(value=value, text=text))
    with facility_file.open("w") as f:
        json.dump(data, f)
    return data

def search(selectedId, start:str, end:str):
    """
    PAC: "4c8a432d-409a-46eb-a1f5-a92bf3b609a2"
    """
    search_file = Path(f"data/{selectedId}.json")
    # update every hour
    if search_file.exists() and (datetime.now() - datetime.fromtimestamp(search_file.stat().st_mtime)).seconds < 3600:
        with search_file.open("r") as f:
            print(f"load from facility Id {selectedId} cache")
            return json.load(f)
    print(f"update facility Id {selectedId}")
    start = quote(start)
    end = quote(end)
    base_url = "https://warrior.uwaterloo.ca/Facility/GetScheduleCustomAppointments?selectedId={selectedId}&start={start}&end={end}"
    url = base_url.format(selectedId=selectedId, start=start, end=end)

    payload = {}
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'priority': 'u=1, i',
        'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Cookie': 'ASP.NET_SessionId=3x5dkosajrpdryl11payil0m'
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    data = response.json()
    location_map = dict((item["value"], item["text"]) for item in load_location())
    
    event_sets = []
    for item in data:
        title = item["title"]
        start = item["start"]
        end = item["end"]
        location = location_map.get(selectedId, "NA")
        event_sets.append(dict(title=title, start=start, end=end, location=location, selectedId=selectedId))    
    
    with search_file.open("w") as f:
        json.dump(event_sets, f)
    
    return event_sets

def update_calendar(name, facilities, filter=None):
    
    # start = "2025-01-19T00:00:00-05:00"
    
    et = pytz.timezone(TIMEZONE)
    start = et.localize(datetime.today()).isoformat()
    end = et.localize(datetime.today() + timedelta(days=14)).isoformat()
    data = []
    for facility in facilities:
        data.extend(search(facility, start, end))
        
    description = f"""Badminton events from UWaterloo Warrior
    From github repo https://github.com/FavorMylikes/uw-warriors-calendar/
"""
    cal = PublicCalendar("UWaterloo Badminton Calendar", description)
    for item in data:
        if filter and not filter(item):
            continue
        event = Event(
            title=item["title"],
            start_date=et.localize(parser.parse(item["start"])),
            end_date=et.localize(parser.parse(item["end"])),
            description=f"{item['title']}\nLast Update: {et.localize(datetime.now()).isoformat()}",
            location=item["location"].split(">")[-1].strip()
        )
        
        cal.add_event(event)
    calendar_file = Path(f"calendar/{name}.ics")
    with calendar_file.open("w") as f:
        f.write(cal.get_ical())

def badminton_calendar():
    facilities = ["4c8a432d-409a-46eb-a1f5-a92bf3b609a2",
                  "a26cd06f-2f4e-4ec7-b946-0985984ba255"]
    filter = lambda x: "badminton" in x["title"].lower()
    update_calendar("badminton", facilities, filter)

if __name__ == "__main__":
    badminton_calendar()