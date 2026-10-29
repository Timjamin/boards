from datetime import datetime, timezone

from flask import Flask, abort, redirect, render_template, request, url_for

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024 # 5 MB

posts = []
next_post_id = 1
MAX_POSTS = 20
MAX_USERNAME_LENGTH = 30
MAX_TITLE_LENGTH = 100
MAX_TEXT_LENGTH = 1000

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
    return render_template("index.html", posts=posts)


@app.route("/post", methods=["POST"])
def post():
    global next_post_id

    username = request.form.get("username", "").strip() or "anon"
    title = request.form.get("title", "").strip()
    text = request.form.get("text", "").strip()
    image = request.files.get("image")

    if len(username) > MAX_USERNAME_LENGTH:
        return render_template(
            "index.html",
            posts=posts,
            error=f"Name must be {MAX_USERNAME_LENGTH} characters or fewer.",
        )
    if not title:
        return render_template("index.html", posts=posts, error="every novel needs a title")
    if len(title) > MAX_TITLE_LENGTH:
        return render_template(
            "index.html",
            posts=posts,
            error=f"Title must be {MAX_TITLE_LENGTH} characters or fewer.",
        )
    if not text:
        return render_template("index.html", posts=posts, error="you didnt even type anything")
    if len(text) > MAX_TEXT_LENGTH:
        return render_template(
            "index.html",
            posts=posts,
            error=f"nuh uh, too much yap, try {MAX_TEXT_LENGTH} characters or fewer.",
        )
    if not image or not image.filename:
        return render_template("index.html", posts=posts, error="you didnt even upload an image.")

    data = image.read()
    content_type = image_type(data)
    if not content_type:
        return render_template(
            "index.html",
            posts=posts,
            error="nope, this image SUCKS, we only accept PNG, JPEG, GIF, WebP, JXL, or AVIF images here. (5mb max)",
        )

    posts.insert(0, {
        "id": next_post_id,
        "username": username,
        "title": title,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "text": text,
        "image": data,
        "type": content_type,
    })
    next_post_id += 1
    del posts[MAX_POSTS:]
    return redirect(url_for("home"))


@app.route("/image/<int:post_id>")
def show_image(post_id):
    for item in posts:
        if item["id"] == post_id:
            return app.response_class(item["image"], mimetype=item["type"])
    abort(404)


if __name__ == "__main__":
    app.run()
