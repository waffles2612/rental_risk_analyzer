#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
PY=$(command -v python3 || command -v python)
echo "Installing requirements..."
"$PY" -m pip install -r requirements.txt
echo "Training model..."
"$PY" -m rental_risk train
echo "Analysing sample agreements..."
"$PY" -m rental_risk analyze data/sample_agreements/leave_and_license_risky.pdf data/sample_agreements/residential_lease_balanced.docx data/sample_agreements/unnumbered_room_rental.txt data/sample_agreements/clause_list.txt
echo "Writing evaluation..."
"$PY" -m rental_risk evaluate
echo
echo "Done. Reports are in the reports folder. Opening the dashboard..."
(open Open_Dashboard.html 2>/dev/null || xdg-open Open_Dashboard.html 2>/dev/null) || echo "Open Open_Dashboard.html in your browser."
