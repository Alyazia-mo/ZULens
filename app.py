from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
import sqlite3, os
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification, pipeline

nltk.download("vader_lexicon")

# Initialize app
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "your_secret_key_here"  # CHANGE THIS TO A SECURE RANDOM VALUE
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

sia = SentimentIntensityAnalyzer()

# ---------- AI Model Initialization ----------

def load_model():
    model = DistilBertForSequenceClassification.from_pretrained("distilbert-base-uncased")
    tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-uncased")
    model = model.half()  # Convert model to FP16 to save memory
    model.eval()  # Set the model to evaluation mode
    return model, tokenizer

try:
    classifier = pipeline("text-classification", model="distilbert-base-uncased")
except Exception as e:
    print("Error loading model:", e)
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

# ---------- USER AUTH ----------

@app.route("/signup-user", methods=["POST"])
def signup_user():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Missing fields"}), 400

    conn = sqlite3.connect("reviews.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        return jsonify({"error": "Username already exists"}), 409

    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    conn.commit()
    conn.close()

    return jsonify({"message": "Account created successfully"}), 200

@app.route("/login-user", methods=["POST"])
def login_user():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    conn = sqlite3.connect("reviews.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        session["user_id"] = user[0]
        session["username"] = username
        return jsonify({"message": "Login successful"}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@app.route("/logout", methods=["POST"])
def logout_user():
    session.clear()
    return jsonify({"message": "Logged out", "redirect": "/"})


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

    # AI moderation to check for inappropriate content using the fine-tuned model
    result = classifier(review)
    if result[0]['label'] == 'LABEL_1':  # Assuming 'LABEL_1' corresponds to toxic content
        return jsonify({"error": "Review contains inappropriate content"}), 400

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
    
    conn = sqlite3.connect("reviews.db")
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO reviews (course, instructor, rating, review, sentiment, summary, flagged, user_id) 
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (course, instructor, rating, review, sentiment, summary, 0, user_id))
    conn.commit()
    conn.close()

    return jsonify({
        "message": "Review submitted successfully",
        "sentiment": sentiment,
        "summary": summary
    })

# ---------- INIT DB ----------

def init_db():
    conn = sqlite3.connect("reviews.db")
    cursor = conn.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL
                    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS reviews (
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
                    )""")

    conn.commit()
    conn.close()

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
