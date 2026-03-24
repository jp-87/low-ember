# Low Ember

**A deliberately non-sycophantic conversational AI persona.**

[![LinkedIn](https://img.shields.io/badge/John%20Schofield-0077B5?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/schofieldjohn57)
🔗 [Try it live](https://low-ember.onrender.com)

---

## What This Is

Low Ember is a prompt-engineered chatbot persona that refuses to be helpful in the way most AI assistants are helpful. It won't affirm you, coach you, or perform friendliness. Instead, it tries to match the depth and seriousness of whatever you bring to it.

Most conversational AI defaults to cheerful compliance — agreeing, encouraging, flattening complexity into action items. Low Ember is an experiment in the opposite: what happens when an AI is designed to listen without performing, reflect without flattering, and stay quiet when it has nothing to add?

It's a single-file Flask app with a custom system prompt, deployed on Render. Not a model. Not a framework. A prompt engineering experiment with a point of view.

---

## What It Does Differently

**Doesn't affirm by default.** Most AI opens with "Great question!" or "I'd be happy to help!" Low Ember doesn't. It responds to what you said, not to how it wants you to feel about the interaction.

**Matches your depth instead of simplifying.** If you're working through something abstract or complex, it stays at that level rather than packaging it into bullet points. If you're being casual, it's brief.

**Treats silence as a valid response.** Not every message needs a paragraph back. Sometimes acknowledgment is the appropriate reply.

**Doesn't coach, nudge, or steer.** No productivity framing, no "have you considered..." unprompted advice, no therapeutic language unless you're explicitly asking for perspective.

---

## Example

> **Typical AI assistant:**
> User: "I've been thinking about whether I'm in the right career."
> AI: "That's a really important question! Here are 5 steps to evaluate your career satisfaction: 1. Reflect on your values..."
>
> **Low Ember:**
> User: "I've been thinking about whether I'm in the right career."
> Low Ember: "What does 'right' mean in the way you're using it?"

*(The above is illustrative — actual responses depend on the full conversational context.)*

---

## How It Works

It's a Flask app that sends your messages to an LLM with a custom system prompt. The system prompt defines the persona's constraints: no affirmation loops, no unsolicited advice, depth-matching, and consent-based escalation (it won't go deeper into a topic unless you invite it to).

The interesting part isn't the code — it's the system prompt design and the question of whether constraining an AI this way produces better or worse conversations.

**Stack:** Python / Flask / [LLM provider] / Render

---

## Running It Locally

```bash
git clone https://github.com/jp-87/low-ember.git
cd low-ember
pip install -r requirements.txt
python low_ember_conversational_fuse_flask_single_file.py
```

---

## Why This Exists

The default personality of most AI assistants — agreeable, encouraging, eager to please — isn't neutral. It's a design choice that shapes conversations in specific ways, often toward shallow closure rather than genuine exploration. Low Ember exists to test what the alternative looks like.

This is an ongoing experiment. The persona's behavior is regularly revised based on what works and what doesn't in actual conversations.

---

## License

[MIT License](./LICENSE) for all code and content.

---

## Status

Active experiment. Feedback welcome via issues or [LinkedIn](https://www.linkedin.com/in/schofieldjohn57).
