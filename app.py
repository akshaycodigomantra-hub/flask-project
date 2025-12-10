import os
import datetime
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from dotenv import load_dotenv
import jwt

from db import db
from models import User, Module, Blog

load_dotenv()


def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "postgresql://akshay:akshay123@localhost:5432/flask_test_db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "mysecret123")

    db.init_app(app)
    return app


app = create_app()
JWT_EXP_HOURS = int(os.getenv("JWT_EXP_HOURS", 2))


# ---------------- JWT helpers ----------------
def generate_token(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXP_HOURS)
    }
    token = jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")
    # pyjwt might return bytes on some versions
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def _get_token_from_request():
    """
    Read token from (1) session cookie 'jwt' (existing flow) or
    (2) Authorization header "Bearer <token>" — useful for API testing.
    """
    # priority: session
    token = session.get("jwt")
    if token:
        return token

    # fallback: Authorization header
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.split(" ", 1)[1].strip()

    return None


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _get_token_from_request()

        if not token:
            # redirect to login for browser routes, JSON for API requests
            if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                return jsonify({"message": "Token missing"}), 401
            return redirect(url_for("login"))

        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            current_user = User.query.get(data.get("user_id"))
            if not current_user:
                raise Exception("User not found")
        except jwt.ExpiredSignatureError:
            # expired
            session.clear()
            return jsonify({"message": "Token expired"}), 401
        except Exception:
            session.clear()
            # redirect for browser, json for API
            if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
                return jsonify({"message": "Invalid token"}), 401
            return redirect(url_for("login"))

        return f(current_user, *args, **kwargs)

    return decorated


# ---------------- Routes (pages) ----------------

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/list")
@token_required
def list_page(current_user):
    return render_template("list.html")


# ---------------- Register / Login ----------------

@app.route("/register", methods=["GET", "POST"])
def register_page():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template("register.html", error="Email and password are required")

        if User.query.filter_by(email=email).first():
            return render_template("register.html", error="Email already exists")

        user = User(name=name, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            token = generate_token(user.id)
            session["jwt"] = token
            session["user_email"] = user.email
            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


@app.route("/dashboard")
@token_required
def dashboard(current_user):
    return render_template("dashboard.html", email=session.get("user_email"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- Module CRUD (ORM-backed) ----------------

@app.route("/modules", methods=["POST"])
@token_required
def add_module(current_user):
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    description = data.get("description", "").strip()

    if not title:
        return jsonify({"message": "Title is required"}), 400

    # Assign next sequence if not provided
    last_seq = db.session.query(db.func.max(Module.sequence)).scalar()
    next_seq = (last_seq or 0) + 1

    mod = Module(title=title, description=description, sequence=next_seq)
    db.session.add(mod)
    db.session.commit()

    return jsonify({"message": "Module added", "id": mod.id}), 201


@app.route("/modules", methods=["GET"])
@token_required
def get_modules(current_user):
    # Optional pagination params (page and limit)
    page = request.args.get("page", type=int)
    limit = request.args.get("limit", type=int)

    query = Module.query.order_by(Module.sequence.asc())

    if page and limit:
        pagination = query.paginate(page=page, per_page=limit, error_out=False)
        items = pagination.items
        payload = {
            "data": [{"id": m.id, "title": m.title, "description": m.description, "sequence": m.sequence}
                     for m in items],
            "current_page": pagination.page,
            "total_pages": pagination.pages,
            "total_items": pagination.total,
            "next_page": pagination.next_num if pagination.has_next else None,
            "prev_page": pagination.prev_num if pagination.has_prev else None
        }
        return jsonify(payload)
    else:
        modules = query.all()
        data = [{"id": m.id, "title": m.title, "description": m.description, "sequence": m.sequence}
                for m in modules]
        return jsonify({"data": data})


@app.route("/modules/<int:module_id>", methods=["PUT"])
@token_required
def update_module_route(current_user, module_id):
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    description = data.get("description", "").strip()

    if not title:
        return jsonify({"message": "Title is required"}), 400

    mod = Module.query.get(module_id)
    if not mod:
        return jsonify({"message": "Module not found"}), 404

    mod.title = title
    mod.description = description
    db.session.commit()

    return jsonify({"message": "Module updated"}), 200


@app.route("/modules/<int:module_id>", methods=["DELETE"])
@token_required
def delete_module_route(current_user, module_id):
    mod = Module.query.get(module_id)
    if not mod:
        return jsonify({"message": "Module not found"}), 404

    db.session.delete(mod)
    db.session.commit()
    return jsonify({"message": "Module deleted"}), 200


@app.route("/modules/<int:module_id>/move", methods=["POST"])
@token_required
def move_module(current_user, module_id):
    data = request.get_json() or {}
    direction = (data.get("direction") or "").lower()
    if direction not in ("up", "down"):
        return jsonify({"message": "direction must be 'up' or 'down'"}), 400

    mod = Module.query.get(module_id)
    if not mod:
        return jsonify({"message": "Module not found"}), 404

    if direction == "up":
        swap = Module.query.filter(Module.sequence < mod.sequence).order_by(Module.sequence.desc()).first()
    else:
        swap = Module.query.filter(Module.sequence > mod.sequence).order_by(Module.sequence.asc()).first()

    if not swap:
        return jsonify({"message": "Cannot move further"}), 400

    mod.sequence, swap.sequence = swap.sequence, mod.sequence
    db.session.commit()
    return jsonify({"message": "Module moved"}), 200


# ---------------- Blog CRUD (ORM-backed) ----------------

@app.route("/blogs", methods=["POST"])
@token_required
def add_blog(current_user):
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()

    if not title or not content:
        return jsonify({"message": "Title and content are required"}), 400

    blog = Blog(title=title, content=content, author=current_user.email)
    db.session.add(blog)
    db.session.commit()

    return jsonify({"message": "Blog created", "id": blog.id}), 201


@app.route("/blogs", methods=["GET"])
def list_blogs():
    # public API to list blogs
    blogs = Blog.query.order_by(Blog.id.desc()).all()
    data = [{"id": b.id, "title": b.title, "content": b.content, "author": b.author} for b in blogs]
    return jsonify({"data": data})


@app.route("/blogs/<int:blog_id>", methods=["GET"])
def get_blog(blog_id):
    b = Blog.query.get(blog_id)
    if not b:
        return jsonify({"message": "Not found"}), 404
    return jsonify({"id": b.id, "title": b.title, "content": b.content, "author": b.author})


@app.route("/blogs/<int:blog_id>", methods=["PUT"])
@token_required
def update_blog(current_user, blog_id):
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()

    if not title or not content:
        return jsonify({"message": "Title and content required"}), 400

    b = Blog.query.get(blog_id)
    if not b:
        return jsonify({"message": "Not found"}), 404

    # Optionally check owner: only author can update
    if b.author != current_user.email:
        return jsonify({"message": "Forbidden"}), 403

    b.title = title
    b.content = content
    db.session.commit()
    return jsonify({"message": "Blog updated"}), 200


@app.route("/blogs/<int:blog_id>", methods=["DELETE"])
@token_required
def delete_blog(current_user, blog_id):
    b = Blog.query.get(blog_id)
    if not b:
        return jsonify({"message": "Not found"}), 404

    # allow only author to delete
    if b.author != current_user.email:
        return jsonify({"message": "Forbidden"}), 403

    db.session.delete(b)
    db.session.commit()
    return jsonify({"message": "Blog deleted"}), 200


# ---------------- Init DB ----------------

@app.route("/init-db")
def init_db():
    db.create_all()
    return "Database Initialized!"


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
