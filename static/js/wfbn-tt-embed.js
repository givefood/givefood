const gf_wfbn = document.querySelector("#gf-needs");
const gf_iframe_html = "<iframe id='gf_headless_iframe' src='https://www.givefood.org.uk/needs/?headless=true&from=trusselltrust' style='width:100%;border:0;height:150px;' allow='geolocation'></iframe>"
gf_wfbn.innerHTML = gf_iframe_html
document.getElementById('gf_headless_iframe').onload = function() {iFrameResize({ log: false }, '#gf_headless_iframe')}
