import warnings
from flask import redirect, session
from sklearn.exceptions import InconsistentVersionWarning
warnings.filterwarnings("ignore", category=InconsistentVersionWarning)

import pickle
import numpy as np
import os
import pandas as pd
from flask import Flask, render_template, request

app = Flask(
    __name__,
    template_folder="../frontend/templates",
    static_folder="../frontend/static"
)
app.secret_key = "crop_ai_secret"

# ✅ CORRECTED HERE (__file__)
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load model & encoders
model = pickle.load(open(os.path.join(BASE_PATH, "crop_model.pkl"), "rb"))
le_area = pickle.load(open(os.path.join(BASE_PATH, "le_area.pkl"), "rb"))
le_item = pickle.load(open(os.path.join(BASE_PATH, "le_item.pkl"), "rb"))

area_options = list(le_area.classes_)
crop_options = list(le_item.classes_)

@app.context_processor
def inject_options():
    return dict(area_options=area_options, crop_options=crop_options)

# ------------------ LANDING PAGE ------------------
@app.route("/")
def home():
    return render_template("home.html")

# ------------------ FORM PAGE ------------------
@app.route("/predict", methods=["GET", "POST"])
def predict():

    # 🔐 LOGIN CHECK
    if "user" not in session:
        return redirect("/login")

    if request.method == "GET":
        return render_template("index.html")

    try:

        area = request.form["Area"]
        crop = request.form["Item"]

        year = float(request.form["Year"])
        rainfall = float(request.form["average_rain_fall_mm_per_year"])
        pesticides = float(request.form["pesticides_tonnes"])
        temp = float(request.form["avg_temp"])

        # Encode categorical values
        area_encoded = le_area.transform([area])[0]
        crop_encoded = le_item.transform([crop])[0]

        # Prepare input
        input_data = np.array([[area_encoded, crop_encoded, year, rainfall, pesticides, temp]])

        prediction = round(model.predict(input_data)[0], 2)

        # ---------- SAVE TO EXCEL ----------
        file_path = os.path.join(BASE_PATH, "user_inputs.xlsx")

        df_new = pd.DataFrame([{
            "Email": session["user"],
            "Area": area,
            "Crop": crop,
            "Year": year,
            "Rainfall": rainfall,
            "Pesticides": pesticides,
            "Avg_Temp": temp,
            "Predicted_Yield": prediction
        }])

        try:
            if os.path.exists(file_path):
                df_old = pd.read_excel(file_path, engine="openpyxl")
                df_final = pd.concat([df_old, df_new], ignore_index=True)
            else:
                df_final = df_new

            df_final.to_excel(file_path, index=False, engine="openpyxl")

        except Exception as excel_error:
            print("Excel Error:", excel_error)

        return render_template("index.html", prediction=prediction)

    except Exception as e:
        print("Prediction Error:", e)
        return render_template("index.html", prediction="Prediction Error — Check Inputs")
    
# ------------------ DASHBOARD PAGE ------------------
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    file_path = os.path.join(BASE_PATH, "user_inputs.xlsx")

    if os.path.exists(file_path):

        df = pd.read_excel(file_path, engine="openpyxl")

        labels = df["Crop"].tolist()
        values = df["Predicted_Yield"].tolist()

        return render_template(
            "dashboard.html",
            labels=labels,
            values=values
        )

    else:
        return render_template(
            "dashboard.html",
            labels=[],
            values=[]
        )

from werkzeug.utils import secure_filename

# ---------------- USER REGISTER ----------------

@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "GET":
        return render_template("user/register.html")

    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]

    # 📸 Profile Photo
    photo = request.files["photo"]

    # secure filename (removes spaces & special characters)
    photo_filename = secure_filename(photo.filename)

    # profile folder path
    profile_folder = os.path.join(
        BASE_PATH,
        "frontend",
        "static",
        "profiles"
    )

    # folder automatically create if not exists
    os.makedirs(profile_folder, exist_ok=True)

    # image save path
    photo_path = os.path.join(profile_folder, photo_filename)

    # save photo
    photo.save(photo_path)

    # 📄 Excel file path
    file_path = os.path.join(BASE_PATH, "users.xlsx")

    new_user = pd.DataFrame([{
        "Name": name,
        "Email": email,
        "Password": password,
        "Photo": photo_filename
    }])

    if os.path.exists(file_path):
        old = pd.read_excel(file_path, engine="openpyxl")
        data = pd.concat([old, new_user], ignore_index=True)
    else:
        data = new_user

    data.to_excel(file_path, index=False, engine="openpyxl")

    return redirect("/login")
# ---------------- USER LOGIN ----------------

@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "GET":
        return render_template("user/login.html")

    email = request.form["email"]
    password = request.form["password"]

    file_path = os.path.join(BASE_PATH, "users.xlsx")

    if not os.path.exists(file_path):
        return "No users registered"

    df = pd.read_excel(file_path)

    user = df[(df["Email"] == email) & (df["Password"] == password)]

    if not user.empty:

        # user session start
        session["user"] = email
        session["photo"] = user.iloc[0]["Photo"]

    
        return redirect("/predict")

    return "Invalid Login"

# ---------------- USER DASHBOARD ----------------

@app.route("/user-dashboard")
def user_dashboard():

    if "user" not in session:
        return redirect("/login")

    return render_template("user/user_dashboard.html")

# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.pop("user", None)
    session.pop("photo", None)

    return redirect("/")

# ---------------- ADMIN LOGIN ----------------

@app.route("/admin", methods=["GET","POST"])
def admin_login():

    if request.method == "GET":
        return render_template("admin/admin_login.html")

    username = request.form["username"]
    password = request.form["password"]

    if username == "admin" and password == "admin123":

        session["admin"] = username

        return redirect("/admin-dashboard")

    return "Invalid Admin Login"


# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin-dashboard")
def admin_dashboard():

    if "admin" not in session:
        return redirect("/admin")

    return render_template("admin/admin_dashboard.html")


# ✅ CORRECTED HERE (__main__)
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)