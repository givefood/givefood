const status = document.querySelector('#status');
if (!navigator.geolocation) {
  status.textContent = 'Sorry. Geolocation is not supported by your browser';
} else {
  status.textContent = 'Requesting your location...';
  navigator.geolocation.getCurrentPosition(success, error);
}
function error() {
  status.textContent = 'Unable to retrieve your location';
}
function success(position) {
  latt  = position.coords.latitude;
  long = position.coords.longitude;
  api_url = '/api/foodbanks/?lattlong=' + latt + ',' + long
  var oReq = new XMLHttpRequest();
  oReq.addEventListener("load", api_response);
  oReq.responseType = 'json';
  oReq.open("GET", api_url);
  oReq.send();
}
function api_response() {
  table_html = "<table class='table'>"
  table_html += "<tr><th>Name</th><th>Distance</th><th>What They Need</th><th>Updated</th></tr>"
  console.log(this.response);
  for (i in this.response) {
    console.log(this.response[i].name)
    table_html += "<tr>"
    table_html += "<td>" + this.response[i].name + "</td>"
    table_html += "<td>" + this.response[i].distance_mi + "mi</td>"
    table_html += "<td>" + this.response[i].needs.replace(/\n/g, '<br>') + "</td>"
    table_html += "<td>" + this.response[i].updated_text + " ago</td>"
    table_html += "</tr>"
  }
  table_html += "</table>"
  document.querySelector('#thecontent').innerHTML = table_html
}
