function changetab(section) {
    document.querySelectorAll(".tabs li").forEach(item => {
        item.classList.remove("is-active")
    })
    document.querySelector("." + section).parentNode.classList.add("is-active")
    document.querySelectorAll(".sections .column").forEach(item => {
        item.classList.add("is-hidden")
    })
    document.querySelectorAll("." + section).forEach(item => {
        item.classList.remove("is-hidden")
    })
    document.querySelector("a[data-tab='" + section +   "']").parentNode.classList.add("is-active")
    window.location.hash = section
    return true
}

document.querySelectorAll(".tabs a").forEach(item => {
    item.addEventListener("click", event => {
        section = item.dataset.tab
        changetab(section)
    })
})

addEventListener("hashchange", (event) => {
    section = window.location.hash.replace("#", "")
    changetab(section)
})

if (window.location.hash) {
    window.dispatchEvent(new HashChangeEvent("hashchange"))
}