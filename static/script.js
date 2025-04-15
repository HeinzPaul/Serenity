async function sendMessage() {
    const input = document.getElementById('user-input');
    const chatBox = document.getElementById('chat-box');
    const message = input.value.trim();
    const username = document.getElementById('username-input').value || 'You';

    handleFormSubmission(input, message);
    if (!message) return;

    // Create user message bubble
    const userBubble = document.createElement('div');
    userBubble.className = 'message user-message';
    userBubble.setAttribute('data-sender', username);
    userBubble.textContent = message;
    chatBox.appendChild(userBubble);

    input.value = '';

    // Scroll to the bottom of the chat
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const response = await fetch("/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: message })
        });

        const data = await response.json();
        const reply = data.reply || "No response";
        

        // Create AI message bubble
        const aiBubble = document.createElement('div');
        aiBubble.className = 'message ai-message';
        aiBubble.setAttribute('data-sender', 'Sera');
        chatBox.appendChild(aiBubble);

        // Simulate typing effect
        for (let i = 0; i < reply.length; i++) {
            aiBubble.textContent += reply[i]; // Add one character at a time
            chatBox.scrollTop = chatBox.scrollHeight; // Ensure it scrolls as the text is typed
            await new Promise(resolve => setTimeout(resolve, 20)); // Delay between characters
        }

        // Ensure it scrolls to the bottom after typing is complete
        chatBox.scrollTop = chatBox.scrollHeight;
    } catch (error) {
        // Handle errors and show an error message
        const errorBubble = document.createElement('div');
        errorBubble.className = 'message ai-message';
        errorBubble.textContent = "Oops! Something went wrong.";
        chatBox.appendChild(errorBubble);

        chatBox.scrollTop = chatBox.scrollHeight;
    }
}

// Add an event listener to trigger sendMessage when Enter is pressed
document.getElementById('user-input').addEventListener('keydown', function (event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        sendMessage(); // Call the sendMessage function
    }
});

// Function to handle form submission and log user message
async function handleFormSubmission(input, message) {
    if (!message) return;

    try {
        // Send user message to the log_user_message route
        await fetch("/log_message", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: message })
        });
    } catch (error) {
        console.error("Error logging user message:", error);
    }
}

// Function to fetch chat history and populate the chat box
async function fetchChatHistory() {
    const chatBox = document.getElementById('chat-box');
    const username = document.getElementById('username-input').value || 'You';

    try {
        const response = await fetch('/get_chat_history', {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.messages) {
            data.messages.forEach(message => {
                const messageBubble = document.createElement('div');
                messageBubble.className = message.startsWith('User:') ? 'message user-message' : 'message ai-message';
                messageBubble.setAttribute('data-sender', message.startsWith('User:') ? username : 'Sera');
                messageBubble.textContent = message.replace('User: ', '').replace('Sera: ', '');
                chatBox.appendChild(messageBubble);
            });

            // Scroll to the bottom of the chat
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    } catch (error) {
        console.error('Error fetching chat history:', error);
    }
}

function toggleMenu() {
    document.body.classList.toggle('menu-open');
}

// Add this to handle click outside to close menu
document.addEventListener('click', function(event) {
    const menu = document.querySelector('.side-menu');
    const hamburger = document.querySelector('.hamburger-menu');
    
    if (!menu.contains(event.target) && !hamburger.contains(event.target)) {
        document.body.classList.remove('menu-open');
    }
});
function showPersonalityOptions() {
    const options = document.getElementById('personality-options');
    options.style.display = options.style.display === 'none' ? 'block' : 'none';

    // Add event listeners to radio buttons
    const radioButtons = document.getElementsByName('personality');
    radioButtons.forEach(radio => {
        radio.addEventListener('change', async function() {
            try {
                const response = await fetch('/update_personality', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        personality: this.value
                    })
                });

                if (response.ok) {
                  
                    const chatBox = document.getElementById('chat-box');
                    const systemMessage = document.createElement('div');
                    systemMessage.className = 'message ai-message';
                    systemMessage.setAttribute('data-sender', 'System');
                    systemMessage.textContent = `Switched to ${this.value} mode`;
                    chatBox.appendChild(systemMessage);
                    chatBox.scrollTop = chatBox.scrollHeight;
                } else {
                    console.error('Failed to update personality');
                }
            } catch (error) {
                console.error('Error updating personality:', error);
            }
        });
    });
}
async function logout() {
    try {
        const response = await fetch('/logout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            window.location.reload();
        } else {
            alert('Logout failed: Server error');
        }
    } catch (error) {
        console.error('Error during logout:', error);
        alert('Logout failed: Network error');
    }
}

function displayStartingMessage() {
    const startingMessage = document.getElementById('startingmessage').value;

    if (startingMessage === 'True') {
        const chatBox = document.getElementById('chat-box');

        // Create AI message bubble
        const aiBubble = document.createElement('div');
        aiBubble.className = 'message ai-message';
        aiBubble.setAttribute('data-sender', 'Sera');
        aiBubble.textContent = "Hi! I'm Serenity or Sera for short, your compassionate and emotionally-aware mental health AI companion. I'm here to support you in processing your emotions and improving your well-being. Whether you need someone to listen, gentle encouragement, or small coping suggestions, I'm here for you. How can I support you today?";

        // Append the starting message to the chat box
        chatBox.appendChild(aiBubble);

        // Scroll to the bottom of the chat
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}
// Call fetchChatHistory when the page loads
window.onload = function () {
    fetchChatHistory(); // Fetch chat history
    displayStartingMessage(); // Display the starting message if applicable
};

async function openMemoriesModal() {
    const modal = document.getElementById('memories-modal');
    const memoriesList = document.getElementById('memories-list');
    memoriesList.innerHTML = ''; // Clear existing memories

    try {
        const response = await fetch('/get_memories', {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.memories) {
            data.memories.forEach(memory => {
                const listItem = document.createElement('li');
                listItem.textContent = memory;

                const deleteButton = document.createElement('button');
                deleteButton.textContent = 'X';
                deleteButton.onclick = () => deleteMemory(memory, listItem);

                listItem.appendChild(deleteButton);
                memoriesList.appendChild(listItem);
            });
        }
    } catch (error) {
        console.error('Error fetching memories:', error);
    }

    modal.style.display = 'block';
}

async function deleteMemory(memory, listItem) {
    try {
        const response = await fetch('/delete_memory', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ memory })
        });

        if (response.ok) {
            listItem.remove(); // Remove the memory from the modal
        } else {
            console.error('Failed to delete memory');
        }
    } catch (error) {
        console.error('Error deleting memory:', error);
    }
}

function closeModal() {
    const modal = document.getElementById('memories-modal');
    modal.style.display = 'none';
}   