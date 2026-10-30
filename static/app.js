const status = document.querySelector("#status");
const list = document.querySelector("#names");

async function loadNames() {
  const response = await fetch("/api/students");
  if (!response.ok) {
    throw new Error("Request failed");
  }
  const students = await response.json();
  list.replaceChildren();
  if (students.length === 0) {
    status.textContent = "No students found.";
    return;
  }
  for (const student of students) {
    const item = document.createElement("li");
    item.textContent = student.name;
    list.append(item);
  }
  status.textContent = `${students.length} students`;
}

loadNames().catch(() => {
  status.textContent = "Could not load names.";
});
