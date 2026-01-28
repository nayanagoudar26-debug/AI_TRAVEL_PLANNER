document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('planner-form');
    const loadingOverlay = document.getElementById('loading');

    // Traveler Count Logic
    const typeSelect = document.getElementById('travelers-type');
    const countWrapper = document.getElementById('traveler-count-wrapper');
    const countInput = document.getElementById('travelers-count');

    if (typeSelect) {
        toggleTravelerCount(); // Init on load
    }

    window.toggleTravelerCount = function () {
        if (typeSelect.value === 'Family' || typeSelect.value === 'Friends') {
            countWrapper.style.display = 'block';
            if (countInput.value < 2) countInput.value = 4; // Default group size
        } else if (typeSelect.value === 'Couple') {
            countWrapper.style.display = 'none';
            countInput.value = 2; // Force 2
        } else {
            countWrapper.style.display = 'none';
            countInput.value = 1; // Force 1
        }
    };

    window.adjustTravelers = function (delta) {
        let current = parseInt(countInput.value);
        let newVal = current + delta;
        if (newVal < 1) newVal = 1;
        countInput.value = newVal;
    };

    if (form) {
        form.addEventListener('submit', function (e) {
            // Check checks for interests
            // Note: browser handles checkbox array for 'interests'

            // Show loading spinner
            loadingOverlay.style.display = 'flex';
        });
    }

    // Modal Logic
    const modal = document.getElementById("placeModal");
    const closeModal = document.querySelector(".close-modal");

    if (closeModal) {
        closeModal.onclick = function () {
            modal.style.display = "none";
        }
    }

    window.onclick = function (event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }

    window.openPlaceModal = function (element) {
        const name = element.getAttribute('data-name');
        const description = element.getAttribute('data-desc');
        const address = element.getAttribute('data-address');
        const mapLink = element.getAttribute('data-map');

        document.getElementById("modal-title").innerText = name;
        document.getElementById("modal-desc").innerText = description;
        document.getElementById("modal-address").innerText = "Address: " + address;
        document.getElementById("modal-map").href = mapLink;

        modal.style.display = "flex";
    }
    // Chat Widget Logic
    const chatWidget = document.getElementById('chat-widget');
    const chatToggle = document.getElementById('chat-toggle');
    const closeChat = document.getElementById('close-chat');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const chatBody = document.getElementById('chat-body');

    if (chatToggle) {
        chatToggle.onclick = () => chatWidget.style.display = 'flex';
        closeChat.onclick = () => chatWidget.style.display = 'none';

        sendBtn.onclick = sendMessage;
        chatInput.onkeypress = (e) => {
            if (e.key === 'Enter') sendMessage();
        };
    }

    function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        // User Message
        appendMessage(text, 'user');
        chatInput.value = '';

        // Bot Loading
        const loadingId = 'loading-' + Date.now();
        appendMessage('...', 'bot', loadingId);

        fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                context: {
                    destination: typeof DESTINATION !== 'undefined' ? DESTINATION : 'Unknown',
                    days: typeof DESTINATION !== 'undefined' ? DAYS : '3'
                }
            })
        })
            .then(res => res.json())
            .then(data => {
                document.getElementById(loadingId).remove();
                appendMessage(data.response, 'bot');
            })
            .catch(err => {
                document.getElementById(loadingId).remove();
                appendMessage("Sorry, I encountered an error.", 'bot');
                console.error(err);
            });
    }

    function appendMessage(text, sender, id = null) {
        const div = document.createElement('div');
        div.className = `chat-message ${sender}`;
        div.innerText = text;
        if (id) div.id = id;
        chatBody.appendChild(div);
        chatBody.scrollTop = chatBody.scrollHeight;
    }
});
