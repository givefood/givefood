window.addEventListener('DOMContentLoaded', () => {
  // Check if the hash (the part after #) contains the text fragment
  if (window.location.hash.includes(':~:text=')) {
    
    // Create a URL object to easily manipulate the URL
    const url = new URL(window.location.href);
    
    // Find the starting position of the text fragment
    const textFragmentIndex = url.hash.indexOf(':~:text=');
    
    // Set the hash to only be the part *before* the text fragment.
    // If the fragment was the only thing, url.hash becomes an empty string.
    url.hash = url.hash.substring(0, textFragmentIndex);

    // Use history.replaceState to update the URL in the browser bar
    // without reloading the page or adding a new history entry.
    history.replaceState(null, '', url.toString());
  }

  // Add the anchor from the current URL to the language switcher links
  const anchor = window.location.hash;
  if (anchor) {
    const langSwitcherLinks = document.querySelectorAll('#langswitcher a');
    langSwitcherLinks.forEach(link => {
      const linkUrl = new URL(link.href, window.location.origin);
      linkUrl.hash = anchor;
      link.href = linkUrl.toString();
    });
  }
});