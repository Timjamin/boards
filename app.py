from datetime import datetime, timezone

from flask import Flask, abort, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024 # 5 MB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

posts = []
MAX_POSTS = 20
MAX_USERNAME_LENGTH = 30
MAX_TITLE_LENGTH = 100
MAX_TEXT_LENGTH = 1000

db = SQLAlchemy(app)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(MAX_USERNAME_LENGTH), default="anon")
    title = db.Column(db.String(MAX_TITLE_LENGTH), nullable=True)
    text = db.Column(db.String(MAX_TEXT_LENGTH), nullable=False)
    image = db.Column(db.LargeBinary, nullable=False)
    type = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc))

with app.app_context():
    db.create_all()

def image_type(data): # I'm gonna be entirely honest, this function is vibecoded because I had no clue how to actually meaningfully restrict filetypes to actually images to prevent uploading binary blobs or just any broken file, and I just needed a quick solution.
                      # Theoretically arbitrary files could still be uploaded if the files start with the first few bytes this function looks for, but this is a prototype and not anything serious. There is probably a library for this problem.
                      # That filetype allow list is all me though I love modern web image formats and jxl is finally supported in major browsers
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"\xff\x0c\x00\x00"):
        return "image/jxl"
    if data.startswith(b"ftypavif") or data.startswith(b"ftypavis"):
        return "image/avif"
    return None


@app.route("/")
def home():
    return render_template("index.html", posts = Post.query.order_by(Post.id.desc()).all())


@app.route("/post", methods=["POST"])
def post():
    username = request.form.get("username", "").strip() or "anon"
    title = request.form.get("title", "").strip()
    text = request.form.get("text", "").strip()
    image = request.files.get("image")

    if len(username) > MAX_USERNAME_LENGTH:
        return render_template(
            "index.html",
            posts=Post.query.order_by(Post.id.desc()).all(),
            error=f"Name must be {MAX_USERNAME_LENGTH} characters or fewer.",
        )
    if not title:
        return render_template("index.html", posts=Post.query.order_by(Post.id.desc()).all(), error="every novel needs a title")
    if len(title) > MAX_TITLE_LENGTH:
        return render_template(
            "index.html",
            posts=Post.query.order_by(Post.id.desc()).all(),
            error=f"Title must be {MAX_TITLE_LENGTH} characters or fewer.",
        )
    if not text:
        return render_template("index.html", posts=Post.query.order_by(Post.id.desc()).all(), error="you didnt even type anything")
    if len(text) > MAX_TEXT_LENGTH:
        return render_template(
            "index.html",
            posts=Post.query.order_by(Post.id.desc()).all(),
            error=f"nuh uh, too much yap, try {MAX_TEXT_LENGTH} characters or fewer.",
        )
    if not image or not image.filename:
        return render_template("index.html", posts=Post.query.order_by(Post.id.desc()).all(), error="you didnt even upload an image. this isnt called a text board, y'know.")

    data = image.read()
    content_type = image_type(data)
    if not content_type:
        return render_template(
            "index.html",
            posts=Post.query.order_by(Post.id.desc()).all(),
            error="nope, this image SUCKS, we only accept PNG, JPEG, GIF, WebP, JXL, or AVIF images here. (5mb max)",
        )

    
    post = Post(
        username=username,
        title=title,
        text=text,
        image=data,
        type=content_type,
    )
    db.session.add(post)
    db.session.commit()

    # cull old posts once limit is reached
    while Post.query.count() > MAX_POSTS:
        oldest_post = Post.query.order_by(Post.id).first()
        db.session.delete(oldest_post)
    db.session.commit()
    return redirect(url_for("home"))


@app.route("/image/<int:post_id>")
def show_image(post_id):
    post = db.session.get(Post, post_id)
    if post is None:
        abort(404)
    return app.response_class(post.image, mimetype=post.type)

@app.route("/admin")
def admin():
    return render_template("admin.html", posts=Post.query.all())

@app.route("/delete/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    db.session.delete(db.session.get(Post, post_id))
    db.session.commit()
    return render_template("admin.html", posts=Post.query.all())

if __name__ == "__main__":
    app.run()
