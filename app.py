from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
import sqlite3, os
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
from openai import OpenAI




client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DATABASE_PATH = "/data/reviews.db"


nltk.download("vader_lexicon")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "your_secret_key_here"
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

sia = SentimentIntensityAnalyzer()

@app.before_request
def redirect_to_www():
    host = request.host
    if host == "zulens.org":
        return redirect("https://www.zulens.org" + request.path, code=301)

# ---------- PAGE ROUTES ----------

@app.route('/')
def homepage():
    return render_template('homepage.html')

@app.route('/about-us')
def about():
    return render_template('about-us.html')

@app.route('/contact-us')
def contact():
    return render_template('contact-us.html')

@app.route('/reviews')
def reviews():
    return render_template('reviews.html')

@app.route('/submit-review-page')
def submit_review_page():
    return render_template('submit_review.html')

@app.route('/admin')
def admin_panel():
    return render_template('admin_panel.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/my-reviews')
def my_reviews_page():
    if "user_id" not in session:
        return redirect(url_for("login_page"))
    return render_template('my_reviews.html')


# Email configuration (update with your real info)
EMAIL_SENDER = "zulensorg@gmail.com"
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_PORT = 587

# ---------- USER AUTH ----------
def send_confirmation_email(to_email, username):
    subject = "Welcome to ZULens!"
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif;">
        <h2>🎉 Welcome to ZULens, {username}!</h2>
        <p>Thank you for signing up to ZULens – your voice matters.</p>
        <p>We’re excited to have you as part of the community!</p>
        <br>
        <p>Cheers,<br>ZULens Team</p>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email
    msg.attach(MIMEText(body, "html"))

    try:
        server = smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        print("Email sending failed:", e)


@app.route("/signup-user", methods=["POST"])
def signup_user():
    data = request.json
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"error": "Missing fields"}), 400

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        return jsonify({"error": "Email already registered"}), 409

    cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
    conn.commit()
    conn.close()

    # Send confirmation email
    send_confirmation_email(email, email.split("@")[0])
    
    return jsonify({"message": "Account created! Check your email to confirm."}), 200


@app.route("/login-user", methods=["POST"])
def login_user():
    data = request.json
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ? AND password = ?", (email, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        session["user_id"] = user[0]
        session["email"] = email
        return jsonify({"message": "Login successful"}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@app.route("/logout", methods=["POST"])
def logout_user():
    session.clear()
    return jsonify({"message": "Logged out", "redirect": "/"})

# ---------- TONE CHECK ENDPOINT ----------

@app.route("/check-tone", methods=["POST"])
def check_tone():
    review = request.json.get("review", "")
    sentiment_score = sia.polarity_scores(review)
    compound = sentiment_score["compound"]

    warning = None
    if compound <= -0.4:
        warning = "⚠️ Your review seems harsh. Consider rewording to sound more constructive."

    return jsonify({"warning": warning})

# ---------- REVIEWS ----------

@app.route('/submit-review', methods=['POST'])
def submit_review():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    course = data.get("course", "").replace(" ", "").replace("-", "").upper()
    raw_instructor = data.get("instructor", "").strip()
    instructor = "Prof. " + " ".join([part.capitalize() for part in raw_instructor.split()])
    review = data.get("review", "").strip()
    rating = int(data.get("rating", 3))

    if not course or not instructor or not review:
        return jsonify({"error": "Missing fields"}), 400

    prompt = f"""
    Analyze the following student review and return:
    1. The overall sentiment as Positive, Negative, or Neutral.
    2. A short summary of the review mentioning the course and instructor name.

    Course ID: {course}
    Instructor: {instructor}
    Rating: {rating} / 5
    Review: {review}

    Respond in this JSON format:
    {{"sentiment": "...", "summary": "..."}}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        content = response.choices[0].message.content.strip()
        sentiment_data = json.loads(content)
        sentiment = sentiment_data["sentiment"]
        summary = sentiment_data["summary"]
    except Exception as e:
        print("GPT error:", e)
        sentiment = "Neutral"
        summary = "Summary unavailable due to error."

    flagged = 1 if sentiment.lower() == "negative" and rating <= 2 else 0

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reviews (course, instructor, rating, review, sentiment, summary, flagged, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (course, instructor, rating, review, sentiment, summary, flagged, user_id))
    conn.commit()
    conn.close()

    return jsonify({
        "message": "Review submitted successfully",
        "sentiment": sentiment,
        "summary": summary,
        "flagged": bool(flagged)
    })

@app.route('/get-reviews', methods=['GET'])
def get_reviews():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, course, instructor, rating, review, sentiment, summary, flagged FROM reviews")
    rows = cursor.fetchall()
    conn.close()

    reviews = []
    for row in rows:
        reviews.append({
            "id": row[0],
            "course": row[1],
            "instructor": row[2],
            "rating": row[3],
            "review": row[4],
            "sentiment": row[5],
            "summary": row[6],
            "flagged": bool(row[7])
        })

    return jsonify(reviews), 200

@app.route('/get-my-reviews', methods=['GET'])
def get_my_reviews():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, course, instructor, rating, review, sentiment, summary, flagged 
        FROM reviews WHERE user_id = ?
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    reviews = [{
        "id": row[0],
        "course": row[1],
        "instructor": row[2],
        "rating": row[3],
        "review": row[4],
        "sentiment": row[5],
        "summary": row[6],
        "flagged": bool(row[7])
    } for row in rows]

    return jsonify(reviews)

@app.route("/delete-review-by-id", methods=["POST"])
def delete_review_by_id():
    user_id = session.get("user_id")
    review_id = request.json.get("review_id")

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reviews WHERE id = ? AND user_id = ?", (review_id, user_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Review deleted"}), 200

@app.route("/update-review", methods=["POST"])
def update_review():
    data = request.json
    review_id = data.get("review_id")
    new_text = data.get("new_text", "").strip()
    new_course = data.get("new_course", "").strip()
    new_instructor = data.get("new_instructor", "").strip()

    if not review_id or not new_text or not new_course or not new_instructor:
        return jsonify({"error": "Missing fields"}), 400

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT sentiment, summary, flagged FROM reviews WHERE id = ?", (review_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Review not found"}), 404

    existing_sentiment, existing_summary, existing_flagged = row

    cursor.execute("""
        UPDATE reviews 
        SET review = ?, course = ?, instructor = ?, sentiment = ?, summary = ?, flagged = ?
        WHERE id = ?
    """, (new_text, new_course, new_instructor, existing_sentiment, existing_summary, existing_flagged, review_id))

    conn.commit()
    conn.close()

    return jsonify({"message": "Review updated"}), 200

@app.route("/review-stats")
def review_stats():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM reviews")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM reviews WHERE sentiment = 'Positive'")
    positive = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM reviews WHERE sentiment = 'Negative'")
    negative = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM reviews WHERE sentiment = 'Neutral'")
    neutral = cursor.fetchone()[0]

    conn.close()
    return jsonify({
        "total": total,
        "positive": positive,
        "negative": negative,
        "neutral": neutral
    })


# ---------- CHATBOT ----------
@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").strip().lower()

    # Fetch reviews
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT course, instructor, rating, sentiment, review FROM reviews")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return jsonify({"reply": "Sorry, no reviews available yet."})

    
    review_data = [
        f"Course: {row[0]}, Instructor: {row[1]}, Rating: {row[2]}/5, Sentiment: {row[3]}, Review: {row[4]}"
        for row in rows
    ]
    joined_data = "\n".join(review_data)

    # Sending GPT a prompt of what is needed
    prompt = f"""
You are a helpful university course advisor for ZULens.

Student asked: "{user_message}"

You have access to the following reviews:
{joined_data}

Based on this data:
- Understand that course prefixes like "CHE" mean Chemistry, "MTH" is Math, "SEC" is Security, etc.
- Recommend or explain courses/instructors that match what the student asked (like "easy chemistry course", "strict professor", etc.).
- Reference real review info when possible.
- Respond conversationally, as if you’re helping a peer.

Return only a helpful reply — no JSON formatting.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        print("Chatbot error:", e)
        reply = "Something went wrong while trying to help. Please try again later."

    return jsonify({"reply": reply})

# ---------- INIT DB ----------

def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course TEXT,
            instructor TEXT,
            rating INTEGER,
            review TEXT,
            sentiment TEXT,
            summary TEXT,
            flagged INTEGER DEFAULT 0,
            user_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
