from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

nltk.download("vader_lexicon")

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)


sia = SentimentIntensityAnalyzer()


from flask import render_template

@app.route("/")
def homepage_redirect():
    return render_template("homepage.html")

@app.route("/about-us")
def about_us():
    return render_template("about-us.html")

@app.route("/reviews")
def reviews():
    return render_template("reviews.html")

@app.route("/submit_review")
def submit_review_page():
    return render_template("submit_review.html")

@app.route("/contact-us")
def contact_us():
    return render_template("contact-us.html")


# Initialize database if not exists
def init_db():
    conn = sqlite3.connect("reviews.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course TEXT,
            instructor TEXT,
            rating INTEGER,
            review TEXT,
            sentiment TEXT,
            summary TEXT,
            flagged INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Route to submit review
@app.route('/submit-review', methods=['POST'])
def submit_review():
    data = request.json
    course = data.get("course", "").strip()
    instructor = data.get("instructor", "").strip()
    review = data.get("review", "").strip()
    rating = int(data.get("rating", 3))

    if not course or not instructor or not review:
        return jsonify({"error": "Missing fields"}), 400

    # Sentiment
    sentiment_score = sia.polarity_scores(review)
    compound = sentiment_score["compound"]
    sentiment = "Neutral"
    if compound >= 0.05:
        sentiment = "Positive"
    elif compound <= -0.05:
        sentiment = "Negative"

        # Sentiment Analysis
    sentiment_score = sia.polarity_scores(review)
    compound = sentiment_score["compound"]
    # Smart adjustment using rating
    if rating >= 4 and compound < 0.05:
        sentiment = "Positive"
    elif rating <= 2 and compound > -0.05:
        sentiment = "Negative"
    elif compound >= 0.05:
        sentiment = "Positive"
    elif compound <= -0.05:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"


    summary = f"This course ({course}) taught by {instructor} has mostly {sentiment.lower()} feedback based on this review."

    # Flag logic (adjust words as needed)
    bad_words = ["stupid", "hate", "trash", "idiot", "useless", "worst","shit", "fuck", "suck", "bitch"]
    flagged = any(word in review.lower() for word in bad_words)

    conn = sqlite3.connect("reviews.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reviews (course, instructor, rating, review, sentiment, summary, flagged)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (course, instructor, rating, review, sentiment, summary, int(flagged)))
    conn.commit()
    conn.close()

    return jsonify({
        "message": "Review submitted successfully",
        "sentiment": sentiment,
        "summary": summary,
        "flagged": flagged
    })

# Route to get reviews
@app.route('/get-reviews', methods=['GET'])
def get_reviews():
    conn = sqlite3.connect("reviews.db")
    cursor = conn.cursor()
    cursor.execute("SELECT course, instructor, rating, review, sentiment, summary, flagged FROM reviews")
    rows = cursor.fetchall()
    conn.close()

    reviews = []
    for row in rows:
        reviews.append({
            "course": row[0],
            "instructor": row[1],
            "rating": row[2],
            "review": row[3],
            "sentiment": row[4],
            "summary": row[5],
            "flagged": bool(row[6])
        })

    return jsonify(reviews), 200

# Chatbot (uses keywords in reviews)
@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "").lower()
    keywords = {
        "project": ["project", "project-based", "no exam", "final project"],
        "exam": ["exam", "midterm", "test", "quiz", "exam-heavy"],
        "flexible": ["flexible", "easy deadline", "no attendance", "lenient"],
        "strict": ["strict", "tough", "hard grader", "heavy rules", "mandatory attendance"],
        "group": ["group", "group work", "team project", "collaborative"],
        "helpful": ["helpful", "supportive", "answers questions", "kind", "responsive"]
    }

    conn = sqlite3.connect("reviews.db")
    cursor = conn.cursor()

    matched = False
    response = ""

    for category, terms in keywords.items():
        for term in terms:
            if term in user_message:
                matched = True
                cursor.execute("""
                    SELECT course, instructor, rating 
                    FROM reviews 
                    WHERE review LIKE ? AND sentiment = 'Positive'
                    ORDER BY rating DESC LIMIT 3
                """, (f"%{term}%",))
                results = cursor.fetchall()

                if results:
                    response += f"<b>{category.title()}-related suggestions:</b>\n"
                    for course, instructor, rating in results:
                        response += f"• {course} (Instructor: {instructor}, Rating: {rating}/5)\n"
                break

    if not matched or response == "":
        response = "Try asking me about project-based, exam-focused, flexible, or strict courses! 😊"

    conn.close()
    return jsonify({"reply": response})

@app.route("/delete-review-by-index", methods=["POST", "OPTIONS"])
def delete_review_by_index():
    if request.method == "OPTIONS":
        return '', 200

    index = request.json.get("index")
    if index is None:
        return jsonify({"error": "Missing index"}), 400

    conn = sqlite3.connect("reviews.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM reviews")
    ids = cursor.fetchall()

    if index < 0 or index >= len(ids):
        return jsonify({"error": "Index out of range"}), 404

    review_id = ids[index][0]
    cursor.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Review deleted"}), 200

from flask import Flask, render_template

app = Flask(__name__)


import os
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

