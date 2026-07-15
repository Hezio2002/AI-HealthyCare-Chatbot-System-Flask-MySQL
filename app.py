from flask import Flask, request, jsonify, render_template, redirect
import mysql.connector
import pdfplumber
import json
import re
from datetime import date

app = Flask(__name__)

# ---- MySQL Database Configuration ----
db_config = {
    'host': 'localhost',
    'user': 'root',           # your MySQL username
    'password': '',           # your MySQL password (empty if no password)
    'database': 'hospital'    # your database name
}

# ---- Load Doctor Info from JSON ----
def load_doctors():
    with open('doctors.json', 'r') as f:
        return json.load(f)

def search_doctor_info(query):
    doctors = load_doctors()
    for doctor in doctors:
        if doctor["specialization"].lower() in query.lower():
            return f"{doctor['name']} ({doctor['specialization']}) is available at {doctor['available_time']}."
    return None

# ---- PDF Search ----
def extract_keywords(query):
    stopwords = {"what", "is", "are", "the", "a", "an", "about", "tell", "me", "explain", "who", "define", "please", "do", "you", "can"}
    return [word for word in query.lower().split() if word not in stopwords]

def search_pdf(query):
    keywords = extract_keywords(query)
    if not keywords:
        return None
    try:
        with pdfplumber.open("medical_info.pdf") as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                for sentence in re.split(r'(?<=[.!?])\s+', text):
                    if any(word in sentence.lower() for word in keywords):
                        return f"I found information: {sentence}"
    except Exception as e:
        return f"Error while reading PDF: {e}"
    return None

# ---- Get patient count for a doctor ----
def get_patient_count(doctor_name):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM appointments WHERE doctor = %s", (doctor_name,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] if result else 0
    except Exception as e:
        return f"Error retrieving patient count: {e}"

# ---- Routes ----
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/doctors')
def doctors():
    return render_template('doctors.html')

@app.route('/appointment')
def appointment():
    return render_template('appointment.html')

# Save appointment to MySQL
@app.route('/book', methods=['POST'])
def book_appointment():
    name = request.form.get('name')
    doctor = request.form.get('doctor')
    date = request.form.get('date')
    time = request.form.get('time')
    notes = request.form.get('notes')

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO appointments (name, doctor, date, time, notes)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, doctor, date, time, notes))
        conn.commit()
        cursor.close()
        conn.close()
        return "<h2>Appointment booked successfully!</h2><a href='/'>Back to Home</a>"
    except Exception as e:
        return f"<h2>Failed to book appointment:</h2> {str(e)}"

# Chatbot endpoint
from datetime import date

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message').strip().lower()
    response = ""

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        if user_message in ["hi", "hello"]:
            response = "Hello! How can I assist you at HealthyCare Hospital?"

        elif user_message in ["bye", "goodbye"]:
            response = "Goodbye! Stay healthy!"

        elif "today's appointments" in user_message or "appointments today" in user_message:
            today = date.today().isoformat()
            cursor.execute("SELECT * FROM appointments WHERE date = %s", (today,))
            results = cursor.fetchall()
            if results:
                response = "📅 Today's Appointments:\n"
                for row in results:
                    response += f"- {row['name']} with {row['doctor']} at {row['time']}\n"
            else:
                response = "There are no appointments scheduled for today."

        elif "how many patients" in user_message:
            match = re.search(r"dr\.?\s+([a-z\s]+)", user_message)
            if match:
                doctor_name = "Dr. " + match.group(1).title().strip()
                cursor.execute("SELECT COUNT(*) as count FROM appointments WHERE doctor LIKE %s", (f"%{doctor_name}%",))
                count = cursor.fetchone()["count"]
                response = f"{doctor_name} has {count} patient(s) with appointments."
            else:
                response = "Please specify the doctor's name."


        elif "appointment for" in user_message or "patient" in user_message:
            match = re.search(r"(appointment|patient)\s+(for\s+)?([a-z\s]+)", user_message)
            if match:
                patient_name = match.group(3).title().strip()
                cursor.execute("SELECT * FROM appointments WHERE name = %s", (patient_name,))
                results = cursor.fetchall()
                if results:
                    response = f"🧾 Appointment(s) for {patient_name}:\n"
                    for row in results:
                        response += f"- {row['doctor']} on {row['date']} at {row['time']}\n"
                else:
                    response = f"No appointments found for {patient_name}."
            else:
                response = "Please specify the patient's name."

        else:
            disease_info = search_pdf(user_message)
            doctor_info = search_doctor_info(user_message)
            if disease_info and doctor_info:
                response = f"📚 Disease Info:\n{disease_info}\n\n👨‍⚕️ Recommended Doctor:\n{doctor_info}"
            elif disease_info:
                response = f"📚 Disease Info:\n{disease_info}"
            elif doctor_info:
                response = f"👨‍⚕️ Recommended Doctor:\n{doctor_info}"
            else:
                response = "Sorry, I couldn't find relevant information."

        cursor.close()
        conn.close()

    except Exception as e:
        response = f"Error processing your request: {str(e)}"

    return jsonify({"reply": response})



if __name__ == "__main__":
    app.run(debug=True)

