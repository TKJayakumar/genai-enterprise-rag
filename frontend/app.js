const messagesEl = document.getElementById("messages");
const traceEl = document.getElementById("trace");
const form = document.getElementById("queryForm");
const input = document.getElementById("queryInput");
const userSelect = document.getElementById("userSelect");
const modePill = document.getElementById("modePill");
const auditBody = document.querySelector("#auditTable tbody");
const refreshAuditBtn = document.getElementById("refreshAudit");

const uploadForm = document.getElementById("uploadForm");
const uploadFile = document.getElementById("uploadFile");
const uploadDept = document.getElementById("uploadDept");
const uploadRoles = document.getElementById("uploadRoles");
const uploadStatus = document.getElementById("uploadStatus");
const docsBody = document.querySelector("#docsTable tbody");

async function loadConfig() {
  const res = await fetch("/api/config");
  const cfg = await res.json();
  modePill.textContent = cfg.mode;
}

async function loadUsers() {
  const res = await fetch("/api/users");
  const users = await res.json();
  userSelect.innerHTML = users
    .map((u) => `<option value="${u.id}">${u.name} — ${u.role}</option>`)
    .join("");
}

function addMessage(role, html, extraClass = "") {
  const div = document.createElement("div");
  div.className = `msg ${role} ${extraClass}`.trim();
  div.innerHTML = html;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderTraceStep(step) {
  if (traceEl.querySelector(".trace-empty")) traceEl.innerHTML = "";
  const li = document.createElement("li");
  li.className = `trace-node ${step.node_type}`;
  const time = step.timestamp.split("T")[1]?.replace("Z", "") || "";
  let extraHtml = "";
  if (step.extra) {
    const text =
      typeof step.extra === "string" ? step.extra : JSON.stringify(step.extra, null, 0);
    extraHtml = `<div class="extra">${text}</div>`;
  }
  li.innerHTML = `
    <div class="row1">
      <span class="label">${step.label}</span>
      <span class="ts">${time}</span>
    </div>
    <div class="detail">${step.detail}</div>
    ${extraHtml}
  `;
  traceEl.appendChild(li);
  traceEl.scrollTop = traceEl.scrollHeight;
}

async function loadAuditLog() {
  const res = await fetch("/api/audit-log");
  const rows = await res.json();
  auditBody.innerHTML = rows
    .map(
      (r) => `
      <tr>
        <td>${r.timestamp.replace("T", " ").replace("Z", "")}</td>
        <td>${r.user_id}</td>
        <td>${r.role}</td>
        <td>${r.query}</td>
        <td class="status-${r.status}">${r.status}</td>
        <td>${r.num_citations}</td>
      </tr>`
    )
    .join("");
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = input.value.trim();
  if (!query) return;

  addMessage("user", query);
  input.value = "";
  traceEl.innerHTML = "";
  const button = form.querySelector("button");
  button.disabled = true;

  try {
    const res = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userSelect.value, query }),
    });
    const data = await res.json();

    data.trace.forEach(renderTraceStep);

    const citationsHtml = data.citations.length
      ? `<div class="citations">${data.citations
          .map((c) => `<span>[${c.n}] ${c.title}</span>`)
          .join("")}</div>`
      : "";

    let extraClass = "";
    if (data.status === "escalated") extraClass = "escalated";
    else if (data.status === "not_found") extraClass = "not-found";

    addMessage(
      "assistant",
      `${data.answer.replace(/\n/g, "<br/>")}${citationsHtml}`,
      extraClass
    );

    loadAuditLog();
  } catch (err) {
    addMessage("assistant", "Something went wrong reaching the backend. Is uvicorn running?");
    console.error(err);
  } finally {
    button.disabled = false;
  }
});

refreshAuditBtn.addEventListener("click", loadAuditLog);

async function loadDeptRoles() {
  const res = await fetch("/api/departments-roles");
  const { departments, roles } = await res.json();

  uploadDept.innerHTML = departments
    .map((d) => `<option value="${d}">${d}</option>`)
    .join("");

  uploadRoles.innerHTML = roles
    .map(
      (r) => `<label><input type="checkbox" name="role" value="${r}" ${
        r === "all-staff" ? "checked" : ""
      }/> ${r}</label>`
    )
    .join("");
}

async function loadDocuments() {
  const res = await fetch("/api/documents");
  const docs = await res.json();
  docsBody.innerHTML = docs
    .map(
      (d) => `
      <tr>
        <td>${d.title}</td>
        <td>${d.department}</td>
        <td class="chip">${d.access_roles.join(", ")}</td>
        <td>${d.chunks}</td>
        <td class="chip">${d.storage_backend}</td>
        <td>${(d.uploaded_at || "").replace("T", " ").replace("Z", "")}</td>
        <td><button class="delete-upload" data-id="${d.upload_id}">Remove</button></td>
      </tr>`
    )
    .join("");

  docsBody.querySelectorAll(".delete-upload").forEach((btn) => {
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      await fetch(`/api/documents/${btn.dataset.id}`, { method: "DELETE" });
      loadDocuments();
    });
  });
}

uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = uploadFile.files[0];
  if (!file) return;

  const selectedRoles = Array.from(
    uploadRoles.querySelectorAll('input[name="role"]:checked')
  ).map((cb) => cb.value);

  if (!selectedRoles.length) {
    uploadStatus.textContent = "Select at least one role that should be able to see this document.";
    uploadStatus.className = "upload-status error";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("department", uploadDept.value);
  formData.append("access_roles", selectedRoles.join(","));

  const button = uploadForm.querySelector("button");
  button.disabled = true;
  uploadStatus.textContent = "Uploading and indexing…";
  uploadStatus.className = "upload-status";

  try {
    const res = await fetch("/api/documents/upload", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok) {
      uploadStatus.textContent = data.detail || "Upload failed.";
      uploadStatus.className = "upload-status error";
      return;
    }

    uploadStatus.textContent = `Indexed "${data.title}" as ${data.chunks_indexed} chunk(s), visible to: ${data.access_roles.join(", ")}.`;
    uploadStatus.className = "upload-status ok";
    uploadForm.reset();
    loadDeptRoles();
    loadDocuments();
  } catch (err) {
    uploadStatus.textContent = "Something went wrong reaching the backend.";
    uploadStatus.className = "upload-status error";
    console.error(err);
  } finally {
    button.disabled = false;
  }
});

loadConfig();
loadUsers();
loadAuditLog();
loadDeptRoles();
loadDocuments();
