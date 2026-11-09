"use strict";

const filterDialog = document.querySelector("#filter-dialog");
const filterForm = filterDialog.querySelector("form");
const filterDates = document.querySelector("#filter-dates");

function toggleFilterDates() {
  const custom = filterForm.elements.period.value === "custom";
  filterDates.hidden = !custom;
  filterDates.disabled = !custom;
}

document.querySelector("#open-filter").addEventListener("click", () => filterDialog.showModal());
document.querySelector("#cancel-filter").addEventListener("click", () => filterDialog.close());
filterForm.addEventListener("change", toggleFilterDates);
filterDialog.addEventListener("close", () => {
  filterForm.reset();
  toggleFilterDates();
});

if (filterDialog.hasAttribute("data-reopen")) {
  filterDialog.showModal();
}
