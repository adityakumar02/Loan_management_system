import hashlib
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_pymongo import PyMongo
from flask_login import login_user, login_required, current_user

app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/loan_management"
mongo = PyMongo(app)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# User Registration & Login Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')

        # Validation
        if len(email) < 4 or '@' not in email:
            flash('Invalid email!', 'danger')
            return redirect(url_for('register'))
        if len(password) < 8:
            flash('Password must be at least 8 characters!', 'danger')
            return redirect(url_for('register'))
        if len(name) < 2:
            flash('Name must be at least 2 characters!', 'danger')
            return redirect(url_for('register'))

        # Check for duplicate user
        existing_user = mongo.db.users.find_one({"email": email})
        if existing_user:
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))

        # Hash password and save to DB
        hashed_password = hash_password(password)
        new_user = {"email": email, "password": hashed_password, "name": name, "is_admin": False}
        mongo.db.users.insert_one(new_user)
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = mongo.db.users.find_one({"email": email})
        if user and user['password'] == hash_password(password):
            login_user(User(user))
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed! Check your email and password.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

# Loan Application Route
@app.route('/apply_loan', methods=['POST'])
@login_required
def apply_loan():
    if request.method == 'POST':
        loan_amount = float(request.form.get('loan_amount'))
        tenure = int(request.form.get('tenure'))
        purpose = request.form.get('purpose')

        # Validate input
        if loan_amount < 50000 or loan_amount > 1000000:
            flash('Loan amount must be between 50,000 and 1,000,000!', 'danger')
            return redirect(url_for('apply_loan'))
        if tenure < 1 or tenure > 5:
            flash('Tenure must be between 1 and 5 years!', 'danger')
            return redirect(url_for('apply_loan'))
        if not purpose or len(purpose) > 200:
            flash('Purpose must be non-empty and less than 200 characters!', 'danger')
            return redirect(url_for('apply_loan'))

        # Check for duplicate application
        existing_loan = mongo.db.loans.find_one({"user_id": current_user.id, "purpose": purpose})
        if existing_loan:
            flash('Loan application already exists for this purpose!', 'danger')
            return redirect(url_for('apply_loan'))

        new_loan = {
            "user_id": current_user.id,
            "loan_amount": loan_amount,
            "tenure": tenure,
            "purpose": purpose,
            "status": "Pending"
        }
        mongo.db.loans.insert_one(new_loan)
        flash('Loan application submitted successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('apply_loan.html')

# Loan Status Route
@app.route('/loan_status', methods=['GET'])
@login_required
def loan_status():
    loans = mongo.db.loans.find({"user_id": current_user.id})
    return render_template('loan_status.html', loans=loans)

# Admin Dashboard Route
@app.route('/admin/dashboard', methods=['GET'])
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('dashboard'))

    loans = mongo.db.loans.find()
    return render_template('admin_dashboard.html', loans=loans)

# Approve/Reject Loan Route (Admin Only)
@app.route('/admin/loan/<string:loan_id>/status', methods=['POST'])
@login_required
def update_loan_status(loan_id):
    if not current_user.is_admin:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('dashboard'))

    loan = mongo.db.loans.find_one({"_id": loan_id})
    status = request.form.get('status')
    if status not in ['Approved', 'Rejected']:
        flash("Invalid status. Choose either Approved or Rejected.", "danger")
        return redirect(url_for('admin_dashboard'))

    mongo.db.loans.update_one({"_id": loan_id}, {"$set": {"status": status}})
    flash(f"Loan {loan_id} status updated to {status}.", "success")
    return redirect(url_for('admin_dashboard'))

if __name__ == "__main__":
    app.run(debug=True)
