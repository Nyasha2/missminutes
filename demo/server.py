from flask import Flask, render_template, request, jsonify
import json

app = Flask(__name__)
SCHEDULE_FILE = 'schedule.json'

def load_schedule():
    try:
        with open(SCHEDULE_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'events': [], 'tasks': []}

def save_schedule(schedule):
    with open(SCHEDULE_FILE, 'w') as f:
        json.dump(schedule, f, indent=2)

@app.route('/')
def calendar():
    return render_template('calendar.html')

@app.route('/plan')
def plan():
    return render_template('plan.html')

@app.route('/api/add_event', methods=['POST'])
def add_event():
    schedule = load_schedule()
    event = request.json
    schedule['events'].append(event)
    save_schedule(schedule)
    return jsonify({'status': 'success'})

@app.route('/api/add_task', methods=['POST'])
def add_task():
    schedule = load_schedule()
    task = request.json
    schedule['tasks'].append(task)
    save_schedule(schedule)
    return jsonify({'status': 'success'})

@app.route('/api/generate_schedule', methods=['POST'])
def generate_schedule():
    schedule = load_schedule()
    # Schedule generation logic here
    return jsonify({'status': 'success'})

@app.route('/api/calendar')
def get_calendar():
    schedule = load_schedule()
    return jsonify(schedule)

if __name__ == '__main__':
    app.run(debug=True)