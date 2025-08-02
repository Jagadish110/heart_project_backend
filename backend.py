from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import pymysql, os, hashlib, pickle
import numpy as np

app = FastAPI()


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Database connection
import psycopg2

def get_db():
    return psycopg2.connect(
        host="dpg-d26vljggjchc73en01s0-a",
        user="heart_database_tx6b_user",
        password="FsIhdoLR6I6iz1PzNycw7tcLwHBFW6bT",
        database="heart_database_tx6b",
        port=5432
    )


# Hashing
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Models
class Register(BaseModel):
    username: str
    email: str
    password: str

class Login(BaseModel):
    username: str
    password: str

class HeartDisease(BaseModel):
    user_id: int
    age: int 
    sex: int  
    cp: int 
    trestbps: int 
    chol: int 
    fbs: int 
    restecg: int 
    thalach: int
    exang: int 
    oldpeak: float 
    slope: int

# Routes
@app.post("/register")
def register_user(user: Register):
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s", (user.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="User already exists")

        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (user.username, user.email, user.password)
        )
        db.commit()
        return {"message": "User registered successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))  # <- Important


@app.post("/login")
def login(user: Login):
    db = get_db()
    cursor = db.cursor()
    hashed = hash_password(user.password)
    cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (user.username, hashed))
    data = cursor.fetchone()
    cursor.close()
    db.close()
    if data:
        return {"message": "Login success", "user_id": data["id"]}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/predict")
def predict(data: HeartDisease):
    with open("heart_webpage.pkl", "rb") as f:
        model = pickle.load(f)

    input_data = [data.age, data.sex, data.cp, data.trestbps, data.chol, data.fbs,
                  data.restecg, data.thalach, data.exang, data.oldpeak, data.slope]
    
    prediction = model.predict([input_data])[0]

    # Save input + prediction
    db = get_db()
    cursor = db.cursor()
    sql = """
        INSERT INTO user_inputs (
            user_id, age, sex, Chest_Pain, Resting_Blood_Pressure, Cholesterol,
            Fasting_Blood_Sugar, Resting_ECG_Results, Maximum_Heart_Rate_Achieved,
            Chest_Pain_During_Exercise, ST_depression_level, Slope_of_ST_segment, prediction_result
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(sql, (data.user_id, *input_data, prediction))
    db.commit()
    cursor.close()
    db.close()

    return {"prediction": int(prediction)}

