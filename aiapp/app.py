from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, send_file, Response
from flask_mail import Mail, Message
from datetime import datetime
import csv
import io
import queue
from flask_wtf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.secret_key = 'Pranav'  
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///volunteers.db'
db = SQLAlchemy(app)
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
def send_cancellation_email(email, event_description, event_date, event_time):
    msg = Message(
        "Event Cancellation Notice",
        sender="your-email@example.com",
        recipients=[email]
    )
    msg.body = f"The event '{event_description}' scheduled on {event_date} at {event_time} has been canceled."
    mail.send(msg)

@app.route('/delete_event/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    global events
    event = next((e for e in events if e['id'] == event_id), None)
    if event:
        events = [e for e in events if e['id'] != event_id]
        
        # Notify volunteers of the cancellation
        for volunteer in volunteers:
            send_cancellation_email(volunteer['contact_email'], event['description'], event['date'], event['time'])
        
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Event not found'}), 404



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        full_name = request.form['full_name']
        contact_phone = request.form['contact_phone']
        contact_email = request.form['contact_email']
        address = request.form['address']
        emergency_contact_name = request.form['emergency_contact_name']
        emergency_contact_phone = request.form['emergency_contact_phone']
        emergency_contact_relationship = request.form['emergency_contact_relationship']
        date_of_birth = request.form['date_of_birth']
        preferred_teams = request.form.getlist('preferred_teams')
        additional_comments = request.form['additional_comments']

        # Get and process the skills
        raw_skills = request.form.getlist('skills[]')
        processed_skills = [skill.strip() for skill in raw_skills if skill.strip()]

        # Check for existing information
        existing_fields = []

        for v in volunteers:
            if full_name == v.get('full_name'):
                existing_fields.append('Full Name')
            if contact_phone and contact_phone == v.get('contact_phone'):
                existing_fields.append('Contact Phone')
            if contact_email and contact_email == v.get('contact_email'):
                existing_fields.append('Contact Email')
            if address and address == v.get('address'):
                existing_fields.append('Address')
            if emergency_contact_name and emergency_contact_name == v.get('emergency_contact_name'):
                existing_fields.append('Emergency Contact Name')
            if emergency_contact_phone and emergency_contact_phone == v.get('emergency_contact_phone'):
                existing_fields.append('Emergency Contact Phone')

        if existing_fields:
            # Map field labels to input names
            field_name_mapping = {
                'Full Name': 'full_name',
                'Contact Phone': 'contact_phone',
                'Contact Email': 'contact_email',
                'Address': 'address',
                'Emergency Contact Name': 'emergency_contact_name',
                'Emergency Contact Phone': 'emergency_contact_phone',
                'Emergency Contact Relationship': 'emergency_contact_relationship',
                'Date of Birth': 'date_of_birth'
            }
            duplicate_fields = [field_name_mapping[field] for field in set(existing_fields)]
            # Generate a warning message
            message = 'The following information already exists in the database: ' + ', '.join(set(existing_fields))
            flash(message, 'warning')
            # Re-render the registration form with the existing data
            # Convert request.form to a dictionary that preserves list values
            form_data = request.form.to_dict(flat=False)
            return render_template('register.html', teams=teams, form_data=form_data, duplicate_fields=duplicate_fields)
        
        # Create the volunteer entry
        volunteer = {
            'id': len(volunteers) + 1,
            'full_name': full_name,
            'contact_phone': contact_phone,
            'contact_email': contact_email,
            'address': address,
            'emergency_contact_name': emergency_contact_name,
            'emergency_contact_phone': emergency_contact_phone,
            'emergency_contact_relationship': emergency_contact_relationship,
            'date_of_birth': date_of_birth,
            'preferred_teams': preferred_teams,
            'skills': processed_skills,
            'additional_comments': additional_comments,
            'assigned_teams': [],
            'hours': [],
            'attendance': {}
        }
        volunteers.append(volunteer)
        flash('Volunteer registered successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('register.html', teams=teams, form_data={}, duplicate_fields=[])





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
        selected_volunteer_ids = request.form.getlist('volunteer_ids')  # Present volunteers
        absent_volunteer_ids = request.form.getlist('absent_volunteer_ids')  # Absent volunteers

        if not selected_volunteer_ids and not absent_volunteer_ids:
            flash('No volunteers selected for attendance.', 'warning')
            return redirect(url_for('track_attendance'))

        for volunteer in volunteers:
            volunteer_id_str = str(volunteer['id'])
            if volunteer_id_str in selected_volunteer_ids:
                # Mark as present
                if session_date in volunteer['attendance']:
                    flash(f"Attendance for {volunteer['full_name']} on {session_date} has already been recorded.", 'danger')
                else:
                    volunteer['attendance'][session_date] = 'present'
            elif volunteer_id_str in absent_volunteer_ids:
                # Mark as absent
                if session_date in volunteer['attendance']:
                    flash(f"Attendance for {volunteer['full_name']} on {session_date} has already been recorded.", 'danger')
                else:
                    volunteer['attendance'][session_date] = 'absent'
            else:
                # Neither present nor absent selected for this volunteer
                pass

        flash('Attendance recorded successfully!', 'success')
        return redirect(url_for('index'))

    # Initialize attendance dictionary if not present
    for volunteer in volunteers:
        if 'attendance' not in volunteer:
            volunteer['attendance'] = {}

    return render_template('attendance.html', volunteers=volunteers)



@app.route('/update_attendance_status/<int:volunteer_id>', methods=['POST'])
def update_attendance_status(volunteer_id):
    volunteer = next((v for v in volunteers if v['id'] == volunteer_id), None)
    if volunteer:
        data = request.get_json()
        date = data.get('date')
        new_status = data.get('status')
        if date in volunteer['attendance']:
            volunteer['attendance'][date] = new_status
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': 'Attendance record not found'}), 404
    else:
        return jsonify({'status': 'error', 'message': 'Volunteer not found'}), 404


@app.route('/remove_attendance/<int:volunteer_id>/<string:date>', methods=['POST'])
def remove_attendance(volunteer_id, date):
    volunteer = next((v for v in volunteers if v['id'] == volunteer_id), None)
    if volunteer and date in volunteer['attendance']:
        del volunteer['attendance'][date]
        flash('Attendance record removed successfully!', 'success')
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
        attendance_dates = "; ".join([f"{date} ({status})" for date, status in v['attendance'].items()])
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
