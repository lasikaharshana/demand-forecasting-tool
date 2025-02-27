# 📊 Demand Forecasting Tool

#### Video Demo: https://youtu.be/m2Ks4qbhV4U
#### Description:

## 📌 Introduction
Demand Forecasting Tool is a web-based application that helps businesses analyze sales trends and forecast future demand using historical data. It allows users to upload **forecasted data**, visualize **sales trends**, and export **reports to Excel and PDF**.

This project was created as my final submission for **CS50x**.

---

## 🛠 Technologies Used
This project is built using:
- **Flask** – Backend framework for handling requests.
- **SQLite** – Database for storing user data and sales records.
- **Bootstrap** – UI framework for styling.
- **Chart.js** – For interactive sales trend visualizations.
- **Flask-Login** – For user authentication.
- **Pandas & ReportLab** – For exporting reports to Excel and PDF.

---

## 🎯 Features
- **User Authentication** – Secure login and registration.
- **Upload Forecasted Data** – Accepts CSV files with sales forecasts.
- **View Sales Trends** – Interactive graph for demand forecasting.
- **Custom Forecast Periods** – Choose between 3-day, 7-day, or 14-day forecasts.
- **Export Reports** – Download forecasted data as **Excel or PDF**.
- **Deployed on Render** – Live web app available.

---

## 📂 Project Files
- `app.py` – Main Flask application handling all routes and logic.
- `templates/` – HTML files for pages (login, upload, forecast, insights).
- `static/` – CSS, JavaScript, and images for UI.
- `uploads/` – Folder where user-uploaded CSV files are temporarily stored.
- `requirements.txt` – Python dependencies for running the project.
- `README.md` – Documentation for the project.

---

## 📝 How to Run Locally
1️⃣ **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/demand-forecasting-tool.git
   cd demand-forecasting-tool