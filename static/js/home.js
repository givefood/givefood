$(do_polling)

function do_polling(){
  setTimeout(live_poll, 300000);
}

function live_poll() {
  $.ajax({
      url: "/live/",
      type: "GET",
      success: function(data) {
          $(".live").replaceWith(data)
      },
      dataType: "html",
      complete: do_polling,
      timeout: 2000
  })
}
