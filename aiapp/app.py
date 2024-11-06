from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, send_file, Response
from flask_mail import Mail, Message
from datetime import datetime
import csv
import io
import queue
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  


app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'pranavprasv@gmail.com'
app.config['MAIL_PASSWORD'] = 'oegj tkbm paej vwaz'

mail = Mail(app)
clients = []

volunteers = []
events = []

teams = ['Attendance', 'Teachers']
def event_stream():
    q = queue.Queue()
    clients.append(q)
    try:
        while True:
            # Wait for an item in the queue
            result = q.get()
            yield f'data: {result}\n\n'
    except GeneratorExit:
        clients.remove(q)
    except Exception:
        clients.remove(q)

@app.route('/')
def index():
    return render_template('index.html', volunteers=volunteers, events=events)


@app.route('/calendar')
def calendar():
    return render_template('calendar_component.html')
@app.route('/stream')
def stream():
    def event_stream():
        q = queue.Queue()
        clients.append(q)
        try:
            while True:
                # Wait for an item in the queue
                result = q.get()
                yield f'data: {result}\n\n'
        except GeneratorExit:
            clients.remove(q)
    response = Response(event_stream(), mimetype="text/event-stream")
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

@app.route('/create_event', methods=['POST'])
def create_event():
    event_data = request.json
    event_date = event_data.get('date')
    event_description = event_data.get('description')
    event_time = event_data.get('time')
    event_color = event_data.get('color', 'red')

    new_event = {
        "id": len(events) + 1,
        "date": event_date,
        "description": event_description,
        "time": event_time,
        "color": event_color
    }

    events.append(new_event)  # Save event in the events list
    for q in clients:
        q.put('new_event')



    # Notify volunteers
    for volunteer in volunteers:
        send_event_email(volunteer['contact_email'], event_date, event_description, event_time)
    return redirect(url_for('index'))

@app.route('/get_events', methods=['GET'])
def get_events():
    return jsonify(events), 200


def send_event_email(email, date, description, time):
    msg = Message(
        "New Event Created",
        sender="your-email@example.com",
        recipients=[email]
    )
    msg.body = f"A new event has been scheduled on {date} at {time}.\n\nEvent: {description}"
    mail.send(msg)
@app.route('/delete_event/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    global events
    event = next((e for e in events if e['id'] == event_id), None)
    if event:
        events = [e for e in events if e['id'] != event_id]
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Event not found'}), 404


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        
        skills = request.form.getlist('skills[]')

        
        volunteer = {
            'id': len(volunteers) + 1,
            'full_name': request.form['full_name'],
            'contact_phone': request.form['contact_phone'],
            'contact_email': request.form['contact_email'],
            'address': request.form['address'],
            'emergency_contact_name': request.form['emergency_contact_name'],
            'emergency_contact_phone': request.form['emergency_contact_phone'],
            'emergency_contact_relationship': request.form['emergency_contact_relationship'],
            'date_of_birth': request.form['date_of_birth'],
            'preferred_teams': request.form.getlist('preferred_teams'),
            'skills': skills,
            'additional_comments': request.form['additional_comments'],
            'assigned_teams': [],
            'hours': [],
            'attendance': []
        }
        volunteers.append(volunteer)
        return redirect(url_for('index'))
    return render_template('register.html', teams=teams)




@app.route('/add_team', methods=['POST'])
def add_team():
    new_team = request.json.get('team_name')
    if new_team and new_team not in teams:
        teams.append(new_team)
        return jsonify({'status': 'success', 'team': new_team})
    else:
        return jsonify({'status': 'error', 'message': 'Team already exists or invalid name'}), 400

@app.route('/remove_team', methods=['POST'])
def remove_team():
    team_name = request.json.get('team_name')
    if team_name in teams:
        teams.remove(team_name)
        
        for volunteer in volunteers:
            if team_name in volunteer['preferred_teams']:
                volunteer['preferred_teams'].remove(team_name)
            if team_name in volunteer['assigned_teams']:
                volunteer['assigned_teams'].remove(team_name)
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Team not found'}), 400

@app.route('/volunteer/<int:volunteer_id>', methods=['GET', 'POST'])
def volunteer_detail(volunteer_id):
    volunteer = next((v for v in volunteers if v['id'] == volunteer_id), None)
    if volunteer is None:
        return redirect(url_for('index'))
    if request.method == 'POST':
        
        assigned_teams = request.form.getlist('assigned_teams')
        volunteer['assigned_teams'] = assigned_teams
        
        new_team = request.form.get('new_team')
        if new_team and new_team not in teams:
            teams.append(new_team)
            volunteer['assigned_teams'].append(new_team)
        flash('Volunteer details updated successfully!', 'success')
        return redirect(url_for('volunteer_detail', volunteer_id=volunteer_id))
    return render_template('volunteer.html', volunteer=volunteer, teams=teams)

@app.route('/hours/<int:volunteer_id>', methods=['GET', 'POST'])
def track_hours(volunteer_id):
    volunteer = next((v for v in volunteers if v['id'] == volunteer_id), None)
    if volunteer is None:
        return redirect(url_for('index'))
    if request.method == 'POST':
        hours_date = request.form['date']
        
        
        if any(entry['date'] == hours_date for entry in volunteer['hours']):
            flash('Hours have already been recorded for this date.', 'danger')
            return redirect(url_for('volunteer_detail', volunteer_id=volunteer_id))
        
        hours_entry = {
            'date': hours_date,
            'hours': request.form['hours'],
            'notes': request.form['notes']
        }
        volunteer['hours'].append(hours_entry)
        flash('Hours logged successfully!', 'success')
        return redirect(url_for('volunteer_detail', volunteer_id=volunteer_id))
    return render_template('hours.html', volunteer=volunteer)



@app.route('/update_hours/<int:volunteer_id>/<string:date>', methods=['POST'])
def update_hours(volunteer_id, date):
    volunteer = next((v for v in volunteers if v['id'] == volunteer_id), None)
    if volunteer:
        new_hours = request.form['hours']
        new_notes = request.form['notes']
        
        
        for entry in volunteer['hours']:
            if entry['date'] == date:
                entry['hours'] = new_hours
                entry['notes'] = new_notes
                break
        flash('Logged hours updated successfully!', 'success')
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Volunteer or hours entry not found'}), 404


@app.route('/attendance', methods=['GET', 'POST'])
def track_attendance():
    if request.method == 'POST':
        session_date = request.form['date']
        selected_volunteer_ids = request.form.getlist('volunteer_ids')
        
        if not selected_volunteer_ids:
            flash('No volunteers selected for attendance.', 'warning')
            return redirect(url_for('track_attendance'))
        
        for volunteer in volunteers:
            if str(volunteer['id']) in selected_volunteer_ids:
                
                if session_date in volunteer['attendance']:
                    flash(f"Attendance for {volunteer['full_name']} on {session_date} has already been recorded.", 'danger')
                else:
                    volunteer['attendance'].append(session_date)
        
        return redirect(url_for('index'))
    
    return render_template('attendance.html', volunteers=volunteers)


@app.route('/remove_attendance/<int:volunteer_id>/<string:date>', methods=['POST'])
def remove_attendance(volunteer_id, date):
    volunteer = next((v for v in volunteers if v['id'] == volunteer_id), None)
    if volunteer and date in volunteer['attendance']:
        volunteer['attendance'].remove(date)
        flash('Attendance date removed successfully!', 'success')
    else:
        flash('Attendance date not found.', 'danger')
    return redirect(url_for('volunteer_detail', volunteer_id=volunteer_id))

@app.route('/reports')
def reports():
    output = io.StringIO()
    writer = csv.writer(output)

    
    writer.writerow([
        'Volunteer ID', 'Full Name', 'Contact Phone', 'Contact Email', 'Address',
        'Emergency Contact Name', 'Emergency Contact Phone', 'Emergency Contact Relationship', 'Preferred Teams', 'Assigned Teams', 'Skills', 
        'Total Hours', 'Attendance Dates', 'Additional Comments'
    ])

    
    for v in volunteers:
        total_hours = sum(float(entry['hours']) for entry in v['hours'])
        attendance_dates = ", ".join(v['attendance'])  
        preferred_teams = ", ".join(v['preferred_teams'])  
        assigned_teams = ", ".join(v['assigned_teams'])  
        skills = ", ".join(v['skills'])  

        
        writer.writerow([
            v['id'], v['full_name'], v['contact_phone'], v['contact_email'], v['address'],
            v['emergency_contact_name'], v['emergency_contact_phone'], v['emergency_contact_relationship'],
             preferred_teams, assigned_teams, skills,
            total_hours, attendance_dates, v['additional_comments']
        ])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='volunteer_report.csv'  
    )

@app.route('/remove_hours/<int:volunteer_id>/<string:date>', methods=['POST'])
def remove_hours(volunteer_id, date):
    volunteer = next((v for v in volunteers if v['id'] == volunteer_id), None)
    if volunteer:
        
        volunteer['hours'] = [entry for entry in volunteer['hours'] if entry['date'] != date]
        flash('Logged hours removed successfully!', 'success')
    else:
        flash('Volunteer or logged hours not found.', 'danger')
    return redirect(url_for('volunteer_detail', volunteer_id=volunteer_id))

@app.route('/delete_volunteer/<int:volunteer_id>', methods=['POST'])
def delete_volunteer(volunteer_id):
    global volunteers
    volunteer = next((v for v in volunteers if v['id'] == volunteer_id), None)
    if volunteer:
        volunteers = [v for v in volunteers if v['id'] != volunteer_id]
        flash('Volunteer removed successfully!', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
