from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from passlib.context import CryptContext
import psycopg2
import pickle
import numpy as np

# Load your trained ML model (make sure the .pkl file is available)
model = pickle.load(open("heart_webpage.pkl", "rb"))

# FastAPI app setup
app = FastAPI()

# CORS configuration (update allowed origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Database connection setup (update with your real DB credentials)
def get_db():
    import os, psycopg2
    db_url = os.environ["DATABASE_URL"]
    print("DB_URL:", db_url)  # Debug print
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    print("Final DB_URL:", db_url)  # Debug print
    return psycopg2.connect(db_url)


       
    

# Pydantic models
class InputData(BaseModel):
    username: str
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
    username: str
    password: str

# Create tables in database (if not existing)
def create_tables():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
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

@app.on_event("startup")
def on_startup():
    create_tables()

@app.get("/")
def read_root():
    return {"message": "Heart Disease Predictor API is Running."}

@app.post("/register")
def register(user: User):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE username=%s", (user.username,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Username already taken")
        hashed_pw = hash_password(user.password)
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (user.username, user.email, hashed_pw)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return {"message": "User registered successfully"}

@app.post("/login")
def login(req: LoginRequest):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT password FROM users WHERE username=%s", (req.username,))
        result = cursor.fetchone()
        if not result or not verify_password(req.password, result[0]):
            raise HTTPException(status_code=401, detail="Invalid username or password")
    finally:
        cursor.close()
        conn.close()
    return {"message": "Login successful", "username": req.username}

@app.post("/predict")
def predict(data: InputData):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM users WHERE username=%s", (data.username,))
        user = cursor.fetchone()
        if user is None:
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
        # Store input and prediction
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
            data.ST_depression_level, data.Slope_of_ST_segment, prediction_result
        ))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return {"prediction": prediction_result}







