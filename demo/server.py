import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, send_file, request, jsonify, render_template_string
from flask_cors import CORS
from missminutes.scheduler import Scheduler
from missminutes.tasks import Task, RecurringTask
from missminutes.timeprofile import TimeProfile, DayOfWeek
from missminutes.events import RecurringEvent
from datetime import datetime, timedelta
import json

app = Flask(__name__, static_folder='static')
CORS(app)  # This allows local development

# Store scheduler state
scheduler_state = {
    'scheduler': Scheduler(start_date=datetime.now(), days=7),
    'time_profiles': [],
    'events': [],
    'tasks': []
}

@app.route('/')
def serve_calendar():
    return send_file('calendar.html')

@app.route('/plan')
def serve_builder():
    return send_file('plan.html')

@app.route('/api/calendar')
def get_calendar():
    return send_file('schedule.json', mimetype='application/json')

@app.route('/api/add_time_profile', methods=['POST'])
def add_time_profile():
    data = request.json
    profile = TimeProfile(name=data['name'])
    
    # Process the grid data
    for day in range(7):
        for hour in data['selected_hours'][day]:
            profile.add_window(
                DayOfWeek(day),
                hour, 0,  # Start at the hour
                hour + 1, 0  # End at next hour
            )
    
    scheduler_state['time_profiles'].append(profile)
    scheduler_state['scheduler'].add_time_profile(profile)
    
    return jsonify({'status': 'success'})

@app.route('/api/add_event', methods=['POST'])
def add_event():
    data = request.json
    start_date = scheduler_state['scheduler'].start_date
    
    event = RecurringEvent(
        id=f"{data['title'].lower().replace(' ', '_')}",
        title=data['title'],
        start_time=datetime.combine(start_date.date(), 
            datetime.strptime(data['start_time'], '%H:%M').time()),
        end_time=datetime.combine(start_date.date(), 
            datetime.strptime(data['end_time'], '%H:%M').time()),
        completed=False
    )
    
    weekdays = [DayOfWeek[day.upper()].value for day in data['days']]
    event.set_weekly_recurrence(
        weekdays=weekdays,
        until=start_date + timedelta(days=7),
        interval=1
    )
    
    scheduler_state['events'].append(event)
    scheduler_state['scheduler'].add_event(event)
    
    return render_events()

@app.route('/api/add_task', methods=['POST'])
def add_task():
    data = request.json
    
    task = Task(
        title=data['title'],
        description=data.get('description', ''),
        duration=timedelta(
            hours=int(data['duration_hours']),
            minutes=int(data['duration_minutes'])
        ),
        min_session_length=timedelta(hours=float(data['min_session'])),
        max_session_length=timedelta(hours=float(data['max_session'])),
        due=datetime.now() + timedelta(days=int(data['due_days']))
    )
    
    if data.get('time_profile'):
        profile = next(p for p in scheduler_state['time_profiles'] 
                      if p.name == data['time_profile'])
        task.assign_time_profile(profile)
    
    scheduler_state['tasks'].append(task)
    scheduler_state['scheduler'].add_task(task)
    
    return render_tasks()

@app.route('/api/generate_schedule', methods=['POST'])
def generate_schedule():
    schedule = scheduler_state['scheduler'].schedule()
    schedule_by_day = scheduler_state['scheduler'].print_schedule()
    
    with open('schedule.json', 'w') as f:
        json.dump(schedule_by_day, f, indent=2, default=str)
    
    return jsonify({'status': 'success'})

# Helper functions to render partial HTML
def render_time_profiles():
    profiles = scheduler_state['time_profiles']
    html = """
    <div class="profiles-list">
        {% for profile in profiles %}
        <div class="profile-item">
            <span class="profile-name">{{ profile.name }}</span>
        </div>
        {% endfor %}
    </div>
    """
    return render_template_string(html, profiles=profiles)

def render_events():
    events = scheduler_state['events']
    html = """
    <div class="events-list">
        {% for event in events %}
        <div class="event-item">
            <span class="event-title">{{ event.title }}</span>
        </div>
        {% endfor %}
    </div>
    """
    return render_template_string(html, events=events)

def render_tasks():
    tasks = scheduler_state['tasks']
    html = """
    <div class="tasks-list">
        {% for task in tasks %}
        <div class="task-item">
            <span class="task-title">{{ task.title }}</span>
        </div>
        {% endfor %}
    </div>
    """
    return render_template_string(html, tasks=tasks)

if __name__ == '__main__':
    app.run(debug=True, port=5000) 