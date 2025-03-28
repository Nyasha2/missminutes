let isMouseDown = false;

// Keep track of profiles per cell
const cellProfiles = new Map(); // key: "day-hour-minute", value: Set of profile colors

function getCurrentProfileColor() {
  const activeProfile = document.querySelector(".profile-item.active");
  return activeProfile ? activeProfile.dataset.color : "#7aa2f7";
}

function updateCellProfiles(cell, color, isAdding) {
  const cellKey = `${cell.dataset.day}-${cell.dataset.hour}-${cell.dataset.minute}`;
  let profiles = cellProfiles.get(cellKey) || new Set();

  if (isAdding) {
    profiles.add(color);
  } else {
    profiles.delete(color);
  }

  if (profiles.size === 0) {
    cellProfiles.delete(cellKey);
    cell.removeAttribute("data-profiles");
    deselectCell(cell);
  } else {
    cellProfiles.set(cellKey, profiles);
    updateCellVisual(cell, profiles);
  }
}

function updateCellVisual(cell, profiles) {
  const profileColors = Array.from(profiles);

  // Set CSS variables for the colors
  profileColors.forEach((color, index) => {
    cell.style.setProperty(`--profile-color-${index + 1}`, color);
  });

  // Store profiles data attribute for styling hooks
  cell.setAttribute("data-profiles", profileColors.join(","));

  // Add hover tooltip showing profile names
  const profileNames = profileColors
    .map((color) => getProfileNameByColor(color))
    .join(", ");

  cell.title = `Profiles: ${profileNames}`;
}

function getProfileNameByColor(color) {
  const profile = document.querySelector(
    `.profile-item[data-color="${color}"]`
  );
  return profile
    ? profile.querySelector(".profile-name").textContent
    : "Unknown";
}

function selectCell(cell) {
  const color = getCurrentProfileColor();
  cell.classList.add("selected");
  cell.dataset.profileColor = color;
  cell.style.setProperty("--profile-color", color);
}

function deselectCell(cell) {
  cell.classList.remove("selected");
  cell.removeAttribute("data-profile-color");
  cell.style.removeProperty("--profile-color");
}

function handleCellMouseDown(e) {
  isDragging = true;
  const cell = e.target;
  const currentColor = getCurrentProfileColor();

  // If cell belongs to current profile, deselect it
  // If cell is empty or belongs to another profile, select it for current profile
  isSelecting = cell.dataset.profileColor !== currentColor;

  if (isSelecting) {
    selectCell(cell);
  } else {
    deselectCell(cell);
  }
}

function handleCellMouseEnter(e) {
  if (!isDragging) return;

  const cell = e.target;
  if (isSelecting) {
    selectCell(cell);
  } else {
    deselectCell(cell);
  }
}

function handleCellMouseUp() {
  isDragging = false;
}

function createTimeGrid() {
  const grid = document.querySelector(".time-grid");
  const days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
  const hours = [];

  // Create hours array (00:00 to 23:30)
  for (let hour = 0; hour < 24; hour++) {
    for (let minute = 0; minute < 60; minute += 30) {
      hours.push({
        hour: hour,
        minute: minute,
        label: `${hour.toString().padStart(2, "0")}:${minute
          .toString()
          .padStart(2, "0")}`,
      });
    }
  }

  // Add empty corner cell
  const cornerCell = document.createElement("div");
  cornerCell.style.backgroundColor = "#1f2335";
  grid.appendChild(cornerCell);

  // Add day headers
  days.forEach((day, index) => {
    const header = document.createElement("div");
    header.className = "day-header";
    header.textContent = day;
    grid.appendChild(header);
  });

  // Add time rows
  hours.forEach((time, rowIndex) => {
    // Add time label
    const timeLabel = document.createElement("div");
    timeLabel.className = "time-label";
    timeLabel.textContent = time.label;
    grid.appendChild(timeLabel);

    // Add cells for each day
    days.forEach((day, dayIndex) => {
      const cell = document.createElement("div");
      cell.className = "time-grid-cell";
      cell.dataset.day = dayIndex;
      cell.dataset.hour = time.hour;
      cell.dataset.minute = time.minute;

      cell.addEventListener("mousedown", (e) => {
        isMouseDown = true;
        handleCellMouseDown(e);
      });

      cell.addEventListener("mouseover", (e) => {
        handleCellMouseEnter(e);
      });

      cell.addEventListener("mouseup", () => {
        handleCellMouseUp();
      });

      grid.appendChild(cell);
    });
  });

  // Add mouseup listener to document to handle mouse release outside grid
  document.addEventListener("mouseup", () => {
    isMouseDown = false;
  });
}

// Initialize grid when DOM is loaded
document.addEventListener("DOMContentLoaded", createTimeGrid);

// Add hover effect to show profile details
function addCellHoverEffect(cell) {
  const cellKey = `${cell.dataset.day}-${cell.dataset.hour}-${cell.dataset.minute}`;
  const profiles = cellProfiles.get(cellKey);

  if (!profiles || profiles.size <= 1) return;

  // Create or update tooltip with profile information
  let tooltip = cell.querySelector(".cell-tooltip");
  if (!tooltip) {
    tooltip = document.createElement("div");
    tooltip.className = "cell-tooltip";
    cell.appendChild(tooltip);
  }

  const profileInfo = Array.from(profiles)
    .map((color) => {
      const name = getProfileNameByColor(color);
      return `<span style="color: ${color}">${name}</span>`;
    })
    .join("<br>");

  tooltip.innerHTML = profileInfo;
}
