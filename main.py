import psycopg2
import uuid
from flask_bcrypt import Bcrypt
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, g
import os

app = Flask(__name__)
# Use environment variables for configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'my_default_secret_key')
app.config['DATABASE_URL'] = os.environ.get('DATABASE_URL')
bcrypt = Bcrypt(app)


# --- DATABASE CONNECTION ---
def connect_to_db():
    conn = psycopg2.connect(app.config['DATABASE_URL'])
    return conn


# --- USER & SESSION MANAGEMENT ---
@app.route('/')
def index():
    if 'session_id' in session and get_username_from_session(session['session_id']):
        return redirect(url_for('dashboard'))
    return render_template('home.html')


def create_session(username):
    session_id = str(uuid.uuid4())
    expire_date = datetime.now() + timedelta(hours=24)
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO sessiondetails (username, sessionid, expiredate) VALUES (%s, %s, %s)",
                (username, session_id, expire_date))
    conn.commit()
    cur.close()
    conn.close()
    return session_id


def delete_session(session_id):
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM sessiondetails WHERE sessionid = %s", (session_id,))
    conn.commit()
    cur.close()
    conn.close()


def get_username_from_session(session_id):
    if not session_id:
        return None
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("SELECT username FROM sessiondetails WHERE sessionid = %s AND expiredate > NOW()", (session_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else None


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'session_id' in session and get_username_from_session(session['session_id']):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = connect_to_db()
        cur = conn.cursor()
        cur.execute("SELECT password FROM userlogindetails WHERE username = %s", (username,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        if result and bcrypt.check_password_hash(result[0], password):
            session['session_id'] = create_session(username)
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error_message="Invalid username or password.")
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        try:
            conn = connect_to_db()
            cur = conn.cursor()
            cur.execute("INSERT INTO userlogindetails (username, password) VALUES (%s, %s)",
                        (username, hashed_password))
            cur.execute("INSERT INTO day_user (username, day) VALUES (%s, %s)", (username, 1))
            cur.execute("INSERT INTO userpersonaldetails (username) VALUES (%s)", (username,))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('login'))
        except psycopg2.errors.UniqueViolation:
            return render_template('register.html', error="Username already exists")
    return render_template('register.html')


@app.route('/logout')
def logout():
    if 'session_id' in session:
        delete_session(session['session_id'])
        session.pop('session_id', None)
    return redirect(url_for('login'))


# --- APPLICATION CORE ROUTES ---
@app.route('/dashboard')
def dashboard():
    username = get_username_from_session(session.get('session_id'))
    if username:
        return render_template('dashboard.html', username=username)
    return redirect(url_for('login'))


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    username = get_username_from_session(session.get('session_id'))
    if not username:
        return redirect(url_for('login'))

    conn = connect_to_db()
    cur = conn.cursor()

    if request.method == 'POST':
        dob = request.form.get('dob')
        weight = float(request.form.get('weight'))
        height_cm = float(request.form.get('height'))
        height_m = height_cm / 100.0  # Convert cm to meters for BMI calculation

        cur.execute("""
            UPDATE userpersonaldetails SET dob=%s, weight=%s, height=%s WHERE username=%s
        """, (dob, weight, height_m, username))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('profile'))

    # GET request logic
    cur.execute("SELECT weight, height, dob FROM userpersonaldetails WHERE username = %s", (username,))
    user_data = cur.fetchone()
    cur.close()
    conn.close()

    # Unpack data and calculate BMI
    weight, height, dob = user_data if user_data else (None, None, None)
    bmi = None
    if weight and height:
        bmi = round(weight / (height * height), 2)

    # Convert height back to cm for display
    display_height_cm = height * 100 if height else None

    return render_template('profile.html', username=username, weight=weight, height=display_height_cm, bmi=bmi, dob=dob)


@app.route('/practise')
def practise():
    username = get_username_from_session(session.get('session_id'))
    if not username:
        return redirect(url_for('login'))

    day = get_day(username)
    age = calculate_age(username)
    bmi = get_bmi(username)

    if age is None or bmi is None:
        message = "Please complete your profile (Date of Birth, Height, Weight) to generate an exercise plan."
        return render_template('practise.html', username=username, message=message)

    exercise_plan = get_exercise_plan(username, day)
    if not exercise_plan:
        new_plan = generate_exercise_plan(bmi, day, age)
        insert_exercise_plan(username, day, new_plan)
        exercise_plan = get_exercise_plan(username, day)  # Fetch the newly created plan

    return render_template('practise.html', username=username, exercise_plan=exercise_plan)


# --- EXERCISE & PROGRESS API ENDPOINTS ---
@app.route('/update_exercise', methods=['POST'])
def update_exercise():
    username = get_username_from_session(session.get('session_id'))
    if not username:
        return jsonify(success=False), 401

    data = request.json
    exercise_type = data.get('exercise_type')
    completed_reps = data.get('completed_reps')
    day = get_day(username)

    conn = connect_to_db()
    cur = conn.cursor()
    try:
        # Update specific exercise
        update_query = f"UPDATE exercise_plan SET {exercise_type}_completed = %s WHERE username = %s AND day = %s"
        cur.execute(update_query, (completed_reps, username, day))

        # Recalculate and update completion percentage
        cur.execute("""
            UPDATE exercise_plan
            SET completion = (
                (pushups_completed::float / pushups + 
                 squats_completed::float / squats + 
                 situps_completed::float / situps) * 100 / 3
            )
            WHERE username = %s AND day = %s
        """, (username, day))

        conn.commit()
        return jsonify(success=True)
    except Exception as e:
        print("Error updating exercise:", e)
        conn.rollback()
        return jsonify(success=False), 500
    finally:
        cur.close()
        conn.close()


@app.route('/increment_day', methods=['POST'])
def increment_day():
    username = get_username_from_session(session.get('session_id'))
    if not username:
        return jsonify(success=False), 401

    conn = connect_to_db()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE day_user SET day = day + 1 WHERE username = %s", (username,))
        conn.commit()
        return jsonify(success=True)
    except Exception as e:
        print("Error incrementing day:", e)
        conn.rollback()
        return jsonify(success=False), 500
    finally:
        cur.close()
        conn.close()


# --- HELPER FUNCTIONS ---
def get_day(username):
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("SELECT day FROM day_user WHERE username = %s", (username,))
    day = cur.fetchone()
    cur.close()
    conn.close()
    return day[0] if day else 1


def calculate_age(username):
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("SELECT dob FROM userpersonaldetails WHERE username = %s", (username,))
    dob_result = cur.fetchone()
    cur.close()
    conn.close()
    if dob_result and dob_result[0]:
        today = date.today()
        dob = dob_result[0]
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return None


def get_bmi(username):
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("SELECT weight, height FROM userpersonaldetails WHERE username = %s", (username,))
    user_details = cur.fetchone()
    cur.close()
    conn.close()
    if user_details and user_details[0] and user_details[1]:
        weight, height = user_details
        if height > 0:  # Avoid division by zero
            return round(weight / (height * height), 2)
    return None


def generate_exercise_plan(bmi, day, age):
    # This is your existing logic, it seems fine.
    base_reps = {'pushups': 10, 'situps': 15, 'squats': 20}
    bmi_factor = 1.0
    if bmi < 18.5:
        bmi_factor = 0.8
    elif 25 <= bmi < 30:
        bmi_factor = 1.2
    else:
        bmi_factor = 1.4

    age_factor = 1.0
    if 30 <= age < 50:
        age_factor = 0.9
    else:
        age_factor = 0.8

    daily_increment = 0.05
    plan = {
        'pushups': int(base_reps['pushups'] * (1 + daily_increment * day) * bmi_factor * age_factor),
        'situps': int(base_reps['situps'] * (1 + daily_increment * day) * bmi_factor * age_factor),
        'squats': int(base_reps['squats'] * (1 + daily_increment * day) * bmi_factor * age_factor)
    }
    return plan


def insert_exercise_plan(username, day, exercise_plan):
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO exercise_plan 
        (username, day, pushups, squats, situps, pushups_completed, squats_completed, situps_completed, completion)
        VALUES (%s, %s, %s, %s, %s, 0, 0, 0, 0)
    """, (username, day, exercise_plan['pushups'], exercise_plan['squats'], exercise_plan['situps']))
    conn.commit()
    cur.close()
    conn.close()


def get_exercise_plan(username, day):
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT day, pushups, squats, situps, pushups_completed, squats_completed, situps_completed, completion
        FROM exercise_plan WHERE username = %s AND day = %s
    """, (username, day))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    return {
        'day': row[0], 'pushups': row[1], 'squats': row[2], 'situps': row[3],
        'pushups_completed': row[4], 'squats_completed': row[5], 'situps_completed': row[6],
        'completion': round(row[7], 2) if row[7] else 0
    }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)