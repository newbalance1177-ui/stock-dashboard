const LEVELS = [
  { id: 1, emoji: '🐣', title: 'ようちえん', desc: 'たんご・あいさつ・いろ・どうぶつ', needXp: 0, rate: 0.75 },
  { id: 2, emoji: '🎒', title: 'しょうがく1・2年', desc: 'かんたんな文・すきなもの', needXp: 100, rate: 0.85 },
  { id: 3, emoji: '📚', title: 'しょうがく3・4年', desc: '日常の話・きのうのこと', needXp: 250, rate: 0.9 },
  { id: 4, emoji: '🧑‍🎓', title: 'しょうがく5・6年', desc: '会話・意見・質問', needXp: 450, rate: 1.0 },
  { id: 5, emoji: '🗽', title: 'ちゅうがく', desc: '自然な会話・口語表現', needXp: 700, rate: 1.0 },
  { id: 6, emoji: '🚀', title: 'ネイティブ', desc: 'フリートーク', needXp: 1000, rate: 1.0 }
];

const el = (id) => document.getElementById(id);
const refs = {
  levelNum: el('levelNum'), xpFill: el('xpFill'), streakNum: el('streakNum'),
  avatar: el('avatar'), bubble: el('bubble'), subEn: el('subtitleEn'), subJa: el('subtitleJa'),
  tipBanner: el('tipBanner'), tipText: el('tipText'),
  feedback: el('feedbackCard'), fbHeard: el('fbHeard'), fbNatural: el('fbNatural'),
  fbWordRow: el('fbWordRow'), fbWord: el('fbWord'), fbPronRow: el('fbPronRow'), fbPron: el('fbPron'),
  fbPraise: el('fbPraise'), fbXp: el('fbXp'),
  playBtn: el('playBtn'), micBtn: el('micBtn'), skipBtn: el('skipBtn'), status: el('status'),
  levelMapBtn: el('levelMapBtn'), levelMap: el('levelMap'), levelList: el('levelList'), closeLevelMap: el('closeLevelMap'),
  setupWarning: el('setupWarning'), setupMsg: el('setupMsg'), closeSetup: el('closeSetup')
};

const state = load();
let history = [];
let lastBuddyLine = '';
let voice = null;
let recognizing = false;

function load() {
  try {
    return JSON.parse(localStorage.getItem('buddyEnglishState')) || { level: 1, xp: 0, streak: 0, lastPlayDate: null };
  } catch {
    return { level: 1, xp: 0, streak: 0, lastPlayDate: null };
  }
}
function save() { localStorage.setItem('buddyEnglishState', JSON.stringify(state)); }

function bumpStreak() {
  const today = new Date().toISOString().slice(0, 10);
  if (state.lastPlayDate === today) return;
  const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
  state.streak = state.lastPlayDate === yesterday ? state.streak + 1 : 1;
  state.lastPlayDate = today;
  save();
}

function levelInfo(id) { return LEVELS.find((l) => l.id === id) || LEVELS[0]; }

function renderStats() {
  refs.levelNum.textContent = state.level;
  refs.streakNum.textContent = state.streak;
  const cur = levelInfo(state.level);
  const next = levelInfo(Math.min(state.level + 1, 6));
  const span = Math.max(next.needXp - cur.needXp, 1);
  const pct = state.level >= 6 ? 100 : Math.min(100, ((state.xp - cur.needXp) / span) * 100);
  refs.xpFill.style.width = `${pct}%`;
}

function renderLevelMap() {
  refs.levelList.innerHTML = '';
  LEVELS.forEach((lv) => {
    const locked = state.xp < lv.needXp;
    const div = document.createElement('div');
    div.className = `level-item ${lv.id === state.level ? 'active' : ''} ${locked ? 'locked' : ''}`;
    div.innerHTML = `<h3>${lv.emoji} Lv.${lv.id} ${lv.title}</h3><p>${lv.desc}${locked ? ` ・ 必要XP ${lv.needXp}` : ''}</p>`;
    if (!locked) {
      div.addEventListener('click', () => {
        state.level = lv.id;
        save();
        renderStats();
        refs.levelMap.classList.add('hidden');
        history = [];
        askBuddy();
      });
    }
    refs.levelList.appendChild(div);
  });
}

function pickVoice() {
  const voices = speechSynthesis.getVoices();
  voice =
    voices.find((v) => v.lang === 'en-US' && /female|samantha|jenny|zira/i.test(v.name)) ||
    voices.find((v) => v.lang === 'en-US') ||
    voices.find((v) => v.lang?.startsWith('en')) ||
    null;
}
speechSynthesis.onvoiceschanged = pickVoice;
pickVoice();

function speak(text, rate) {
  return new Promise((resolve) => {
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    if (voice) u.voice = voice;
    u.lang = 'en-US';
    u.rate = rate;
    u.onstart = () => refs.avatar.classList.add('talking');
    u.onend = () => { refs.avatar.classList.remove('talking'); resolve(); };
    u.onerror = () => { refs.avatar.classList.remove('talking'); resolve(); };
    speechSynthesis.speak(u);
  });
}

async function api(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body)
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'request failed');
  return data;
}

function showSetupError(msg) {
  refs.setupMsg.textContent = msg.includes('ANTHROPIC_API_KEY')
    ? 'サーバーに ANTHROPIC_API_KEY が設定されていません。english-app/.env を作成し、Anthropic の API キーを設定してからサーバーを再起動してください。'
    : `エラーが発生しました: ${msg}`;
  refs.setupWarning.classList.remove('hidden');
}

async function askBuddy() {
  refs.feedback.classList.add('hidden');
  refs.tipBanner.classList.add('hidden');
  refs.status.textContent = 'Buddy が話しています…';
  try {
    const data = await api('/api/next-line', { level: state.level, history });
    lastBuddyLine = data.en;
    history.push({ role: 'buddy', text: data.en });
    refs.subEn.textContent = data.en;
    refs.subJa.textContent = data.ja || '';
    refs.bubble.classList.remove('hidden');
    if (data.tip) {
      refs.tipText.textContent = data.tip;
      refs.tipBanner.classList.remove('hidden');
    }
    await speak(data.en, levelInfo(state.level).rate);
    refs.status.textContent = 'マイクを押して答えてみよう';
  } catch (err) {
    showSetupError(err.message);
    refs.status.textContent = '';
  }
}

const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognizer = null;
if (SpeechRecognitionCtor) {
  recognizer = new SpeechRecognitionCtor();
  recognizer.lang = 'en-US';
  recognizer.maxAlternatives = 3;
  recognizer.interimResults = true;

  recognizer.onstart = () => {
    recognizing = true;
    refs.micBtn.classList.add('listening');
    refs.status.textContent = '聞いています…';
  };
  recognizer.onresult = (event) => {
    const result = event.results[event.results.length - 1];
    if (!result.isFinal) {
      refs.status.textContent = `聞いています… "${result[0].transcript}"`;
      return;
    }
    const transcript = result[0].transcript.trim();
    const alternatives = Array.from(result).map((r) => r.transcript.trim());
    recognizer.stop();
    handleUserSpeech(transcript, alternatives);
  };
  recognizer.onerror = (e) => {
    refs.status.textContent = e.error === 'no-speech' ? '聞き取れなかったよ。もう一度どうぞ' : `マイクエラー: ${e.error}`;
  };
  recognizer.onend = () => {
    recognizing = false;
    refs.micBtn.classList.remove('listening');
  };
} else {
  refs.status.textContent = '音声認識は Chrome / Edge でのみ利用できます';
  refs.micBtn.disabled = true;
}

async function handleUserSpeech(transcript, alternatives) {
  if (!transcript) {
    refs.status.textContent = '聞き取れなかったよ。もう一度どうぞ';
    return;
  }
  history.push({ role: 'learner', text: transcript });
  refs.status.textContent = 'フィードバックを考えています…';
  try {
    const fb = await api('/api/feedback', {
      level: state.level,
      buddyLine: lastBuddyLine,
      userTranscript: transcript,
      alternatives
    });
    showFeedback(fb);
    awardXp(fb.xp || 10);
    bumpStreak();
    renderStats();
  } catch (err) {
    showSetupError(err.message);
  }
  refs.status.textContent = '準備ができたらマイクを押すか、次へ進んでね';
}

function showFeedback(fb) {
  refs.fbHeard.textContent = fb.heard || '';
  refs.fbNatural.textContent = fb.natural || '';
  if (fb.wordTip) {
    refs.fbWord.textContent = fb.wordTip;
    refs.fbWordRow.classList.remove('hidden');
  } else {
    refs.fbWordRow.classList.add('hidden');
  }
  if (fb.pronunciationTip) {
    refs.fbPron.textContent = fb.pronunciationTip;
    refs.fbPronRow.classList.remove('hidden');
  } else {
    refs.fbPronRow.classList.add('hidden');
  }
  refs.fbPraise.textContent = fb.praise || '';
  refs.fbXp.textContent = `+${fb.xp || 0} XP`;
  refs.feedback.classList.remove('hidden');
}

function awardXp(amount) {
  state.xp += amount;
  const next = levelInfo(Math.min(state.level + 1, 6));
  if (state.level < 6 && state.xp >= next.needXp) {
    state.level = next.id;
  }
  save();
}

refs.micBtn.addEventListener('click', () => {
  if (!recognizer) return;
  if (recognizing) {
    recognizer.stop();
  } else {
    speechSynthesis.cancel();
    recognizer.start();
  }
});

refs.playBtn.addEventListener('click', () => {
  if (lastBuddyLine) speak(lastBuddyLine, levelInfo(state.level).rate);
});

refs.skipBtn.addEventListener('click', () => askBuddy());

refs.levelMapBtn.addEventListener('click', () => {
  renderLevelMap();
  refs.levelMap.classList.remove('hidden');
});
refs.closeLevelMap.addEventListener('click', () => refs.levelMap.classList.add('hidden'));
refs.closeSetup.addEventListener('click', () => refs.setupWarning.classList.add('hidden'));

renderStats();
askBuddy();
