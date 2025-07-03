from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
import plotly.graph_objects as go
import json
from plotly.utils import PlotlyJSONEncoder
from datetime import datetime, timedelta

app = Flask(__name__)

# MongoDB Configuration
client = MongoClient("mongodb://localhost:27017/")
db = client["risk_management"]
risks_collection = db["risks"]
threats_collection = db["threats"]
assessments_collection = db["assessments"]

# Fungsi untuk menentukan risk level berdasarkan data yang diisi user
def determine_risk_level(user_data):
    if 'critical' in user_data.lower() or 'high' in user_data.lower():
        return 'High'
    elif 'moderate' in user_data.lower() or 'medium' in user_data.lower():
        return 'Medium'
    else:
        return 'Low'

# Fungsi untuk menentukan recommended controls berdasarkan risk level
def determine_recommended_controls(risk_level):
    controls = {
        'High': 'Implement strong encryption, multi-factor authentication, and continuous monitoring.',
        'Medium': 'Ensure access controls, perform regular audits, and implement network segmentation.',
        'Low': 'Keep software updated, apply basic security policies, and perform periodic reviews.'
    }
    return controls.get(risk_level, 'Standard security measures.')

# Dashboard Route
@app.route("/")
def dashboard():
    risks_data = list(risks_collection.find({}, {"_id": 0}))
    threats_data = list(threats_collection.find({}, {"_id": 0}))

    # Mengambil data dari assessments collection untuk 6 bulan terakhir
    six_months_ago = datetime.now() - timedelta(days=180)
    assessments_data = list(assessments_collection.find({"date": {"$gte": six_months_ago}}, {"_id": 0}))

    # Membuat data untuk grafik (Total Risks, Critical Risks, Mitigated Risks, Active Threats)
    months = [datetime.now() - timedelta(days=i*30) for i in range(6)]
    months = [month.strftime("%b %Y") for month in months]
    
    total_risks = [10, 9, 8, 7, 6, 5]  # Angka dummy untuk Total Risks
    critical_risks = [4, 3, 5, 2, 6, 1]  # Angka dummy untuk Critical Risks
    mitigated_risks = [3, 2, 4, 5, 4, 3]  # Angka dummy untuk Mitigated Risks
    active_threats = [2, 4, 3, 2, 1, 3]  # Angka dummy untuk Active Threats

    # Membuat grafik dengan menggunakan Plotly
    bar_chart = go.Figure()

    bar_chart.add_trace(go.Bar(
        x=months,
        y=total_risks,
        name="Total Risks",
        marker_color="blue",
        text=total_risks,
        textposition='outside'
    ))

    bar_chart.add_trace(go.Bar(
        x=months,
        y=critical_risks,
        name="Critical Risks",
        marker_color="red",
        text=critical_risks,
        textposition='outside'
    ))

    bar_chart.add_trace(go.Bar(
        x=months,
        y=mitigated_risks,
        name="Mitigated Risks",
        marker_color="green",
        text=mitigated_risks,
        textposition='outside'
    ))

    bar_chart.add_trace(go.Bar(
        x=months,
        y=active_threats,
        name="Active Threats",
        marker_color="yellow",
        text=active_threats,
        textposition='outside'
    ))

    bar_chart.update_layout(
        barmode='group',
        title="Risk Assessment Overview (Last 6 Months)",
        xaxis_title="Month",
        yaxis_title="Count",
        showlegend=True
    )

    bar_chart_json = json.dumps(bar_chart, cls=PlotlyJSONEncoder)

    # Threat Trends Chart
    line_chart = go.Figure(
        data=[go.Scatter(
            x=[threat["month"] for threat in threats_data],
            y=[threat["threats"] for threat in threats_data],
            mode="lines+markers",
            line=dict(color="indigo"),
        )]
    )
    line_chart.update_layout(title="Threat Trends", xaxis_title="Month", yaxis_title="Threats")

    line_chart_json = json.dumps(line_chart, cls=PlotlyJSONEncoder)

    return render_template(
        "dashboard.html",
        bar_chart_json=bar_chart_json,
        line_chart_json=line_chart_json,
    )

# Assessment Page
@app.route("/assessments")
def assessments():
    return render_template("assessments.html")

# Save Assessment (with Auto Risk Level & Recommended Controls)
@app.route("/save-assessment", methods=["POST"])
def save_assessment():
    data = request.json

    # Menggabungkan semua jawaban user untuk dianalisis
    combined_data = " ".join(data.values())

    # Menentukan Risk Level & Recommended Controls
    risk_level = determine_risk_level(combined_data)
    recommended_controls = determine_recommended_controls(risk_level)

    # Tambahkan tanggal assessment
    data.update({
        "risk_level": risk_level,
        "recommended_controls": recommended_controls,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

    # Simpan ke MongoDB
    assessments_collection.insert_one(data)

    return jsonify({"message": "Assessment saved successfully!", "risk_level": risk_level, "recommended_controls": recommended_controls})

# Reports Page
@app.route("/reports")
def reports():
    reports_data = list(assessments_collection.find({}, {"_id": 0}))
    project_names = list(set(report["project_name"] for report in reports_data))
    
    return render_template("reports.html", reports=reports_data, project_names=project_names)

# API untuk mengambil Risk Chart berdasarkan proyek
@app.route("/get-risk-chart", methods=["POST"])
def get_risk_chart():
    data = request.json
    project_name = data.get("project_name")

    assessments = list(assessments_collection.find({"project_name": project_name}, {"_id": 0}))

    risk_counts = {"High": 0, "Medium": 0, "Low": 0}
    for assessment in assessments:
        risk_counts[assessment["risk_level"]] += 1

    risk_chart = go.Figure(data=[
        go.Bar(x=list(risk_counts.keys()), y=list(risk_counts.values()), marker_color=["red", "orange", "green"])
    ])
    risk_chart.update_layout(title=f"Risk Chart for {project_name}", xaxis_title="Risk Level", yaxis_title="Count")

    return jsonify({"risk_chart_json": json.dumps(risk_chart, cls=PlotlyJSONEncoder)})

# Profile Page
@app.route("/profile")
def profile():
    return render_template("profile.html")

# Run Flask App
if __name__ == "__main__":
    app.run(debug=True)