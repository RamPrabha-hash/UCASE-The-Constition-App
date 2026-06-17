function requestOTP() {
    const mobile = document.getElementById("mobile").value;

    fetch("/request-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mobile })
    })
    .then(res => res.json())
    .then(data => {
        alert(data.msg);
        if (data.success) {
            document.getElementById("otp").style.display = "block";
            document.getElementById("verifyBtn").style.display = "block";
        }
    });
}

function verifyOTP() {
    const mobile = document.getElementById("mobile").value;
    const otp = document.getElementById("otp").value;

    fetch("/verify-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mobile, otp })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            window.location.href = "/chat";
        } else {
            if (data.success) {
    window.location.href = "/chat";
} else {
    alert("Login failed. Please try again.");
}

        }
    });
}
fetch("/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ message: userMessage })
})

