const status = document.querySelector('#status');
if (!navigator.geolocation) {
  error()
} else {
  status.textContent = 'Requesting your location...';
  navigator.geolocation.getCurrentPosition(success, error);
}
function error() {
  if (document.querySelector('#postcodeform input').value == '') {
      status.textContent = 'Sorry, we can\t find your location automatically. Put your postcode in here instead.';
  }
  document.querySelector('#postcodeform').style.display = ""
  api_url = '/api/foodbanks/?postcode=' + document.querySelector('#postcodeform input').value
  var oReq = new XMLHttpRequest();
  oReq.addEventListener("load", api_response);
  oReq.responseType = 'json';
  oReq.open("GET", api_url);
  oReq.send();
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
  table_html = "<table class='table needs'>";
  console.log(this.response);
  for (i in this.response) {
    table_html += "<tr>";
    table_html += "<td><a href='" + this.response[i].url + "'>" + this.response[i].name + "</a><br><span class='distance'>" + this.response[i].distance_mi + "mi</span></td>";
    table_html += "<td>";
    if (this.response[i].number_needs > 0) {
      table_html += "<details><summary>" + this.response[i].number_needs + " items</summary>" + this.response[i].needs.replace(/\n/g, '<br>') + "</summary>";
    } else {
      table_html += "Nothing right now, thanks"
    }
    table_html += "</td>";
    table_html += "<td>" + this.response[i].updated_text + " ago</td>";
    table_html += "</tr>";
  }
  table_html += "</table>";
  document.querySelector('#thecontent').innerHTML = table_html;
}
