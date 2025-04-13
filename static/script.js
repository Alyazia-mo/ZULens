document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("review-form");
  const reviewInput = document.getElementById("review");
  const warningBox = document.getElementById("warning-box");

  if (reviewInput) {
    reviewInput.addEventListener("input", async () => {
      const reviewText = reviewInput.value.trim();

      // Check review with the backend AI moderation
      const response = await fetch("/submit-review", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          course: document.getElementById("course").value.trim(),
          instructor: document.getElementById("professor").value.trim(),
          rating: document.getElementById("rating").value.trim(),
          review: reviewText
        })
      });

      const data = await response.json();

      if (response.status === 400 && data.error) {
        warningBox.innerHTML = `⚠️ ${data.error}`;
        warningBox.style.display = "block";
        document.querySelector("button[type='submit']").disabled = true;
      } else {
        warningBox.style.display = "none";
        document.querySelector("button[type='submit']").disabled = false;
      }
    });
  }

  // Review form submission handler
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
        window.location.href = data.redirect || "/";
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
