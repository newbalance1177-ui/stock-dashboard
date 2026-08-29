import 'dotenv/config';
import express from 'express';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = process.env.PORT || 3000;
const MODEL = 'claude-sonnet-5';

const LEVEL_GUIDE = {
  1: 'American kindergarten level. Use single words or 2-4 word phrases only. Vocabulary: colors, animals, numbers 1-10, greetings, family words, simple objects. Present tense only ("It is a dog."). No contractions needed, no complex grammar.',
  2: 'American grade 1-2 level. Short simple sentences (4-7 words), present tense, likes/dislikes, daily objects, simple questions ("Do you like pizza?").',
  3: 'American grade 3-4 level. Everyday topics (school, food, weather, hobbies), simple past tense allowed, sentences up to ~10 words.',
  4: 'American grade 5-6 level. Short conversations about daily life, opinions ("I think..."), past and future tense, sentences up to ~14 words.',
  5: 'American middle-school / casual native level. Natural everyday spoken English, contractions, idioms kept simple, sentences up to ~18 words.',
  6: 'Natural fluent native conversation. Casual idioms, varied tenses, normal conversational pace and length.'
};

async function callClaude(system, userText, maxTokens = 400) {
  if (!process.env.ANTHROPIC_API_KEY) {
    throw new Error('ANTHROPIC_API_KEY is not set on the server (.env)');
  }
  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-api-key': process.env.ANTHROPIC_API_KEY,
      'anthropic-version': '2023-06-01'
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: maxTokens,
      thinking: { type: 'disabled' },
      system,
      messages: [{ role: 'user', content: userText }]
    })
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Claude API error ${res.status}: ${errText}`);
  }
  const data = await res.json();
  const textBlock = data.content?.find((block) => block.type === 'text');
  return textBlock?.text ?? '';
}

function extractJson(text) {
  const match = text.match(/\{[\s\S]*\}/);
  if (!match) throw new Error('No JSON found in model response');
  return JSON.parse(match[0]);
}

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

app.get('/healthz', (_req, res) => res.status(200).send('ok'));

app.post('/api/next-line', async (req, res) => {
  try {
    const { level = 1, history = [] } = req.body;
    const guide = LEVEL_GUIDE[level] || LEVEL_GUIDE[1];
    const transcript = history
      .slice(-8)
      .map((h) => `${h.role === 'buddy' ? 'Buddy' : 'Learner'}: ${h.text}`)
      .join('\n');

    const system = `You are "Buddy", an upbeat, playful American English conversation partner in a language-learning game for a Japanese learner. Speak ONLY English at this difficulty level: ${guide}
Stay warm and encouraging like a game character. React briefly to what the learner just said before moving the conversation forward (ask a simple question or introduce a new short idea) so the chat keeps flowing naturally.
Reply with ONLY valid JSON, no markdown fences, in this exact shape:
{"en": "Buddy's line in English", "ja": "Japanese translation of that line", "tip": "one very short reusable phrase or word for the learner, or empty string"}`;

    const userText = transcript
      ? `Conversation so far:\n${transcript}\n\nContinue as Buddy with your next short line.`
      : `Start a new conversation as Buddy. Greet the learner and ask something easy to answer at this level.`;

    const raw = await callClaude(system, userText, 300);
    const json = extractJson(raw);
    res.json(json);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/feedback', async (req, res) => {
  try {
    const { level = 1, buddyLine = '', userTranscript = '', alternatives = [] } = req.body;
    const guide = LEVEL_GUIDE[level] || LEVEL_GUIDE[1];

    const altNote = alternatives.length > 1
      ? `The speech recognizer wasn't fully sure and also considered these alternatives: ${alternatives.join(' | ')}. Low confidence on a word often means it was said unclearly — consider that when giving pronunciation tips.`
      : '';

    const system = `You are a warm, encouraging American English speaking coach for a Japanese learner in a game-like app. The learner is at this level: ${guide}
The learner just tried to respond (out loud, in English) to Buddy's line: "${buddyLine}"
Speech recognition heard: "${userTranscript}"
${altNote}
Give feedback matched to their level — do not correct a beginner into complex native grammar, just nudge them one small step forward.
Reply with ONLY valid JSON, no markdown fences, in this exact shape:
{"heard": "clean repeat of what they said", "natural": "how a friendly native speaker would actually say the same idea at or slightly above this level", "wordTip": "one short word-choice or grammar note, or empty string if nothing needed", "pronunciationTip": "one short, concrete pronunciation pointer about a specific sound or word, or empty string if nothing stands out", "praise": "a short enthusiastic one-line encouragement, game-style", "xp": 12}
"xp" must be an integer between 5 and 20 based on effort and correctness — be generous, especially for beginners.`;

    const raw = await callClaude(system, 'Give feedback now.', 400);
    const json = extractJson(raw);
    res.json(json);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`Buddy English running at http://localhost:${PORT}`);
});
