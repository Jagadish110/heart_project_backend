from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from fastapi.middleware.cors import CORSMiddleware
import pickle
import numpy as np

# Load the model
model = pickle.load(open("heart_webpage.pkl", "rb"))

# Initialize FastAPI app
app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PostgreSQL connection settings (Render DB credentials)
def get_db():
    return psycopg2.connect(
        host="dpg-cnsnm4ocn0vc73bl4gm0-a.singapore-postgres.render.com",
        database="hotdb",
        user="hotdb_user",
        password="YmzCekSCLFSPdo1uw3xvBUmdU4cljKm1"
    )

# Pydantic models
class InputData(BaseModel):
    email: str
    age: int
    sex: int
    Chest_Pain: int
    Resting_Blood_Pressure: int
    Cholesterol: int
    Fasting_Blood_Sugar: int
    Resting_ECG_Results: int
    Maximum_Heart_Rate_Achieved: int
    Chest_Pain_During_Exercise: int
    ST_depression_level: float
    Slope_of_ST_segment: int

class User(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

# Create necessary tables
def create_tables():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(100) NOT NULL
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_inputs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            age INTEGER,
            sex INTEGER,
            Chest_Pain INTEGER,
            Resting_Blood_Pressure INTEGER,
            Cholesterol INTEGER,
            Fasting_Blood_Sugar INTEGER,
            Resting_ECG_Results INTEGER,
            Maximum_Heart_Rate_Achieved INTEGER,
            Chest_Pain_During_Exercise INTEGER,
            ST_depression_level FLOAT,
            Slope_of_ST_segment INTEGER,
            prediction_result INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
    """)

    conn.commit()
    cursor.close()
    conn.close()

# Create tables when app starts
@app.on_event("startup")
def on_startup():
    create_tables()

# API Endpoints
@app.get("/")
def read_root():
    return {"message": "Heart Disease Predictor API is Running."}

@app.post("/predict")
def predict(data: InputData):
    conn = get_db()
    cursor = conn.cursor()

    # Check user by email
    cursor.execute("SELECT id FROM users WHERE email=%s", (data.email,))
    user = cursor.fetchone()

    if user is None:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    user_id = user[0]

    input_features = np.array([[
        data.age, data.sex, data.Chest_Pain,
        data.Resting_Blood_Pressure, data.Cholesterol,
        data.Fasting_Blood_Sugar, data.Resting_ECG_Results,
        data.Maximum_Heart_Rate_Achieved, data.Chest_Pain_During_Exercise,
        data.ST_depression_level, data.Slope_of_ST_segment
    ]])

    prediction = model.predict(input_features)
    prediction_result = int(prediction[0])

    # Save input and prediction to DB
    cursor.execute("""
        INSERT INTO user_inputs (
            user_id, age, sex, Chest_Pain, Resting_Blood_Pressure, Cholesterol,
            Fasting_Blood_Sugar, Resting_ECG_Results, Maximum_Heart_Rate_Achieved,
            Chest_Pain_During_Exercise, ST_depression_level, Slope_of_ST_segment,
            prediction_result
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        user_id, data.age, data.sex, data.Chest_Pain, data.Resting_Blood_Pressure,
        data.Cholesterol, data.Fasting_Blood_Sugar, data.Resting_ECG_Results,
        data.Maximum_Heart_Rate_Achieved, data.Chest_Pain_During_Exercise,
        data.ST_depression_level, data.Slope_of_ST_segment,
        prediction_result
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return {"prediction": prediction_result}

@app.post("/register")
def register(user: User):
    conn = get_db()
    cursor = conn.cursor()

    # Check if email already exists
    cursor.execute("SELECT * FROM users WHERE email=%s", (user.email,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")

    cursor.execute(
        "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
        (user.username, user.email, user.password)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return {"message": "User registered successfully"}

@app.post("/login")
def login(req: LoginRequest):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email=%s AND password=%s",
        (req.email, req.password)
    )

    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {"message": "Login successful", "email": req.email}
