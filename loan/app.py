import hashlib
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, login_required, current_user

app = Flask(__name__)



db = SQLAlchemy(app)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    name = db.Column(db.String(150), nullable=False)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Loan Model
class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    loan_amount = db.Column(db.Float, nullable=False)
    tenure = db.Column(db.Integer, nullable=False)
    purpose = db.Column(db.String(200), nullable=False)


# Initialize Database
with app.app_context():
    db.create_all()

# Homepage route
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')

        # Validate input
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
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))

        # Hash password and save to DB
        hashed_password = hash_password(password)
        new_user = User(email=email, password=hashed_password, name=name)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and user.password == hash_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed! Check your email and password.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

# Loan Application Route (for Users)
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
            existing_loan = Loan.query.filter_by(user_id=current_user.id, purpose=purpose).first()
            if existing_loan:
                flash('Loan application already exists for this purpose!', 'danger')
                return redirect(url_for('apply_loan'))

            new_loan = Loan(user_id=current_user.id, loan_amount=loan_amount, tenure=tenure, purpose=purpose)
            db.session.add(new_loan)
            db.session.commit()
            flash('Loan application submitted successfully!', 'success')
            return redirect(url_for('dashboard'))

        return render_template('apply_loan.html')

# Check Loan Status (for Users)
@app.route('/loan_status', methods=['GET'])
@login_required
def loan_status():
    loans = Loan.query.filter_by(user_id=current_user.id).all()
    return render_template('loan_status.html', loans=loans)


# Admin Panel (View All Loans)
@app.route('/admin/dashboard', methods=['GET'])
@login_required
def admin_dashboard():
    # Check if user is admin
    if not current_user.is_admin:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('dashboard'))

    loans = Loan.query.all()
    return render_template('admin_dashboard.html', loans=loans)

# Approve/Reject Loan (Admin Only)
@app.route('/admin/loan/<int:loan_id>/status', methods=['POST'])
def update_loan_status(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    status = request.form['status']

    if status not in ['Approved', 'Rejected']:
        flash("Invalid status. Choose either Approved or Rejected.", "danger")
        return redirect(url_for('admin_dashboard'))

    loan.status = status
    db.session.commit()

    flash(f"Loan {loan_id} status updated to {status}.", "success")
    return redirect(url_for('admin_dashboard'))

if __name__ == "__main__":
    app.run(debug=True)
