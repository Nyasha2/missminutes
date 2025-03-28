// Add predefined colors for profiles
const profileColors = [
  "#7aa2f7", // Default blue
  "#bb9af7", // Purple
  "#2ac3de", // Cyan
  "#ff9e64", // Orange
  "#9ece6a", // Green
  "#f7768e", // Red
  "#e0af68", // Yellow
  "#449dab", // Teal
];

let profiles = [
  {
    id: "default",
    name: "Default Profile",
    color: profileColors[0],
    timeSlots: [],
  },
];

let currentColorIndex = 1; // Start after default color

function makeEditable(element) {
  const originalText = element.textContent;
  element.classList.add("editing");
  element.contentEditable = true;
  element.focus();

  // Save on enter
  element.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();
      element.blur();
    }
  });

  // Save on blur
  element.addEventListener(
    "blur",
    function () {
      const newText = element.textContent.trim();
      if (newText && newText !== originalText) {
        const profileId = element.closest(".profile-item").dataset.profileId;
        updateProfileName(profileId, newText);
      } else {
        element.textContent = originalText;
      }
      element.contentEditable = false;
      element.classList.remove("editing");
    },
    { once: true }
  );
}

function addNewProfile() {
  const id = "profile-" + Date.now();
  const color = profileColors[currentColorIndex % profileColors.length];
  currentColorIndex++;

  const newProfile = {
    id: id,
    name: "New Profile",
    color: color,
    timeSlots: [],
  };

  profiles.push(newProfile);

  const profileList = document.querySelector(".profile-list");
  const profileElement = createProfileElement(newProfile);
  profileList.appendChild(profileElement);

  // Trigger rename immediately
  const nameElement = profileElement.querySelector(".profile-name");
  makeEditable(nameElement);
}

function createProfileElement(profile) {
  const div = document.createElement("div");
  div.className = "profile-item";
  div.dataset.profileId = profile.id;
  div.dataset.color = profile.color;
  div.innerHTML = `
    <div class="profile-color-indicator" style="color: ${profile.color}"></div>
    <span class="profile-name" ondblclick="makeEditable(this)">${profile.name}</span>
    <button class="delete-profile" onclick="deleteProfile(this)" title="Delete Profile">
      <span class="delete-icon">×</span>
    </button>
  `;

  div.addEventListener("click", () => selectProfile(profile.id));
  return div;
}

function selectProfile(profileId) {
  // Remove active class from all profiles
  document.querySelectorAll(".profile-item").forEach((item) => {
    item.classList.remove("active");
  });

  // Add active class to selected profile
  const selectedItem = document.querySelector(
    `[data-profile-id="${profileId}"]`
  );
  selectedItem.classList.add("active");

  // Load the profile's time slots
  const profile = profiles.find((p) => p.id === profileId);
  loadTimeSlots(profile.timeSlots);

  // Update grid selection color
  document.documentElement.style.setProperty(
    "--current-profile-color",
    profile.color
  );
}

function deleteProfile(button) {
  const profileItem = button.closest(".profile-item");
  const profileId = profileItem.dataset.profileId;

  if (profileId === "default") {
    alert("Cannot delete the default profile");
    return;
  }

  // Animate deletion
  profileItem.style.transform = "translateX(-100%)";
  profileItem.style.opacity = "0";

  setTimeout(() => {
    profiles = profiles.filter((p) => p.id !== profileId);
    profileItem.remove();

    // Select default profile if deleted profile was active
    if (profileItem.classList.contains("active")) {
      selectProfile("default");
    }
  }, 300);
}

function updateProfileName(profileId, newName) {
  const profile = profiles.find((p) => p.id === profileId);
  if (profile) {
    profile.name = newName;
    // Here you would typically save to the backend
    saveProfiles();
  }
}

function saveProfiles() {
  // Send to server
  fetch("/api/save_profiles", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(profiles),
  });
}

// Initialize profiles on page load
document.addEventListener("DOMContentLoaded", () => {
  // Fetch existing profiles from server
  fetch("/api/get_profiles")
    .then((response) => response.json())
    .then((data) => {
      profiles = data;
      const profileList = document.querySelector(".profile-list");
      profiles.forEach((profile) => {
        profileList.appendChild(createProfileElement(profile));
      });
      selectProfile("default");
    });
});

// Update the time grid cell selection to use profile colors
function updateGridCell(cell, selected) {
  const activeProfile = profiles.find((p) =>
    document.querySelector(`[data-profile-id="${p.id}"].active`)
  );

  if (selected) {
    cell.classList.add("selected");
    cell.dataset.profileColor = activeProfile.color;
    cell.style.setProperty("--profile-color", activeProfile.color);
  } else {
    cell.classList.remove("selected");
    cell.removeAttribute("data-profile-color");
    cell.style.removeProperty("--profile-color");
  }
}
