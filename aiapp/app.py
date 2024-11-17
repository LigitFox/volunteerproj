from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, send_file, Response
from flask_mail import Mail, Message
from datetime import datetime
import csv
import io
import queue
from flask_wtf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
import os
import csv
from datetime import datetime

expected_headers = [
    'id', 'full_name', 'contact_phone', 'contact_email', 'address', 
    'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship', 
    'date_of_birth', 'preferred_teams', 'skills', 'additional_comments'
]
UPLOAD_FOLDER = 'data/'
app = Flask(__name__)
app.secret_key = 'Pranav'  
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///volunteers.db'
db = SQLAlchemy(app)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'pranavprasv@gmail.com'
app.config['MAIL_PASSWORD'] = 'oegj tkbm paej vwaz'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
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
            
            result = q.get()
            yield f'data: {result}\n\n'
    except GeneratorExit:
        clients.remove(q)
    except Exception:
        clients.remove(q)
import csv


expected_headers = [
    'volunteer id', 'full name', 'contact phone', 'contact email', 'address', 
    'emergency contact name', 'emergency contact phone', 'emergency contact relationship', 'preferred teams', 'assigned teams'
]

def check_csv_format_and_extract_data(file_path):
    volunteers_data = []

    
    header_map = {
        'full_name': 'full name',
        'contact_phone': 'contact phone',
        'contact_email': 'contact email',
        'address': 'address',
        'emergency_contact_name': 'emergency contact name',
        'emergency_contact_phone': 'emergency contact phone',
        'emergency_contact_relationship': 'emergency contact relationship',
        'date_of_birth': 'date of birth',
        'preferred_teams': 'preferred teams',
    }

    with open(file_path, mode='r') as file:
        reader = csv.DictReader(file)

        global csv_headers, missing_headers
        csv_headers = {header.strip().lower(): header for header in reader.fieldnames}
        missing_headers = [field for field, csv_field in header_map.items() if csv_field not in csv_headers]
        
        if missing_headers:
            print("CSV format is incorrect. Missing headers:", missing_headers)
            return None
        
        
        for row in reader:
            try:
                date_of_birth = datetime.strptime(row[csv_headers[header_map['date_of_birth']]], '%m/%d/%Y').strftime('%Y-%m-%d')
            except ValueError:
                print("Date of birth format is incorrect.")
                continue  

            volunteer_data = {
                'full_name': row[csv_headers[header_map['full_name']]],
                'contact_phone': row[csv_headers[header_map['contact_phone']]],
                'contact_email': row[csv_headers[header_map['contact_email']]],
                'address': row[csv_headers[header_map['address']]],
                'emergency_contact_name': row[csv_headers[header_map['emergency_contact_name']]],
                'emergency_contact_phone': row[csv_headers[header_map['emergency_contact_phone']]],
                'emergency_contact_relationship': row[csv_headers[header_map['emergency_contact_relationship']]],
                'date_of_birth': date_of_birth,
                'preferred_teams': row[csv_headers[header_map['preferred_teams']]].split(', '),
            }
            volunteers_data.append(volunteer_data)
            

    print("CSV format is correct. Volunteer data extracted successfully.")
    return volunteers_data



@app.route('/')
def index():
    return render_template('index.html', volunteers=volunteers, events=events)


@app.route('/upload_volunteer_data', methods=['POST'])
def upload_volunteer_data():
    if 'volunteer_file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    
    file = request.files['volunteer_file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
    
    if file and file.filename.endswith('.csv'):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        
        
        volunteers_data = check_csv_format_and_extract_data(file_path)
        
        if not volunteers_data:
            return jsonify({
                "status": "error",
                "message": ("CSV format is incorrect. Missing headers:", missing_headers)
            }), 400

        added_count = 0  

        for volunteer_data in volunteers_data:
            
            if not any(v['full_name'] == volunteer_data['full_name'] and v['contact_email'] == volunteer_data['contact_email'] for v in volunteers):
                
                volunteer = {
                    'id': len(volunteers) + 1,
                    'full_name': volunteer_data['full_name'],
                    'contact_phone': volunteer_data['contact_phone'],
                    'contact_email': volunteer_data['contact_email'],
                    'address': volunteer_data['address'],
                    'emergency_contact_name': volunteer_data['emergency_contact_name'],
                    'emergency_contact_phone': volunteer_data['emergency_contact_phone'],
                    'emergency_contact_relationship': volunteer_data['emergency_contact_relationship'],
                    'date_of_birth': volunteer_data['date_of_birth'],
                    'preferred_teams': volunteer_data['preferred_teams'],
                    'assigned_teams': [],
                    'hours': [],
                    'attendance': {}
                }
                volunteers.append(volunteer)
                added_count += 1
            else:
                print(f"Volunteer {volunteer_data['full_name']} with email {volunteer_data['contact_email']} already exists.")

        
        message = f"{added_count} volunteers added successfully to the database." if added_count > 0 else "No new volunteers were added."

        
        return jsonify({
            "status": "success",
            "message": message
        }), 200

    else:
        return jsonify({"status": "error", "message": "Please upload a CSV file"}), 400



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

    events.append(new_event)  
    flash('event details have been emailed to all volunteers!')
    for q in clients:
        q.put('new_event')



    
    for volunteer in volunteers:
        send_event_email(volunteer['contact_email'], event_date, event_description, event_time)
    flash('event details have been emailed to all volunteers!')
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
        
        
        for volunteer in volunteers:
            send_cancellation_email(volunteer['contact_email'], event['description'], event['date'], event['time'])
        
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Event not found'}), 404



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        
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

        
        raw_skills = request.form.getlist('skills[]')
        processed_skills = [skill.strip() for skill in raw_skills if skill.strip()]

        
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
            
            message = 'The following information already exists in the database: ' + ', '.join(set(existing_fields))
            flash(message, 'warning')
            
            
            form_data = request.form.to_dict(flat=False)
            return render_template('register.html', teams=teams, form_data=form_data, duplicate_fields=duplicate_fields)
        
        
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


@app.route('/update_volunteer_detail', methods=['POST'])
def update_volunteer_detail():
    data = request.get_json()
    
    
    volunteer_id = data.get('volunteer_id')
    field = data.get('field')
    value = data.get('value')
    
    
    if not volunteer_id or not field or value is None:
        return jsonify({'status': 'error', 'message': 'Missing required parameters.'}), 400
    
    
    allowed_fields = {
        'contact_phone',
        'contact_email',
        'emergency_contact_name',
        'emergency_contact_phone',
        'address',
        'date_of_birth',
        'preferred_teams',
        'skills',
        'additional_comments'
    }
    
    if field not in allowed_fields:
        return jsonify({'status': 'error', 'message': f'Field "{field}" is not allowed to be updated.'}), 400
    
    
    try:
        volunteer_id_int = int(volunteer_id)
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Invalid volunteer ID.'}), 400
    
    volunteer = next((v for v in volunteers if v['id'] == volunteer_id_int), None)
    
    if not volunteer:
        return jsonify({'status': 'error', 'message': 'Volunteer not found.'}), 404
    
    
    try:
        if field in {'preferred_teams', 'skills'}:
            
            updated_list = [item.strip() for item in value.split(',') if item.strip()]
            volunteer[field] = updated_list
        elif field == 'date_of_birth':
            
            try:
                
                datetime.strptime(value, '%Y-%m-%d')
                volunteer[field] = value
            except ValueError:
                return jsonify({'status': 'error', 'message': 'Invalid date format. Expected YYYY-MM-DD.'}), 400
        else:
            
            volunteer[field] = value.strip()
        
        return jsonify({'status': 'success', 'message': f'{field.replace("_", " ").capitalize()} updated successfully.'})
    
    except Exception as e:
        
        return jsonify({'status': 'error', 'message': f'An error occurred: {str(e)}'}), 500


@app.route('/attendance', methods=['GET', 'POST'])
def track_attendance():
    if request.method == 'POST':
        session_date = request.form['date']
        selected_volunteer_ids = request.form.getlist('volunteer_ids')  
        absent_volunteer_ids = request.form.getlist('absent_volunteer_ids')  

        if not selected_volunteer_ids and not absent_volunteer_ids:
            flash('No volunteers selected for attendance.', 'warning')
            return redirect(url_for('track_attendance'))

        for volunteer in volunteers:
            volunteer_id_str = str(volunteer['id'])
            if volunteer_id_str in selected_volunteer_ids:
                
                if session_date in volunteer['attendance']:
                    flash(f"Attendance for {volunteer['full_name']} on {session_date} has already been recorded.", 'danger')
                else:
                    volunteer['attendance'][session_date] = 'present'
            elif volunteer_id_str in absent_volunteer_ids:
                
                if session_date in volunteer['attendance']:
                    flash(f"Attendance for {volunteer['full_name']} on {session_date} has already been recorded.", 'danger')
                else:
                    volunteer['attendance'][session_date] = 'absent'
            else:
                
                pass

        flash('Attendance recorded successfully!', 'success')
        return redirect(url_for('index'))

    
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
        'Emergency Contact Name', 'Emergency Contact Phone', 'Emergency Contact Relationship', 'Preferred Teams', 'Assigned Teams', 
        'Total Hours', 'Attendance Dates'
    ])

    
    for v in volunteers:
        total_hours = sum(float(entry['hours']) for entry in v['hours'])
        attendance_dates = "; ".join([f"{date} ({status})" for date, status in v['attendance'].items()])
        preferred_teams = ", ".join(v['preferred_teams'])  
        assigned_teams = ", ".join(v['assigned_teams'])    

        
        writer.writerow([
            v['id'], v['full_name'], v['contact_phone'], v['contact_email'], v['address'],
            v['emergency_contact_name'], v['emergency_contact_phone'], v['emergency_contact_relationship'],
             preferred_teams, assigned_teams,
            total_hours, attendance_dates
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
