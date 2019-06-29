$("li").each(function(el){
  the_date = $(this).data("date")
  url = "chkr/?date=" + the_date
  the_li = this
  $.get({
    url: url,
    success: function(data){
      if (data == "OK") {
        the_color = "green"
      } else {
        the_color = "red"
      }
      $("span", the_li).attr("style","color:" + the_color).html(data)
    },
    async: false
  })
})