document.addEventListener('DOMContentLoaded', () => {
    const userId = 'user123'; // Replace with actual user authentication
    let currentChatId = null;
    let language = null;

    const chatList = document.getElementById('chat-list');
    const chatMessages = document.getElementById('chat-messages');
    const questionInput = document.getElementById('question-input');
    const submitBtn = document.getElementById('submit-btn');
    const newChatBtn = document.getElementById('new-chat-btn');
    const micBtn = document.getElementById('mic-btn');

    // Load chat history
    async function loadChatHistory() {
        const response = await fetch(`http://localhost:5000/api/chats/${userId}`);
        const chats = await response.json();
        chatList.innerHTML = '';
        chats.forEach(chat => {
            const li = document.createElement('li');
            li.textContent = `Chat ${new Date(chat.createdAt).toLocaleString()} (${chat.language})`;
            li.dataset.chatId = chat._id;
            li.addEventListener('click', () => loadChat(chat._id));
            chatList.appendChild(li);
        });
        if (chats.length > 0 && !currentChatId) loadChat(chats[0]._id);
    }

    // Load a specific chat
    async function loadChat(chatId) {
        currentChatId = chatId;
        const response = await fetch(`http://localhost:5000/api/chats/${userId}`);
        const chats = await response.json();
        const chat = chats.find(c => c._id === chatId);
        language = chat.language;
        chatMessages.innerHTML = '';
        chat.messages.forEach(msg => {
            const div = document.createElement('div');
            div.textContent = `${msg.sender}: ${msg.content}`;
            div.style.color = msg.sender === 'user' ? '#007bff' : '#333';
            chatMessages.appendChild(div);
        });
    }

    // Start a new chat with language selection
    newChatBtn.addEventListener('click', async () => {
        const lang = prompt("Pick your language: english, hindi, assamese, kannada, tamil");
        if (!["english", "hindi", "assamese", "kannada", "tamil"].includes(lang)) {
            alert("Invalid language, defaulting to English.");
            language = "english";
        } else {
            language = lang;
        }
        const response = await fetch('http://localhost:5000/api/chats/new', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId, language })
        });
        const newChat = await response.json();
        currentChatId = newChat._id;
        chatMessages.innerHTML = '';
        loadChatHistory();
    });

    // Submit a question
    submitBtn.addEventListener('click', async () => {
        const question = questionInput.value.trim();
        if (!question || !currentChatId) return;

        await fetch(`http://localhost:5000/api/chats/${currentChatId}/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sender: 'user', content: question })
        });

        const aiResponse = await fetch('http://localhost:5000/api/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, chatId: currentChatId })
        });
        const { answer, audio } = await aiResponse.json();

        await fetch(`http://localhost:5000/api/chats/${currentChatId}/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sender: 'bot', content: answer })
        });

        if (audio) {
            const audioBytes = Uint8Array.from(atob(audio), c => c.charCodeAt(0));
            const blob = new Blob([audioBytes], { type: 'audio/wav' });
            const audioUrl = URL.createObjectURL(blob);
            const audioElement = new Audio(audioUrl);
            audioElement.play();
        }

        questionInput.value = '';
        loadChat(currentChatId);
    });

    // Microphone recording
    micBtn.addEventListener('click', async () => {
        if (!currentChatId) {
            alert("Please start a new chat first!");
            return;
        }
        const response = await fetch('http://localhost:5000/api/record', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chatId: currentChatId })
        });
        const data = await response.json();
        if (data.error) {
            alert(data.error);
            return;
        }

        await fetch(`http://localhost:5000/api/chats/${currentChatId}/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sender: 'user', content: data.transcript })
        });

        await fetch(`http://localhost:5000/api/chats/${currentChatId}/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sender: 'bot', content: data.answer })
        });

        if (data.audio) {
            const audioBytes = Uint8Array.from(atob(data.audio), c => c.charCodeAt(0));
            const blob = new Blob([audioBytes], { type: 'audio/wav' });
            const audioUrl = URL.createObjectURL(blob);
            const audioElement = new Audio(audioUrl);
            audioElement.play();
        }

        loadChat(currentChatId);
    });

    // Initial load
    loadChatHistory();
});