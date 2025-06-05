from flask import Flask, request, render_template, redirect, url_for, flash
from googleapiclient.errors import HttpError
import pandas as pd
import traceback
from google.oauth2 import service_account
from googleapiclient.discovery import build
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SERVICE_ACCOUNT_FILE = json.loads(os.environ.get('GOOGLE_CREDENTIALS'))  # path to your JSON key



def get_google_sheet(sheet_id, range_name):
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=sheet_id, range=range_name).execute()
        values = result.get('values', [])
        if not values:
            raise ValueError("No data found in the Google Sheet")
        headers = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=headers)
        return df
    except HttpError as e:
        print("HttpError details:", e.content.decode())
        raise
    except Exception as e:
        print(traceback.format_exc())
        raise
app = Flask(__name__)
app.secret_key = "supersecretkey"

students = []  # flattened list of all clerkship entries per student

def parse_google_form_spreadsheet(df):
    students_expanded = []
    rounds = 9  # number of rounds

    for _, row in df.iterrows():
        name = str(row.get('Name', '')).strip()
        phone = str(row.get('(optional) Phone Number', '')).strip()
        email = str(row.get('Email Address', '')).strip()
        selective_specialty = str(row.get('Selective Specialty', '')).strip()
        selective_location = str(row.get('Selective Location', '')).strip()

        default_trade_status = 'open'  # adjust as needed

        for i in range(1, rounds + 1):
            spec_col = f'Round {i} Specialty'
            loc_col = f'Round {i} Location'
            specialty = str(row.get(spec_col, '')).strip()
            location = str(row.get(loc_col, '')).strip()
            if specialty and location:
                students_expanded.append({
                    'name': name,
                    'phone': phone or email,
                    'email': email,
                    'specialty': specialty,
                    'block': f'Round {i}',
                    'location': location,
                    'trade_status': default_trade_status
                })

        # Add selective round
        if selective_specialty and selective_location:
            students_expanded.append({
                'name': name,
                'phone': phone or email,
                'email': email,
                'specialty': selective_specialty,
                'block': 'Selective',
                'location': selective_location,
                'trade_status': default_trade_status
            })

    return students_expanded

@app.route("/", methods=["GET"])
def load_sheet():
    try:
        SHEET_ID = '1VwjJy0_9NdFHPIPLd9GA6mr0OUiMq_IxaRFyEQD7C1Q'
        RANGE_NAME = ('Unformatted')  # or the exact range, e.g. 'A1:Z1000'
        df = get_google_sheet(SHEET_ID, RANGE_NAME)

        global students
        students = parse_google_form_spreadsheet(df)

        return redirect(url_for('find_matches'))


    except Exception as e:
        error_details = traceback.format_exc()
        return f"<h2>Error loading Google Sheet:</h2><pre>{error_details}</pre>"

# @app.route("/", methods=["GET", "POST"])
# def upload_file():
#     if request.method == "POST":
#         file = request.files.get("file")
#         if not file:
#             flash("No file uploaded!", "error")
#             return redirect(request.url)
#         try:
#             df = pd.read_excel(file)
#             # You can add column checks here if you want
#
#             global students
#             students = parse_google_form_spreadsheet(df)
#
#             flash(f"Uploaded {len(students)} rotation records!", "success")
#             return redirect(url_for("find_matches"))
#         except Exception as e:
#             flash(f"Error reading file: {e}", "error")
#             return redirect(request.url)
#
#     return render_template("upload.html")

@app.route("/find_matches", methods=["GET", "POST"])
def find_matches():
    matches = []
    message = ""
    blocks = sorted(set(s['block'] for s in students))  # to show dropdown of blocks

    if request.method == "POST":
        your_name = request.form.get("name", "").strip()
        your_block = request.form.get("block", "")

        your_entries = [s for s in students if s["name"].lower() == your_name.lower() and s["block"] == your_block]
        if not your_entries:
            message = f"No rotation found for {your_name} in {your_block}."
        else:
            specialty = your_entries[0]["specialty"]
            matches = [
                s for s in students
                if s["block"] == your_block and s["specialty"] == specialty and s["name"].lower() != your_name.lower()
            ]

    return render_template("find_matches.html", matches=matches, message=message, blocks=blocks)

if __name__ == "__main__":
    app.run(debug=True)
