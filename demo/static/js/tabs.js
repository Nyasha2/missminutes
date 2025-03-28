function switchTab(tabId) {
  // Hide all tabs
  document.querySelectorAll(".tab-content").forEach((tab) => {
    tab.classList.remove("active");
  });
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.remove("active");
  });

  // Show selected tab
  document.getElementById(tabId).classList.add("active");
  document
    .querySelector(`.tab[onclick="switchTab('${tabId}')"]`)
    .classList.add("active");
}
