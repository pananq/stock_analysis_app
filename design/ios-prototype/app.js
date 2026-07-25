const phone = document.querySelector('.phone');
const screens = [...document.querySelectorAll('.screen')];
const tabs = [...document.querySelectorAll('.tab')];
const toast = document.querySelector('.toast');
let toastTimer;

function showToast(message) {
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 1800);
}

function switchTab(name) {
  screens.forEach(screen => screen.classList.toggle('active', screen.dataset.screen === name));
  tabs.forEach(tab => tab.classList.toggle('active', tab.dataset.tab === name));
  const activeScroll = document.querySelector(`.screen[data-screen="${name}"] .scroll-area`);
  if (activeScroll) activeScroll.scrollTop = 0;
}

tabs.forEach(tab => tab.addEventListener('click', () => switchTab(tab.dataset.tab)));
document.querySelectorAll('[data-tab-jump]').forEach(button => {
  button.addEventListener('click', () => switchTab(button.dataset.tabJump));
});

function openSheet(selector) {
  document.querySelectorAll('.bottom-sheet').forEach(sheet => sheet.classList.remove('open'));
  document.querySelector(selector).classList.add('open');
  phone.classList.add('sheet-open');
}

function closeSheets() {
  document.querySelectorAll('.bottom-sheet').forEach(sheet => sheet.classList.remove('open'));
  phone.classList.remove('sheet-open');
}

document.querySelectorAll('[data-add-stock]').forEach(button => button.addEventListener('click', () => {
  openSheet('.add-sheet');
  setTimeout(() => document.querySelector('#stock-search').focus(), 340);
}));
document.querySelectorAll('[data-subscribe]').forEach(button => button.addEventListener('click', () => openSheet('.subscribe-sheet')));
document.querySelectorAll('[data-sheet-close]').forEach(button => button.addEventListener('click', closeSheets));

document.querySelectorAll('[data-toast]').forEach(button => {
  button.addEventListener('click', () => showToast(button.dataset.toast));
});

document.querySelectorAll('[data-add-name]').forEach(button => {
  button.addEventListener('click', () => {
    const icon = button.querySelector('i');
    icon.textContent = '✓';
    icon.style.background = '#0f7467';
    icon.style.color = 'white';
    setTimeout(() => {
      closeSheets();
      showToast(`${button.dataset.addName}已加入自选`);
    }, 240);
  });
});

document.querySelectorAll('.market-selector button, .filter-row .filter').forEach(button => {
  button.addEventListener('click', () => {
    [...button.parentElement.children].forEach(item => item.classList.remove('active'));
    button.classList.add('active');
  });
});

document.querySelector('[data-complete-subscribe]').addEventListener('click', () => {
  closeSheets();
  showToast('订阅确认将通过 App Store 完成');
});

document.querySelector('[data-open-detail]').addEventListener('click', () => {
  document.querySelector('.detail-overlay').classList.add('open');
});
document.querySelector('[data-close-detail]').addEventListener('click', () => {
  document.querySelector('.detail-overlay').classList.remove('open');
});

document.querySelectorAll('[data-stock]').forEach(row => {
  row.addEventListener('click', () => showToast(`${row.dataset.stock}详情将在下一版交付`));
});
