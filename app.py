import os
import io
import matplotlib
matplotlib.use('Agg') # Required to save plots as images
import matplotlib.pyplot as plt
import base64
import sqlite3
import pandas as pd
from flask import Flask, request, render_template, redirect, url_for, flash, session, send_file
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = "your_secret_key" # Change this to a random value for security
app.config["SESSION_TYPE"] = "filesystem"

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login" # Redirect user to login page if not logged in

# Configure database
DATABASE = "sales.db"

# Create database connection
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

# Migration Function: Add user_id column to sales table
def add_user_id_column():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the column exists
    cursor.execute("PRAGMA table_info(sales);")
    columns = [column[1] for column in cursor.fetchall()]
    
    if "user_id" not in columns:
        print("Adding user_id column to sales table...")
        cursor.execute("ALTER TABLE sales ADD COLUMN user_id INTEGER;")
        conn.commit()
    else:
        print("user_id column already exists.")

    conn.close()

# Create sales table if it doesn't exist
def create_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create sales table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            product TEXT,
            quantity INTEGER,
            user_id INTEGER
        )
    ''')

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

# Call function to ensure table exists
create_table()

# Run migration to add user_id if missing
add_user_id_column()

# Set the folder where uploaded files will be stored
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER



class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    if not user_id:
        return None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (int(user_id),))
    user = cursor.fetchone()
    conn.close()

    if user:
        return User(id=user["id"], username=user["username"], password=user["password"])
    return None



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists. Choose another.", "danger")
        
        conn.close()

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            login_user(User(id=user["id"], username=user["username"], password=user["password"]))
            flash("Login successful!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid credentials. Try again.", "danger")

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route('/')
def home():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sales ORDER BY date DESC")
    sales_data = cursor.fetchall()
    conn.close()

    return render_template("index.html", sales=sales_data)

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return render_template("index.html", message="No file uploaded", sales=[])
    
    file = request.files["file"]

    if file.filename == "":
        return render_template("index.html", message="No selected file", sales=[])
    
    if file and file.filename.endswith(".csv"):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        
        # Read the CSV file
        data = pd.read_csv(file_path)

        # Debugging: Print the column names
        print("CSV Columns:", data.columns.to_list())   

        # Validate if required columns exist
        required_columns = {"date", "product", "quantity"}
        if not required_columns.issubset(data.columns):
            return render_template("index.html", message=f"CSV must have columns: {required_columns}. Found: {data.columns.to_list()}")
        
        # Connect to the database and clear old data before inserting new records
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sales")
        conn.commit()

        # Insert new data
        for _, row in data.iterrows():
            cursor.execute("INSERT INTO sales (date, product, quantity, user_id) VALUES (?, ?, ?, ?)", (row["date"], row["product"], row["quantity"], int(current_user.id)))
        
        conn.commit()
        conn.close()

        # Fetch the updated sales data
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sales ORDER BY date DESC")
        sales_data = cursor.fetchall()
        conn.close()

        return render_template("index.html", message="File uploaded and data stored successfully!", sales=sales_data)
    
    
    return render_template("index.html", message="Invalid file type. Please upload a CSV file", sales=[])

@app.route("/forecast")
@login_required
def forecast():
    # Get the selected forecast period from user (default to 7)
    window_size = request.args.get("window_size", default=7, type=int)

    # Debugging print
    print("Current User ID: {current_user.id}")


    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT date, SUM(quantity) as total_quantity FROM sales WHERE user_id=? GROUP BY date ORDER BY date ASC", (int(current_user.id),))
    sales_data = cursor.fetchall()

    # Debugging: Print fetched sales data
    print("Fetched Sales Data:", sales_data)

    conn.close()

    # Debugging: Print fetched sales data
    print("Raw sales data from DB:", sales_data)

    if not sales_data or len(sales_data) < window_size:
        return render_template("forecast.html", message="Not enough data for forecasting (at least {window_size} days required).")

    # Convert sales data to Pandas DataFrame
    import pandas as pd
    df = pd.DataFrame(sales_data, columns=["date", "total_quantity"])

    # Debugging: Check if DataFrame is created correctly
    print("DataFrame Created:")
    print(df.head())

    # Ensure 'date' column exists before proceeding
    if "date" not in df.columns:
        return render_template("forecast.html", message="Error: 'date' column missing in the dataset.")

    # Convert 'date' column to datetime and handle errors
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")

    # Remove invalid dates
    df.dropna(subset=["date"], inplace=True)

    # Debugging: Check after date conversion
    print("After date conversion:")
    print(df.head())

    # If DataFrame is empty after cleaning, return an error message
    if df is None or df.empty:
        return render_template("forecast.html", message="Error: No valid sales data found.")

    df.set_index("date", inplace=True)

    # Apply the user-selected moving avereage
    df["forecast"] = df["total_quantity"].rolling(window=window_size, min_periods=1).mean()

    # Drop NaN values (but only if we still have data)
    if df["forecast"].isna().all():
        return render_template("forecast.html", message="Error: Not enough data points for forecasting.")

    df.dropna(inplace=True)  # Remove rows with NaN forecast values

    # Ensure there is still data left
    if df.empty:
        return render_template("forecast.html", message="Error: No valid forecast data available.")


    return render_template("forecast.html", forecast_data=df.reset_index().to_dict(orient="records"), window_size=window_size)

@app.route("/insights")
@login_required
def insights():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Best-selling product
    cursor.execute("SELECT product, SUM(quantity) as total_sold FROM sales WHERE user_id=? GROUP BY product ORDER BY total_sold DESC LIMIT 1", (int(current_user.id),))
    best_selling_product = cursor.fetchone()

    # Lowest sales day
    cursor.execute("SELECT date, SUM(quantity) as total_sold FROM sales WHERE user_id=? GROUP BY date ORDER BY total_sold ASC LIMIT 1", (int(current_user.id),))
    lowest_sales_day = cursor.fetchone()

    # Overall sales trend (comparing first and last 7 days)
    cursor.execute("SELECT date, SUM(quantity) as total_sold FROM sales GROUP BY date ORDER BY date ASC")
    sales_data = cursor.fetchall()

    conn.close()

    import pandas as pd
    df = pd.DataFrame(sales_data, columns=["date", "total_sold"])
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")

    if len(df) >= 14:
        first_week_avg = df["total_sold"].head(7).mean()
        last_week_avg = df["total_sold"].tail(7).mean()
        if last_week_avg > first_week_avg:
            sales_trend = "📈 Increasing"
        elif last_week_avg < first_week_avg:
            sales_trend = "📉 Decreasing"
        else:
            sales_trend = "➡️ Stable"
    else:
        sales_trend = "Not enough data to determine trend"

    return render_template("insights.html", 
                           best_selling_product=best_selling_product, 
                           lowest_sales_day=lowest_sales_day, 
                           sales_trend=sales_trend)


@app.route("/clear_data")
def clear_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sales")
    conn.commit()
    conn.close()

    return render_template("index.html", message="All data has been cleared!")

def clear_data_on_start():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sales")
    conn.commit()
    conn.close()

clear_data_on_start() # Clear data on app start

@app.route("/export/forecast/excel")
@login_required
def export_forecast_excel():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT date, SUM(quantity) as total_quantity FROM sales WHERE user_id=? GROUP BY date ORDER BY date ASC", (int(current_user.id),))
    sales_data = cursor.fetchall()
    conn.close()

    if len(sales_data) < 7:
        return "Not enough data for forecasting (at least 7 days required)."

    import pandas as pd
    df = pd.DataFrame(sales_data, columns=["Date", "Total Quantity"])
    df["Forecast"] = df["Total Quantity"].rolling(window=7, min_periods=1).mean()

    # Keep only forecasted data
    df = df[["Date", "Forecast"]]

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Forecast Data")

    output.seek(0)
    return send_file(output, as_attachment=True, download_name="forecasted_data.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route("/export/forecast/pdf")
@login_required
def export_forecast_pdf():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT date, SUM(quantity) as total_quantity FROM sales WHERE user_id=? GROUP BY date ORDER BY date ASC", (int(current_user.id),))
    sales_data = cursor.fetchall()
    conn.close()

    if len(sales_data) < 7:
        return "Not enough data for forecasting (at least 7 days required)."

    import pandas as pd
    df = pd.DataFrame(sales_data, columns=["Date", "Total Quantity"])
    df["Forecast"] = df["Total Quantity"].rolling(window=7, min_periods=1).mean()

    # Keep only forecasted data
    df = df[["Date", "Forecast"]]

    output = BytesIO()
    p = canvas.Canvas(output, pagesize=letter)
    width, height = letter

    p.setFont("Helvetica-Bold", 14)
    p.drawString(200, height - 50, "Forecasted Data Report")

    p.setFont("Helvetica", 12)
    y_position = height - 100

    p.drawString(100, y_position, "Date")
    p.drawString(300, y_position, "Forecasted Quantity")
    y_position -= 20

    for index, row in df.iterrows():
        p.drawString(100, y_position, str(row["Date"]))
        p.drawString(300, y_position, str(round(row["Forecast"], 2)))
        y_position -= 20

    p.save()
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="forecasted_data.pdf", mimetype="application/pdf")


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
