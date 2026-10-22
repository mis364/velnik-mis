const chatForm = document.getElementById('aiChatForm');
const chatMessagesElement = document.getElementById('aiChatMessages');
const chatQuestion = document.getElementById('aiChatQuestion');
const languageButtons = [...document.querySelectorAll('.language-button')];
let analysisLanguage = 'en';
let lastQuestion = '';
let lastAnswerElement = null;

function addChatMessage(role, content, isError = false) {
  const message = document.createElement('p');
  message.className = `ai-message ${role}${isError ? ' error' : ''}`;
  message.textContent = content;
  chatMessagesElement.append(message);
  chatMessagesElement.scrollTop = chatMessagesElement.scrollHeight;
  return message;
}

async function runAnalysis(question, addQuestion) {
  if (addQuestion) {
    addChatMessage('user', question);
    lastQuestion = question;
    chatQuestion.value = '';
  }
  const submit = document.getElementById('aiChatSubmit');
  submit.disabled = true;
  submit.textContent = 'Checking data…';
  languageButtons.forEach(button => { button.disabled = true; });
  const waiting = addQuestion || !lastAnswerElement
    ? addChatMessage('assistant', 'Checking the selected report data on this computer…')
    : lastAnswerElement;
  waiting.textContent = 'Checking the selected report data on this computer…';
  waiting.classList.remove('error');
  lastAnswerElement = waiting;
  const payload = {
    question,
    scope: document.getElementById('aiChatScope').value,
    language: analysisLanguage,
  };
  const from = document.getElementById('dateFrom')?.value;
  const to = document.getElementById('dateTo')?.value;
  if (from) payload.startDate = from;
  if (to) payload.endDate = to;

  try {
    const response = await fetch('/ai-chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.error || 'AI analysis failed.');
    waiting.textContent = result.answer;
    chatMessagesElement.scrollTop = chatMessagesElement.scrollHeight;
  } catch (error) {
    waiting.textContent = error.message || 'AI analysis failed. Please try again.';
    waiting.classList.add('error');
  } finally {
    submit.disabled = false;
    submit.textContent = 'Analyze';
    languageButtons.forEach(button => { button.disabled = false; });
    if (addQuestion) chatQuestion.focus();
  }
}

chatForm.addEventListener('submit', event => {
  event.preventDefault();
  const question = chatQuestion.value.trim();
  if (question) runAnalysis(question, true);
});

languageButtons.forEach(button => {
  button.addEventListener('click', () => {
    analysisLanguage = button.dataset.language;
    languageButtons.forEach(option => {
      const selected = option === button;
      option.classList.toggle('selected', selected);
      option.setAttribute('aria-pressed', String(selected));
    });
    if (lastQuestion) runAnalysis(lastQuestion, false);
  });
});

document.addEventListener('sales-mis-language-change', event => {
  analysisLanguage = event.detail.language;
  languageButtons.forEach(button => {
    const selected = button.dataset.language === analysisLanguage;
    button.classList.toggle('selected', selected);
    button.setAttribute('aria-pressed', String(selected));
  });
  if (lastQuestion) runAnalysis(lastQuestion, false);
});
