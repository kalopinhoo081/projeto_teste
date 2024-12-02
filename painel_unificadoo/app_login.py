from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configuração do MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://xupeta:bigbig83121790@projeto-mysql.cp8iawgsqg45.us-east-2.rds.amazonaws.com:3306/database_name'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelo de Usuário
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Senha armazenada como hash

# Modelo de Controle de Acesso
class AccessControl(db.Model):
    __tablename__ = 'accesscontrol'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    is_allowed = db.Column(db.Boolean, nullable=False, default=False)

@app.route('/')
def login():
    popup = session.pop('show_popup', None)
    return render_template('login.html', popup=popup)

@app.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')

    # Verifica se o e-mail existe no banco de dados
    user = User.query.filter_by(email=email).first()

    if not user:
        session['show_popup'] = {'type': 'danger', 'message': 'E-mail não cadastrado.'}
        return redirect(url_for('login'))

    if not check_password_hash(user.password, password):
        session['show_popup'] = {'type': 'danger', 'message': 'Senha incorreta. Tente novamente.'}
        return redirect(url_for('login'))

    # Verifica se o e-mail está liberado para acessar
    access = AccessControl.query.filter_by(email=email).first()
    if not access or not access.is_allowed:
        session['show_popup'] = {'type': 'danger', 'message': 'Acesso negado. Contate o administrador.'}
        return redirect(url_for('login'))

    # Login bem-sucedido
    session['user_id'] = user.id
    session['show_popup'] = {'type': 'success', 'message': 'Login bem-sucedido!'}
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        return redirect('http://127.0.0.1:5002')
    flash('Por favor, faça login primeiro.', 'warning')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session['show_popup'] = {'type': 'info', 'message': 'Logout realizado com sucesso.'}
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Verifica se o e-mail já está registrado
        if User.query.filter_by(email=email).first():
            session['show_popup'] = {'type': 'danger', 'message': 'E-mail já cadastrado.'}
            return redirect(url_for('register'))

        # Criptografa a senha antes de salvar no banco
        hashed_password = generate_password_hash(password)
        user = User(email=email, password=hashed_password)
        db.session.add(user)

        # Adiciona o e-mail à tabela de controle de acesso
        access = AccessControl(email=email, is_allowed=False)  # Não liberado por padrão
        db.session.add(access)

        db.session.commit()
        session['show_popup'] = {'type': 'success', 'message': 'Registro realizado com sucesso! Aguarde liberação do administrador.'}
        return redirect(url_for('register'))

    popup = session.pop('show_popup', None)
    return render_template('register.html', popup=popup)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
