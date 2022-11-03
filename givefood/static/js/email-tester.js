document.querySelectorAll("#email a").forEach(emaillink =>
    emaillink.addEventListener("click", function(event){
        Array.from(document.querySelectorAll("#email a")).forEach((el) => el.classList.remove('is-active'));
        this.classList.add("is-active")
    })
);