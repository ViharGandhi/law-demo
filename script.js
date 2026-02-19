document.addEventListener('DOMContentLoaded', () => {

    // --- Mobile Navigation Toggle ---
    const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
    const nav = document.querySelector('.nav');

    mobileMenuBtn.addEventListener('click', () => {
        nav.classList.toggle('active');
        // Change icon based on state
        const icon = mobileMenuBtn.querySelector('i');
        if (nav.classList.contains('active')) {
            icon.classList.remove('fa-bars');
            icon.classList.add('fa-xmark');
        } else {
            icon.classList.remove('fa-xmark');
            icon.classList.add('fa-bars');
        }
    });

    // Close mobile menu when clicking a link
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            if (nav.classList.contains('active')) {
                nav.classList.remove('active');
                const icon = mobileMenuBtn.querySelector('i');
                icon.classList.remove('fa-xmark');
                icon.classList.add('fa-bars');
            }
        });
    });

    // --- FAQ Accordion ---
    const faqQuestions = document.querySelectorAll('.faq-question');

    faqQuestions.forEach(question => {
        question.addEventListener('click', () => {
            // Toggle active class on the question
            question.classList.toggle('active');

            // Get the answer element
            const answer = question.nextElementSibling;

            // Toggle max-height for smooth transition
            if (question.classList.contains('active')) {
                answer.style.maxHeight = answer.scrollHeight + 'px';
            } else {
                answer.style.maxHeight = 0;
            }

            // Optional: Close other open FAQs
            faqQuestions.forEach(otherQuestion => {
                if (otherQuestion !== question && otherQuestion.classList.contains('active')) {
                    otherQuestion.classList.remove('active');
                    otherQuestion.nextElementSibling.style.maxHeight = 0;
                }
            });
        });
    });

    // --- Smooth Scrolling for Anchor Links ---
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;

            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                // Adjust for fixed header offset
                const headerOffset = 80;
                const elementPosition = targetElement.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });

    // --- Active Navigation Highlight on Scroll ---
    const sections = document.querySelectorAll('section');
    const navLinks = document.querySelectorAll('.nav-link');

    window.addEventListener('scroll', () => {
        let current = '';
        const scrollY = window.pageYOffset;

        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            // fixed header offset compensation
            if (scrollY >= (sectionTop - 150)) {
                current = section.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href').includes(current)) {
                link.classList.add('active');
            }
        });
    });

    // --- Contact Form Submission (Mock) ---
    const contactForm = document.getElementById('contact-form');
    if (contactForm) {
        contactForm.addEventListener('submit', (e) => {
            e.preventDefault();

            // Basic validation is handled by HTML 'required' attributes
            // Here we simulate a submission
            const submitBtn = contactForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerText;

            submitBtn.innerText = 'Sending...';
            submitBtn.disabled = true;

            setTimeout(() => {
                // Simulate success
                alert('Thank you for your inquiry. A team member from Caldwell Family Law Group will contact you shortly.');
                contactForm.reset();
                submitBtn.innerText = originalText;
                submitBtn.disabled = false;
            }, 1500);
        });
    }

    // --- Chat Widget ---
    const chatToggle = document.getElementById('chat-toggle');
    const chatWindow = document.getElementById('chat-window');
    const chatClose = document.getElementById('chat-close');
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const chatSend = document.getElementById('chat-send');
    const suggestionChips = document.getElementById('suggestion-chips');
    const chatBadge = document.querySelector('.chat-badge');

    let messageCount = 0;
    let leadFormShown = false;
    let leadCaptured = false;
    let leadSkipCount = 0;
    let conversationContext = [];

    // Chat input is enabled from the start (no lead gate)
    chatInput.disabled = false;
    chatSend.disabled = false;
    chatInput.placeholder = "Type your question...";

    // Toggle chat open/close
    chatToggle.addEventListener('click', () => {
        chatWindow.classList.toggle('chat-hidden');
        if (!chatWindow.classList.contains('chat-hidden')) {
            chatInput.focus();
            chatBadge.classList.add('hidden');
        }
    });

    chatClose.addEventListener('click', () => {
        chatWindow.classList.add('chat-hidden');
    });

    // Markdown formatter for bot messages
    function formatMessage(text) {
        let html = text;

        // Code blocks (```...```)
        html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');

        // Inline code (`...`)
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Headers (### h4, ## h3, # h2)
        html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>');
        html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
        html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>');

        // Bold **text**
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        // Italic *text*
        html = html.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');

        // Links [text](url)
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

        // Unordered list items (- item at line start)
        html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
        // Wrap consecutive <li> in <ul>
        html = html.replace(/(<li>.*?<\/li>\n?)+/g, (match) => '<ul>' + match + '</ul>');

        // Horizontal rule
        html = html.replace(/^---$/gm, '<hr>');

        // Line breaks (remaining newlines)
        html = html.replace(/\n/g, '<br>');

        // Clean up: remove <br> adjacent to block elements
        html = html.replace(/<\/(h[234]|ul|ol|pre|hr)><br>/g, '</$1>');
        html = html.replace(/<br><(h[234]|ul|ol|pre|hr)/g, '<$1');

        return html;
    }

    // Add a message to the chat
    function addMessage(text, type) {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('chat-message', type === 'user' ? 'user-message' : 'bot-message');

        const contentDiv = document.createElement('div');
        contentDiv.innerHTML = type === 'bot' ? formatMessage(text) : `<p>${text}</p>`;

        const timeSpan = document.createElement('span');
        timeSpan.classList.add('message-time');
        const now = new Date();
        timeSpan.textContent = now.getHours() + ':' + now.getMinutes().toString().padStart(2, '0');

        msgDiv.appendChild(contentDiv);
        msgDiv.appendChild(timeSpan);

        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Track context for lead capture
        conversationContext.push({ role: type, content: text });
        if (conversationContext.length > 10) conversationContext.shift();
    }

    // Show typing indicator
    function showTyping() {
        const typingDiv = document.createElement('div');
        typingDiv.classList.add('typing-indicator');
        typingDiv.id = 'typing-indicator';
        typingDiv.innerHTML = '<span></span><span></span><span></span>';
        chatMessages.appendChild(typingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function removeTyping() {
        const el = document.getElementById('typing-indicator');
        if (el) el.remove();
    }

    // Suggestion Chips Handler
    if (suggestionChips) {
        suggestionChips.addEventListener('click', (e) => {
            if (e.target.classList.contains('chip')) {
                const text = e.target.textContent;
                sendMessage(text);
                suggestionChips.style.display = 'none';
            }
        });
    }

    function showLeadForm(mandatory) {
        leadFormShown = true;
        const template = document.getElementById('lead-form-template');
        const clone = template.content.cloneNode(true);

        const form = clone.querySelector('#lead-capture-form');
        const card = clone.querySelector('.lead-form-card');

        // Update heading & message based on mandatory flag
        if (mandatory) {
            card.querySelector('h3').textContent = "We'd love to help you further!";
            card.querySelector('p').textContent = "Please share your details so an attorney from our firm can reach out to you personally. We're here for you.";
            // Disable chat input until they fill out the form
            chatInput.disabled = true;
            chatSend.disabled = true;
            chatInput.placeholder = "Please share your details above to continue...";
        }

        // Only show skip button on first appearance
        if (!mandatory) {
            const skipBtn = document.createElement('button');
            skipBtn.type = 'button';
            skipBtn.className = 'skip-lead';
            skipBtn.textContent = 'Skip for now';
            card.appendChild(skipBtn);
        }

        chatMessages.appendChild(clone);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        const insertedCard = chatMessages.querySelector('.lead-form-card');

        // Handle Skip (only exists on first appearance)
        if (!mandatory) {
            insertedCard.querySelector('.skip-lead').addEventListener('click', () => {
                leadSkipCount++;
                leadFormShown = false; // allow it to appear again  
                insertedCard.remove();
            });
        }

        // Handle Form Submit
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = form.querySelector('#lead-email').value;
            const phone = form.querySelector('#lead-phone').value;

            const submitBtn = form.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Sending...';

            try {
                // Mock API call for demo
                await new Promise(resolve => setTimeout(resolve, 600));

                leadCaptured = true;
                const card = form.closest('.lead-form-card');
                card.remove();

                // Re-enable chat input
                chatInput.disabled = false;
                chatSend.disabled = false;
                chatInput.placeholder = "Type your question...";
                chatInput.focus();

                addMessage("Thanks for sharing your details! We'll have someone reach out to you. In the meantime, feel free to keep asking me anything. \ud83d\ude0a", 'bot');
            } catch (err) {
                alert("Error. Please try again.");
                submitBtn.disabled = false;
                submitBtn.textContent = 'Send Details';
            }
        });
    }

    async function sendMessage(message) {
        if (!message) return;

        // Hide chips after first user interaction
        if (suggestionChips) {
            suggestionChips.style.display = 'none';
        }

        // Show user message
        addMessage(message, 'user');
        messageCount++;

        // Show lead form: first at 2 messages (skippable), again at 4 messages (mandatory)
        if (!leadCaptured && !leadFormShown) {
            if (leadSkipCount === 0 && messageCount === 2) {
                setTimeout(() => showLeadForm(false), 800);
            } else if (leadSkipCount > 0 && messageCount === 4) {
                setTimeout(() => showLeadForm(true), 800);
            }
        }
        chatInput.value = '';
        chatSend.disabled = true;

        // Show typing indicator
        showTyping();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message, history: conversationContext.slice(0, -1) })
            });

            removeTyping();

            if (response.ok) {
                const data = await response.json();
                addMessage(data.reply, 'bot');
            } else {
                addMessage('Sorry, something went wrong. Please try again.', 'bot');
            }
        } catch (error) {
            removeTyping();
            addMessage('Unable to connect to the server. Make sure the server is running.', 'bot');
        }

        chatSend.disabled = false;
        chatInput.focus();
    }

    // Send message to backend
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        sendMessage(chatInput.value.trim());
    });

});
