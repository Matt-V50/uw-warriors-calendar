import requests
from urllib.parse import quote
from dateutil import parser

from datetime import datetime, date
from typing import List, Dict, Optional
import uuid
from icalendar import Calendar, Event as ICalEvent
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import os

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

start = "2025-01-19T00:00:00-05:00"
end = "2025-01-26T00:00:00-05:00"

location_map = {
    "4c8a432d-409a-46eb-a1f5-a92bf3b609a2": "PAC Small Gym"
}

def update_calendar(selectedId, start, end):
    """
    PAC: "4c8a432d-409a-46eb-a1f5-a92bf3b609a2"
    """
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
    cal = PublicCalendar("Team Calendar", "Our team's public calendar")
    
    for item in data:
        if "badminton" not in item["title"].lower():
            continue
        # convert it to ics format
        start = item["start"]
        end = item["end"]
        # start = start.replace("T", " ")
        # end = end.replace("T", " ")
        title = item["title"]
                # Add some example events
        event = Event(
            title=title,
            start_date=parser.parse(start),
            end_date=parser.parse(end),
            description=item["title"],
            location=location_map.get(selectedId, "NA")
        )
                
        

        cal.add_event(event)
    with open(f"{selectedId}.ics", "w") as f:
        f.write(cal.get_ical())
    
if __name__ == "__main__":
    update_calendar("4c8a432d-409a-46eb-a1f5-a92bf3b609a2", start, end)