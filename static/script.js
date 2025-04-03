document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("review-form");
  const reviewInput = document.getElementById("review");
  const warningBox = document.getElementById("warning-box");

  // 🧠 Unfriendly words + suggested alternatives
  const flaggedWords = {
    "stupid": "not helpful",
    "idiot": "unprofessional",
    "useless": "not useful",
    "hate": "strongly dislike",
    "trash": "poor quality",
    "dumb": "confusing",
    "worst": "needs improvement",
    "pathetic": "disappointing",
    "annoying": "frustrating",
    "terrible": "unsatisfactory",
    "sucks": "could be better",
    "lazy": "unresponsive",
    "mean": "not supportive",
    "bad": "ineffective",
    "awful": "not ideal",
    "fuck": "inappropriate",
    "bitch": "inappropriate",
    "shit": "inappropriate"
  };

  const flaggedPhrases = [
    "waste of time",
    "should be fired",
    "doesn't know how to teach",
    "professor is a joke",
    "i hate this class"
  ];

  // 🔍 Live review content scanning
  if (reviewInput) {
    reviewInput.addEventListener("input", () => {
      const reviewText = reviewInput.value.toLowerCase();
      let message = "";
      let hasFlaggedWords = false;
  
      // Check for single words
      Object.keys(flaggedWords).forEach(word => {
        if (reviewText.includes(word)) {
          hasFlaggedWords = true;
          message += `⚠️ Consider replacing "<strong>${word}</strong>" with "<strong>${flaggedWords[word]}</strong>"<br>`;
        }
      });
  
      // Check for full phrases
      flaggedPhrases.forEach(phrase => {
        if (reviewText.includes(phrase)) {
          hasFlaggedWords = true;
          message += `⚠️ Please avoid the phrase "<strong>${phrase}</strong>"<br>`;
        }
      });
  
      // Show/hide warning + control submission
      const submitButton = form.querySelector("button[type='submit']");
      if (message) {
        warningBox.innerHTML = message;
        warningBox.style.display = "block";
        submitButton.disabled = true;
        submitButton.style.opacity = "0.6";
        submitButton.style.cursor = "not-allowed";
      } else {
        warningBox.style.display = "none";
        submitButton.disabled = false;
        submitButton.style.opacity = "1";
        submitButton.style.cursor = "pointer";
      }
    });
  }
  
     

  // ✅ Handle form submit
  if (form) {
    form.addEventListener("submit", async function (e) {
      e.preventDefault();

      const instructor = document.getElementById("professor").value.trim();
      const course = document.getElementById("course").value.trim();
      const rating = parseInt(document.getElementById("rating").value.trim());
      const review = reviewInput.value.trim();

      // ✅ Word Count Validation
    const wordCount = review.split(/\s+/).filter(word => word.length > 0).length;
      if (wordCount < 5) {
        alert("⚠️ Please write at least 5 words in your review.");
         return;
        }


      if (!instructor || !course || !rating || !review) {
        alert("Please fill in all required fields.");
        return;
      }

      const reviewData = { instructor, course, rating, review };

      try {
        const response = await fetch("http://127.0.0.1:5000/submit-review", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(reviewData),
        });

        const result = await response.json();

        if (response.ok) {
          alert(`✅ Review submitted!\nSentiment: ${result.sentiment}\nSummary: ${result.summary}`);
          form.reset();
          warningBox.style.display = "none";
        } else {
          alert("❌ Error: " + (result.error || "Something went wrong"));
        }
      } catch (error) {
        console.error("Error:", error);
        alert("❌ Server error. Please make sure the backend is running.");
      }
    });
  }

  // 💬 Chatbot toggle
  const chatbotToggle = document.getElementById("chatbot-toggle");
  const chatbotModal = document.getElementById("chatbot-modal");
  const closeChatbot = document.getElementById("close-chatbot");
  const chatInput = document.getElementById("chat-input");

  if (chatbotToggle && chatbotModal && closeChatbot) {
    chatbotToggle.addEventListener("click", () => {
      chatbotModal.style.display = "block";
    });

    closeChatbot.addEventListener("click", () => {
      chatbotModal.style.display = "none";
    });
  }

  // Chatbot interaction
  if (chatInput) {
    chatInput.addEventListener("keypress", async (e) => {
      if (e.key === "Enter") {
        const input = e.target.value.trim();
        if (!input) return;

        const log = document.getElementById("chat-log");
        log.innerHTML += `<p><strong>You:</strong> ${input}</p>`;
        e.target.value = "";

        const res = await fetch("http://127.0.0.1:5000/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: input })
        });

        const data = await res.json();
        log.innerHTML += `<p><strong>ZULens Bot:</strong> ${data.reply.replace(/\n/g, "<br>")}</p>`;
        log.scrollTop = log.scrollHeight;
      }
    });
  }
});
