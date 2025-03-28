function saveProfile() {
  const name = document.querySelector(".profile-name-input").value;
  if (!name) {
    alert("Please enter a profile name");
    return;
  }

  // Collect selected time slots
  const selectedCells = document.querySelectorAll(".time-grid-cell.selected");
  const timeSlots = Array.from(selectedCells).map((cell) => ({
    day: parseInt(cell.dataset.day),
    hour: parseInt(cell.dataset.hour),
    minute: parseInt(cell.dataset.minute),
  }));

  // Send to server
  fetch("/api/add_time_profile", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name: name,
      timeSlots: timeSlots,
    }),
  }).then((response) => {
    if (response.ok) {
      document.querySelector(".profile-name-input").value = "";
      document.querySelectorAll(".time-grid-cell.selected").forEach((cell) => {
        cell.classList.remove("selected");
      });
    }
  });
}

// Load components when the page loads
document.addEventListener("DOMContentLoaded", () => {
  fetch("/static/components/events-form.html")
    .then((response) => response.text())
    .then((html) => {
      document.getElementById("events-form").innerHTML = html;
    });

  fetch("/static/components/tasks-form.html")
    .then((response) => response.text())
    .then((html) => {
      document.getElementById("tasks-form").innerHTML = html;
    });
});
