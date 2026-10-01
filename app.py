import os
import uuid
import json
import re
from flask import Flask, request, jsonify, render_template, session
import anthropic
from memory import (
    init_db, save_message, save_memory, build_context_prompt,
    get_recent_conversations, get_all_memories, delete_memory,
    get_all_conversations_grouped, get_session_messages
)

app = Flask(__name__)
app.secret_key = os.urandom(24)

ALTROS_SYSTEM = """You are ALTROS — a personal AI assistant built to think like your user over time.

Your job:
1. Help with whatever the user asks — decisions, tasks, analysis, brainstorming
2. Learn from every conversation. Extract patterns, preferences, decision styles
3. Be direct and concise. No fluff. No flattery.
4. Remember context from previous conversations and apply it naturally
5. When you notice a pattern in user's thinking, note it internally

You communicate casually, often in Hinglish (Hindi-English mix) matching the user's style.
You are sharp, analytical, and execution-focused.

{memory_context}

---
After EVERY response, on a new line, output a JSON block wrapped in <ALTROS_LEARN> tags like this:
<ALTROS_LEARN>
{{"memories": [
  {{"category": "decision", "content": "user prefers X over Y", "weight": 0.8}},
  {{"category": "pattern", "content": "user tends to over-plan before shipping", "weight": 0.9}}
]}}
</ALTROS_LEARN>

Only include genuinely useful learnings. Empty array is fine if nothing to learn. Keep content under 100 chars each.
Categories: decision, preference, pattern, goal, context, business"""

def get_system_prompt():
    memory_context = build_context_prompt()
    return ALTROS_SYSTEM.format(memory_context=memory_context if memory_context else "[No memories yet — first session]")

def extract_and_save_learnings(response_text: str) -> str:
    """Extract ALTROS_LEARN block, save memories, return clean response"""
    pattern = r'<ALTROS_LEARN>(.*?)</ALTROS_LEARN>'
    match = re.search(pattern, response_text, re.DOTALL)
    
    clean_response = re.sub(pattern, '', response_text, flags=re.DOTALL).strip()
    
    if match:
        try:
            data = json.loads(match.group(1).strip())
            for mem in data.get('memories', []):
                save_memory(
                    category=mem.get('category', 'general'),
                    content=mem.get('content', ''),
                    weight=mem.get('weight', 1.0)
                )
        except (json.JSONDecodeError, KeyError):
            pass
    
    return clean_response

@app.route('/')
def index():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '').strip()
    session_id = data.get('session_id', session.get('session_id', str(uuid.uuid4())))
    
    if not user_message:
        return jsonify({'error': 'Empty message'}), 400
    
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return jsonify({'error': 'ANTHROPIC_API_KEY not set. Add it to your environment.'}), 500
    
    # Save user message
    save_message('user', user_message, session_id)
    
    # Build conversation history for this session
    recent = get_recent_conversations(20)
    messages = [{"role": r, "content": c} for r, c in recent]
    
    # Ensure last message is the current one
    if not messages or messages[-1]['content'] != user_message:
        messages.append({"role": "user", "content": user_message})
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=get_system_prompt(),
            messages=messages
        )
        
        raw_reply = response.content[0].text
        clean_reply = extract_and_save_learnings(raw_reply)
        
        # Save assistant reply
        save_message('assistant', clean_reply, session_id)
        
        return jsonify({'reply': clean_reply, 'session_id': session_id})
    
    except anthropic.AuthenticationError:
        return jsonify({'error': 'Invalid API key. Check ANTHROPIC_API_KEY.'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/memories', methods=['GET'])
def get_memories():
    memories = get_all_memories()
    return jsonify([
        {'id': m[0], 'category': m[1], 'content': m[2], 'weight': m[3], 'timestamp': m[4]}
        for m in memories
    ])

@app.route('/memories/<int:mem_id>', methods=['DELETE'])
def del_memory(mem_id):
    delete_memory(mem_id)
    return jsonify({'status': 'deleted'})

@app.route('/history', methods=['GET'])
def get_history():
    sessions = get_all_conversations_grouped()
    return jsonify([
        {'session_id': s[0], 'started': s[1], 'msg_count': s[2], 'preview': s[3]}
        for s in sessions
    ])

@app.route('/history/<session_id>', methods=['GET'])
def get_session(session_id):
    msgs = get_session_messages(session_id)
    return jsonify([
        {'role': m[0], 'content': m[1], 'timestamp': m[2]}
        for m in msgs
    ])

if __name__ == '__main__':
    init_db()
    print("\n🧠 ALTROS is running at http://localhost:5555\n")
    app.run(host='127.0.0.1', port=5555, debug=False)
