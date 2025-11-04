# MediConnect - Stylish Pro
Run instructions:
1. Create venv and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install flask werkzeug
   ```
2. Run the app:
   ```bash
   python app.py
   ```
3. Open http://127.0.0.1:5000
Seeded accounts:
- Admin: admin@example.com / password123
- Doctor: doctor@example.com / password123
- Patient: patient@example.com / password123
Notes:
- This is a demo. Replace `app.secret_key` before production.
- Uploaded files are served directly from /uploads (for demo only).
