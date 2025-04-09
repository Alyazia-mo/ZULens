document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("review-form");
  const reviewInput = document.getElementById("review");
  const warningBox = document.getElementById("warning-box");

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

  if (reviewInput) {
    reviewInput.addEventListener("input", () => {
      const reviewText = reviewInput.value.toLowerCase();
      let message = "";

      Object.keys(flaggedWords).forEach(word => {
        if (reviewText.includes(word)) {
          message += `⚠️ Consider replacing "<strong>${word}</strong>" with "<strong>${flaggedWords[word]}</strong>"<br>`;
        }
      });

      flaggedPhrases.forEach(phrase => {
        if (reviewText.includes(phrase)) {
          message += `⚠️ Please avoid the phrase "<strong>${phrase}</strong>"<br>`;
        }
      });

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

  if (form) {
    form.addEventListener("submit", async function (e) {
      e.preventDefault();

      const instructor = document.getElementById("professor").value.trim();
      const course = document.getElementById("course").value.trim();
      const rating = parseInt(document.getElementById("rating").value.trim());
      const review = reviewInput.value.trim();

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
        const response = await fetch("/submit-review", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(reviewData)
        });

// Handle login redirect
const result = await response.json();

if (response.status === 401) {
  // Not logged in – show login modal
  const modal = new bootstrap.Modal(document.getElementById("loginModal"));
  modal.show();
  return;
}

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

const logoutBtn = document.getElementById("logoutBtn");
if (logoutBtn) {
  logoutBtn.addEventListener("click", () => {
    fetch("/logout", {
      method: "POST"
    })
    .then(res => res.json())
    .then(data => {
      if (data.redirect) {
        window.location.href = "/";
      }
    });
  });
}




  // Chatbot toggle
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

  if (chatInput) {
    chatInput.addEventListener("keypress", async (e) => {
      if (e.key === "Enter") {
        const input = e.target.value.trim();
        if (!input) return;

        const log = document.getElementById("chat-log");
        log.innerHTML += `<p><strong>You:</strong> ${input}</p>`;
        e.target.value = "";

        const res = await fetch("/chat", {
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
