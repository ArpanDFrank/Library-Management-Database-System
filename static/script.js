document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('name').value;
            const password = document.getElementById('password').value;
            const role = document.getElementById('role').value;

            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, password, role })
                });

                const result = await response.json();
                console.log("Login response:", result);  // Debug: log response
                if (response.ok) {
                    alert(result.message);
                    window.location.href = result.redirect;  // Redirect to the portal
                } else {
                    alert(result.message);
                }
            } catch (error) {
                console.error("Error during login:", error);  // Debug: log any errors
                alert("An error occurred during login.");
            }
        });
    }

    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const data = {
                name: document.getElementById('name').value,
                password: document.getElementById('password').value,
                role: document.getElementById('role').value
            };

            if (data.role === 'reader') {
                data.email = document.getElementById('email').value;
                data.phone_no = document.getElementById('phone_no').value;
                data.address = document.getElementById('address').value;
            } else if (data.role === 'staff') {
                data.post = document.getElementById('post').value;
            }

            try {
                const response = await fetch('/signup', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (response.redirected) {
                    window.location.href = response.url;  // Redirect if necessary
                } else {
                    const result = await response.json();
                    console.log("Signup response:", result);  // Debug: log response
                    alert(result.message);
                }
            } catch (error) {
                console.error("Error during signup:", error);  // Debug: log any errors
                alert("An error occurred during signup.");
            }
        });
    }

    if (document.getElementById('role')) {
        document.getElementById('role').addEventListener('change', () => {
            const role = document.getElementById('role').value;
            document.getElementById('readerFields').style.display = role === 'reader' ? 'block' : 'none';
            document.getElementById('staffFields').style.display = role === 'staff' ? 'block' : 'none';
        });
    }
});
