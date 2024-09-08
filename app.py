from flask import Flask, render_template, request, jsonify, send_file
import pyodbc
from fpdf import FPDF
from datetime import datetime
import os
import csv

app = Flask(__name__)

# Get the user's Downloads directory
DOWNLOADS_DIR = os.path.expanduser('~/Downloads')
FILES_DIR = os.path.expanduser('~/Downloads')
# Ensure Downloads directory exists (though it should by default)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# Database connection string
db_conn_str = 'DRIVER={SQL Server};SERVER=127.0.0.1;DATABASE=GEC_EM_GF;UID=admin;PWD=admin@123'

def get_db_connection():
    return pyodbc.connect(db_conn_str)

def get_timestamp_column(table):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = ? AND DATA_TYPE = 'datetime'
    """
    cursor.execute(query, table)
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

@app.route('/')
def index():
    # Predefined report options with corresponding table names
    report_options = {
        "Alarm Report": "Consumption_Report",
        "Audit Report": "FILTER",
        "Service Report": "INCOMER1",
        "Sanitization Report": "IOT_LAB"
    }
    return render_template('index.html', report_options=report_options)

@app.route('/fetch_columns', methods=['POST'])
def fetch_columns():
    try:
        table = request.form['table']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        interval = int(request.form['interval'])

        timestamp_column = get_timestamp_column(table)
        if not timestamp_column:
            return jsonify({"error": "No timestamp column found"}), 400

        start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M").strftime("%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(end_time, "%Y-%m-%dT%H:%M").strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db_connection()
        cursor = conn.cursor()
        query = f"""
            SELECT * FROM {table}
            WHERE {timestamp_column} BETWEEN ? AND ?
        """
        cursor.execute(query, start_time, end_time)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

        if not rows:
            return jsonify({"columns": columns, "data": []})

        filtered_data = []
        last_time = None
        for row in rows:
            timestamp = row[columns.index(timestamp_column)]
            if not last_time or (timestamp - last_time).seconds >= interval * 60:
                filtered_data.append([str(item) for item in row])
                last_time = timestamp

        conn.close()
        return jsonify({"columns": columns, "data": filtered_data})

    except Exception as e:
        print(f"Error fetching columns: {e}")
        return jsonify({"error": str(e)}), 500

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, self.title, 0, 1, 'C')  # Title

        # Adjust the font size and add extra space for 'From' and 'To' dates
        self.set_font('Arial', '', 10)  # Set to size 8
        self.ln(2)  # Add more space between title and dates
        self.cell(0, 10, f'From: {self.from_date} To: {self.to_date}', 0, 1, 'C')  # Dates below title
        self.ln(10)  # Add extra space after the dates to avoid overlap

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    try:
        table = request.form.get('table')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        interval = request.form.get('interval')
        report_name = request.form.get('report_name')

        if not table or not start_time or not end_time or not interval or not report_name:
            return jsonify({"message": "Missing required parameters"}), 400

        interval = int(interval)
        timestamp_column = get_timestamp_column(table)
        if not timestamp_column:
            return jsonify({"message": "No timestamp column found"}), 400

        start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M").strftime("%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(end_time, "%Y-%m-%dT%H:%M").strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db_connection()
        cursor = conn.cursor()
        query = f"""
            SELECT * FROM {table}
            WHERE {timestamp_column} BETWEEN ? AND ?
        """
        cursor.execute(query, start_time, end_time)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

        if not rows:
            return jsonify({"message": "No data to generate PDF."}), 400

        pdf = PDF()
        pdf.title = report_name
        pdf.from_date = start_time
        pdf.to_date = end_time

        pdf.add_page()

        header_font_size = 8
        data_font_size = 10

        # Limit to 5 columns and ensure the DateTime column gets enough space
        columns_to_print = columns[:5]
        col_widths = [min(pdf.get_string_width(col) + 20, (pdf.w - 20) / 5) for col in columns_to_print]  # Adjust for more space

        def print_header():
            pdf.set_xy(10, 30)  # Adjust positioning
            pdf.set_font('Arial', 'B', header_font_size)
            pdf.set_fill_color(200, 220, 255)

            for i, col_name in enumerate(columns_to_print):
                pdf.cell(col_widths[i], 8, col_name, border=1, fill=True, align='C')
            pdf.ln()

        def add_row_to_pdf(row):
            if pdf.get_y() + 10 > pdf.h - 30:
                pdf.add_page()
                print_header()

            pdf.set_font('Arial', '', data_font_size)
            # Only print data for the first 5 columns
            for i, item in enumerate(row[:5]):
                pdf.cell(col_widths[i], 10, str(item), border=1)
            pdf.ln()

        print_header()

        for row in rows:
            add_row_to_pdf(row)

        pdf_file = os.path.join(DOWNLOADS_DIR, 'report.pdf')
        pdf.output(pdf_file)

        conn.close()
        return send_file(pdf_file, as_attachment=True)

    except Exception as e:
        print(f"Error generating PDF: {e}")
        return jsonify({"message": f"Error generating PDF: {str(e)}"}), 500

@app.route('/generate_csv', methods=['POST'])
def generate_csv():
    try:
        table = request.form['table']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        interval = int(request.form['interval'])

        timestamp_column = get_timestamp_column(table)
        if not timestamp_column:
            return jsonify({"message": "No timestamp column found"}), 400

        start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M").strftime("%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(end_time, "%Y-%m-%dT%H:%M").strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db_connection()
        cursor = conn.cursor()
        query = f"""
            SELECT * FROM {table}
            WHERE {timestamp_column} BETWEEN ? AND ?
        """
        cursor.execute(query, start_time, end_time)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

        if not rows:
            return jsonify({"message": "No data to generate CSV."})

        csv_file = os.path.join(FILES_DIR, 'report.csv')
        with open(csv_file, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(columns)
            for row in rows:
                writer.writerow([str(item) for item in row])

        conn.close()
        return send_file(csv_file, as_attachment=True)

    except Exception as e:
        print(f"Error generating CSV: {e}")
        return jsonify({"message": f"Error generating CSV: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=443, debug=True) #added for local web server this word (host='0.0.0.0', port=443, )
