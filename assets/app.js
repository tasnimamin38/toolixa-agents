"use strict";

const catalogUrl = "/catalog/agents.json";
const grid = document.getElementById("agent-grid");
const statusNode = document.getElementById("catalog-status");
const countNode = document.getElementById("directory-count");
const searchInput = document.getElementById("agent-search");
const filtersNode = document.getElementById("category-filters");
const emptyNode = document.getElementById("empty-state");
const clearButton = document.getElementById("clear-filters");

let allAgents = [];
let activeCategory = "all";

document.getElementById("current-year").textContent = String(new Date().getFullYear());

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function createAgentCard(agent, index, repository) {
  const card = element("article", "agent-card");
  const top = element("div", "card-top");
  top.append(element("span", "card-index", String(index + 1).padStart(2, "0") + " / " + String(agent.category || "agent").toUpperCase()));
  top.append(element("span", "status-pill", agent.status || "experimental"));
  card.append(top);
  card.append(element("h3", "", agent.name));
  card.append(element("p", "", agent.description));

  const capabilities = element("div", "capability-list");
  (Array.isArray(agent.capabilities) ? agent.capabilities : []).slice(0, 3).forEach((capability) => {
    capabilities.append(element("span", "capability", String(capability).replaceAll("_", " ")));
  });
  card.append(capabilities);

  const links = element("div", "card-links");
  const source = element("a", "", "Source code ↗");
  source.href = repository + "/tree/main/" + agent.path;
  source.target = "_blank";
  source.rel = "noopener noreferrer";
  links.append(source);
  const docs = element("a", "", "Documentation ↗");
  docs.href = repository + "/blob/main/" + agent.path + "/" + agent.documentation;
  docs.target = "_blank";
  docs.rel = "noopener noreferrer";
  links.append(docs);
  card.append(links);
  return card;
}

function renderFilters(agents) {
  const categories = [...new Set(agents.map((agent) => agent.category).filter(Boolean))].sort();
  filtersNode.replaceChildren();
  const allButton = element("button", "filter-button is-active", "All agents");
  allButton.type = "button";
  allButton.dataset.category = "all";
  allButton.setAttribute("aria-pressed", "true");
  filtersNode.append(allButton);

  categories.forEach((category) => {
    const button = element("button", "filter-button", category.replaceAll("-", " "));
    button.type = "button";
    button.dataset.category = category;
    button.setAttribute("aria-pressed", "false");
    filtersNode.append(button);
  });
}

function renderAgents() {
  const query = searchInput.value.trim().toLocaleLowerCase();
  const filtered = allAgents.filter((agent) => {
    const categoryMatch = activeCategory === "all" || agent.category === activeCategory;
    const searchable = [
      agent.name,
      agent.description,
      agent.category,
      ...(Array.isArray(agent.capabilities) ? agent.capabilities : []),
    ].join(" ").toLocaleLowerCase();
    return categoryMatch && searchable.includes(query);
  });
  grid.replaceChildren();
  const repository = "https://github.com/tasnimamin38/toolixa-agents";
  filtered.forEach((agent) => grid.append(createAgentCard(agent, allAgents.indexOf(agent), repository)));
  emptyNode.hidden = filtered.length !== 0;
  countNode.textContent = filtered.length + " / " + allAgents.length + " AGENTS";
  statusNode.textContent = allAgents.length + " agent manifests loaded. Select an agent to inspect its source and requirements.";
}

filtersNode.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-category]");
  if (!button) return;
  activeCategory = button.dataset.category;
  filtersNode.querySelectorAll("button").forEach((item) => {
    const selected = item === button;
    item.classList.toggle("is-active", selected);
    item.setAttribute("aria-pressed", String(selected));
  });
  renderAgents();
});

searchInput.addEventListener("input", renderAgents);
clearButton.addEventListener("click", () => {
  searchInput.value = "";
  activeCategory = "all";
  const allButton = filtersNode.querySelector('[data-category="all"]');
  if (allButton) allButton.click();
  searchInput.focus();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "/" && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
    event.preventDefault();
    searchInput.focus();
  }
});

fetch(catalogUrl, { headers: { Accept: "application/json" }, cache: "no-cache" })
  .then((response) => {
    if (!response.ok) throw new Error("Catalog request failed with HTTP " + response.status);
    return response.json();
  })
  .then((catalog) => {
    if (!catalog || catalog.schema_version !== 1 || !Array.isArray(catalog.agents)) {
      throw new Error("Catalog format is invalid");
    }
    allAgents = catalog.agents.filter((agent) =>
      agent && typeof agent.id === "string" &&
      typeof agent.name === "string" &&
      typeof agent.description === "string" &&
      typeof agent.path === "string" &&
      typeof agent.documentation === "string"
    );
    if (allAgents.length === 0) throw new Error("No valid agent entries were found");
    renderFilters(allAgents);
    renderAgents();
  })
  .catch((error) => {
    countNode.textContent = "CATALOG UNAVAILABLE";
    statusNode.textContent = "The agent catalog could not be loaded. Check the repository catalog/agents.json file.";
    const message = element("p", "catalog-error", error.message);
    grid.replaceChildren(message);
  });
