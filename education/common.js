/* === Trading Education Common JS === */

// Tab switching (works with both onclick="switchTab(n)" and data-tab patterns)
function switchTab(index) {
  document.querySelectorAll('.tab-content').forEach((el, i) => {
    el.classList.toggle('active', i === index);
  });
  document.querySelectorAll('.tab-btn').forEach((btn, i) => {
    btn.classList.toggle('active', i === index);
  });
}

// Alternative: data-tab based switching
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.tab-btn[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.getAttribute('data-tab');
      document.querySelectorAll('.tab-content').forEach(el => {
        el.classList.toggle('active', el.id === tabId);
      });
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });
});

// Quiz Engine
class QuizEngine {
  constructor(containerId, questions) {
    this.container = document.getElementById(containerId);
    this.questions = this.shuffle([...questions]);
    this.current = 0;
    this.score = 0;
    this.answered = false;
    if (this.container && this.questions.length > 0) {
      this.render();
    }
  }

  shuffle(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  render() {
    const q = this.questions[this.current];
    let html = `
      <div class="quiz-score">得分: ${this.score} / ${this.current} (共 ${this.questions.length} 題)</div>
      <div class="quiz-question">${this.current + 1}. ${q.question}</div>
      <ul class="quiz-options">
    `;
    q.options.forEach((opt, i) => {
      html += `<li onclick="window._quiz_${this.container.id}.select(${i})">${opt}</li>`;
    });
    html += `</ul>
      <div class="quiz-explanation" id="${this.container.id}-explanation">${q.explanation || ''}</div>
      <button onclick="window._quiz_${this.container.id}.next()" style="display:none;margin-top:12px;padding:8px 16px;background:var(--blue);color:#fff;border:none;border-radius:6px;cursor:pointer;" id="${this.container.id}-next">下一題 →</button>
    `;
    this.container.innerHTML = html;
    this.answered = false;
  }

  select(index) {
    if (this.answered) return;
    this.answered = true;
    const q = this.questions[this.current];
    const options = this.container.querySelectorAll('.quiz-options li');
    
    if (index === q.correct) {
      options[index].classList.add('correct');
      this.score++;
    } else {
      options[index].classList.add('wrong');
      options[q.correct].classList.add('correct');
    }
    
    const explanation = document.getElementById(`${this.container.id}-explanation`);
    if (explanation) explanation.classList.add('show');
    
    const nextBtn = document.getElementById(`${this.container.id}-next`);
    if (nextBtn) nextBtn.style.display = 'inline-block';
  }

  next() {
    this.current++;
    if (this.current >= this.questions.length) {
      this.container.innerHTML = `
        <div class="card" style="text-align:center;padding:30px;">
          <h3>測驗完成！</h3>
          <p style="font-size:24px;font-weight:800;color:var(--blue);margin:12px 0;">${this.score} / ${this.questions.length}</p>
          <p>正確率: ${Math.round(this.score / this.questions.length * 100)}%</p>
          <button onclick="window._quiz_${this.container.id} = new QuizEngine('${this.container.id}', window._quiz_data_${this.container.id})" style="margin-top:16px;padding:10px 20px;background:var(--blue);color:#fff;border:none;border-radius:8px;cursor:pointer;">重新測驗</button>
        </div>
      `;
    } else {
      this.render();
    }
  }
}

// Helper: init quiz with global reference for onclick
function initQuiz(containerId, questions) {
  window[`_quiz_data_${containerId}`] = questions;
  window[`_quiz_${containerId}`] = new QuizEngine(containerId, questions);
}

// Position Size Calculator
function calcPositionSize(account, riskPct, entry, stop) {
  const riskAmount = account * (riskPct / 100);
  const distance = Math.abs(entry - stop);
  if (distance === 0) return { size: 0, risk: 0, leverage: 0 };
  const size = riskAmount / distance;
  const notional = size * entry;
  const leverage = notional / account;
  return { size: size.toFixed(4), risk: riskAmount.toFixed(2), leverage: leverage.toFixed(2) };
}

// Kelly Criterion Calculator
function calcKelly(winRate, avgWin, avgLoss) {
  const b = avgWin / avgLoss;
  const p = winRate / 100;
  const q = 1 - p;
  const kelly = (b * p - q) / b;
  const halfKelly = kelly / 2;
  return { kelly: (kelly * 100).toFixed(2), halfKelly: (halfKelly * 100).toFixed(2) };
}

// Leverage Liquidation Calculator
function calcLiquidation(entry, leverage, direction) {
  // direction: 'long' or 'short'
  const liqDistance = 1 / leverage;
  if (direction === 'long') {
    return (entry * (1 - liqDistance)).toFixed(2);
  } else {
    return (entry * (1 + liqDistance)).toFixed(2);
  }
}
