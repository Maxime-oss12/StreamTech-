// C'EST CA LA CORRECTION : Ca doit pointer sur le port 8000
const BACKEND_URL = 'http://127.0.0.1:8000/chat';
const JSON_FILE = 'movies.json';
let movieStore = [];

document.addEventListener('DOMContentLoaded', run);

async function run() {
    try {
        const response = await fetch(JSON_FILE);
        movieStore = await response.json();
        if (movieStore.length > 0) {
            setHero(movieStore[0]);
            renderGrid();
        }
        initChat();
    } catch (err) {
        console.error('Initialisation echouee', err);
    }
}

function setHero(m) {
    const hero = document.getElementById('hero');
    document.getElementById('heroTitle').innerText = m.title;
    document.getElementById('heroDescription').innerText = m.description || m.plot;
    hero.style.backgroundImage = `linear-gradient(rgba(0,0,0,0.5), rgba(0,0,0,0.5)), url(${m.poster})`;
}

function renderGrid() {
    const grid = document.getElementById('moviesGrid');
    grid.innerHTML = '';
    movieStore.forEach(m => {
        const card = document.createElement('div');
        card.className = 'movie-card';
        card.innerHTML = `
            <img src="${m.poster}" alt="${m.title}">
            <div class="movie-label">${m.title.toUpperCase()}</div>
        `;
        card.onclick = () => { setHero(m); window.scrollTo({top: 0, behavior: 'smooth'}); };
        grid.appendChild(card);
    });
}

function initChat() {
    const box = document.getElementById('chatbotWindow');
    const input = document.getElementById('userInput');
    const messages = document.getElementById('chatMessages');

    document.getElementById('chatbotToggle').onclick = () => box.classList.toggle('active');
    document.getElementById('chatbotClose').onclick = () => box.classList.remove('active');
    document.getElementById('chatbotResize').onclick = () => box.classList.toggle('expanded');
    document.getElementById('chatbotReset').onclick = () => {
        messages.innerHTML = '';
        displayMsg('Assistant StreamTech réinitialisé. Posez-moi vos questions !', 'bot');
    };

    const sendAction = async () => {
        const text = input.value.trim();
        if (!text) return;

        displayMsg(text, 'user');
        input.value = '';
        const botNode = displayMsg('Assistant StreamTech analyse...', 'bot');

        try {
            const res = await fetch(BACKEND_URL, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({prompt: text})
            });
            const data = await res.json();
            botNode.innerText = data.response;
        } catch (e) {
            botNode.innerText = "Erreur : L'IA n'est pas joignable.";
        }
    };

    document.getElementById('sendBtn').onclick = sendAction;
    input.onkeypress = (e) => { if (e.key === 'Enter') sendAction(); };
}

function displayMsg(msg, role) {
    const b = document.createElement('div');
    b.className = `bubble ${role}-bubble`;
    b.innerText = msg;
    const area = document.getElementById('chatMessages');
    area.appendChild(b);
    area.scrollTop = area.scrollHeight;
    return b;
}
