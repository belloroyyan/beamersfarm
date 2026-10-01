document.addEventListener("DOMContentLoaded", () => {
  const role = document.querySelector("[data-staff-role]");
  const usernameField = document.querySelector("[data-salesperson-username]");
  const username = usernameField?.querySelector("input");
  if (!role || !usernameField || !username) return;
  const refresh = () => {
    const isSalesperson = role.value === "salesperson";
    usernameField.hidden = !isSalesperson;
    username.required = isSalesperson;
  };
  role.addEventListener("change", refresh);
  refresh();
});
