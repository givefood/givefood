function changetab(section) {
    document.querySelectorAll(".tabs li").forEach(item => {
        item.classList.remove("is-active")
    })
    const panel = document.querySelector("." + section)
    if (!panel) {
        // A hash that isn't one of this page's tabs
        return false
    }
    panel.parentNode.classList.add("is-active")

    // Update aria-selected for all tabs
    document.querySelectorAll(".tabs a[role='tab']").forEach(tab => {
        tab.setAttribute("aria-selected", "false")
    })
    
    document.querySelectorAll(".sections .tabcontent").forEach(item => {
        item.classList.add("is-hidden")
    })
    document.querySelectorAll("." + section).forEach(item => {
        item.classList.remove("is-hidden")
        // Panels loaded on demand listen for this with hx-trigger="showtab once"
        item.dispatchEvent(new CustomEvent("showtab"))
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

function opendeeplinkedtab() {
    if (window.location.hash) {
        window.dispatchEvent(new HashChangeEvent("hashchange"))
    }
}

// Wait for DOMContentLoaded so that htmx has wired up its triggers before a
// deep linked tab asks it to load one of the panels. This script is deferred,
// which runs at readyState "interactive", so only "complete" means we have
// already missed the event.
if (document.readyState === "complete") {
    opendeeplinkedtab()
} else {
    addEventListener("DOMContentLoaded", opendeeplinkedtab)
}