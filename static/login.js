(() => {
  const tabs = [...document.querySelectorAll('[data-login-role]')];
  const panels = {
    owner: document.getElementById('bossLoginPanel'),
    manager: document.getElementById('managerLoginPanel'),
  };
  const stateGroup = document.getElementById('managerStateGroup');

  function selectRole(role) {
    for (const tab of tabs) {
      tab.setAttribute('aria-pressed', String(tab.dataset.loginRole === role));
    }
    for (const [panelRole, panel] of Object.entries(panels)) {
      if (panel) panel.hidden = panelRole !== role;
    }
  }

  for (const tab of tabs) {
    tab.addEventListener('click', () => selectRole(tab.dataset.loginRole));
  }
})();
