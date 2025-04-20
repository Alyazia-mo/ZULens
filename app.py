from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
import sqlite3, os
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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
    course = data.get("course", "").strip()
    instructor = data.get("instructor", "").strip()
    review = data.get("review", "").strip()
    rating = int(data.get("rating", 3))

    if not course or not instructor or not review:
        return jsonify({"error": "Missing fields"}), 400

    sentiment_score = sia.polarity_scores(review)
    compound = sentiment_score["compound"]
    sentiment = "Neutral"

    if rating >= 4 and compound < 0.05:
        sentiment = "Positive"
    elif rating <= 2 and compound > -0.05:
        sentiment = "Negative"
    elif compound >= 0.05:
        sentiment = "Positive"
    elif compound <= -0.05:
        sentiment = "Negative"

    summary = f"This course ({course}) taught by {instructor} has mostly {sentiment.lower()} feedback based on this review."
    flagged = compound <= -0.5

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reviews (course, instructor, rating, review, sentiment, summary, flagged, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (course, instructor, rating, review, sentiment, summary, int(flagged), user_id))
    conn.commit()
    conn.close()

    return jsonify({
        "message": "Review submitted successfully",
        "sentiment": sentiment,
        "summary": summary,
        "flagged": flagged
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

# ---------- CHATBOT ----------

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").lower()
    keywords = {
        "project": ["project", "project-based", "no exam", "final project"],
        "exam": ["exam", "midterm", "test", "quiz", "exam-heavy"],
        "flexible": ["flexible", "easy deadline", "no attendance", "lenient"],
        "strict": ["strict", "tough", "hard grader", "mandatory attendance"],
        "group": ["group", "group work", "team project", "collaborative"],
        "helpful": ["helpful", "supportive", "kind", "responsive"]
    }

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    matched = False
    response = ""

    for category, terms in keywords.items():
        for term in terms:
            if term in user_message:
                matched = True
                cursor.execute("""
                    SELECT course, instructor, rating FROM reviews
                    WHERE review LIKE ? AND sentiment = 'Positive'
                    ORDER BY rating DESC LIMIT 3
                """, (f"%{term}%",))
                results = cursor.fetchall()
                if results:
                    response += f"<b>{category.title()}-related suggestions:</b>\n"
                    for course, instructor, rating in results:
                        response += f"• {course} (Instructor: {instructor}, Rating: {rating}/5)\n"
                break

    conn.close()
    if not matched or response == "":
        response = "Try asking about project-based, exam-heavy, or flexible courses! 😊"

    return jsonify({"reply": response})

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
