function changetab(section) {
    document.querySelectorAll(".tabs li").forEach(item => {
        item.classList.remove("is-active")
    })
    document.querySelector("." + section).parentNode.classList.add("is-active")
    
    // Update aria-selected for all tabs
    document.querySelectorAll(".tabs a[role='tab']").forEach(tab => {
        tab.setAttribute("aria-selected", "false")
    })
    
    document.querySelectorAll(".sections .tabcontent").forEach(item => {
        item.classList.add("is-hidden")
    })
    document.querySelectorAll("." + section).forEach(item => {
        item.classList.remove("is-hidden")
    })
    
    const activeTab = document.querySelector("a[data-tab='" + section + "']")
    if (activeTab) {
        activeTab.parentNode.classList.add("is-active")
        activeTab.setAttribute("aria-selected", "true")
    }
    
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